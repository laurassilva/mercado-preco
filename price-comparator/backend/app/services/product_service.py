import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select, or_

from app.core.config import settings
from app.models.market import Market
from app.models.product import MarketProduct, ScrapingJob
from app.models.search_history import SearchHistory
from app.normalizer.product_normalizer import title_case
from app.scrapers.connector_manager import ConnectorManager
from app.scrapers.search_utils import filter_products, _key_terms, product_score
from app.schemas.product import ProductResult as ProductResultSchema, SearchResponse

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutos

_STOP_WORDS = {
    "de", "do", "da", "dos", "das", "com", "sem", "para", "por",
    "kg", "g", "gr", "ml", "lt", "l", "un", "pc", "cx", "pct",
}

_redis_pool = None


async def _get_redis():
    global _redis_pool
    if _redis_pool is None:
        import redis.asyncio as aioredis
        _redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def _cache_get(key: str) -> str | None:
    try:
        r = await _get_redis()
        return await r.get(key)
    except Exception as exc:
        logger.debug("Cache get falhou: %s", exc)
        return None


async def _cache_set(key: str, value: str) -> None:
    try:
        r = await _get_redis()
        await r.setex(key, _CACHE_TTL, value)
    except Exception as exc:
        logger.debug("Cache set falhou: %s", exc)


def _make_cache_key(query: str, market_ids) -> str:
    raw = f"dbsearch:{query}:{sorted(str(m) for m in market_ids) if market_ids else ''}"
    return hashlib.md5(raw.encode()).hexdigest()


async def search_products(
    query: str,
    db: AsyncSession,
    user_id=None,
    market_ids: list | None = None,
    category: str | None = None,
    live: bool = True,
) -> SearchResponse:
    from app.scrapers.search_utils import _expand_synonyms, _normalize, _correct_typo

    # Correct typos and expand synonyms for display
    q_norm = _normalize(query)
    words = q_norm.split()
    corrected_words = [_correct_typo(w) if len(w) >= 3 else w for w in words]
    corrected = " ".join(corrected_words)
    corrected_query = corrected if corrected != q_norm else None

    if live:
        results = await _live_search(query, db, market_ids)
    else:
        results = await _db_search(query, db, market_ids, category)

    # Sort by relevance first, then price as tiebreaker
    results.sort(key=lambda x: (-(x.confidence_score or 0), float(x.price)))

    if results:
        min_price = min(float(r.price) for r in results)
        max_price = max(float(r.price) for r in results)
        avg_price = sum(float(r.price) for r in results) / len(results)

        # Find cheapest item
        cheapest_item = min(results, key=lambda x: float(x.price))
        cheapest_item.is_cheapest = True

        for r in results:
            r.difference = Decimal(str(float(r.price) - min_price)).quantize(Decimal("0.01"))
            r.difference_pct = (
                (float(r.price) - min_price) / min_price * 100
                if max_price > min_price else 0.0
            )

        cheapest = cheapest_item.market_name
        priciest = max(results, key=lambda x: float(x.price)).market_name
    else:
        avg_price = cheapest = priciest = None

    history = SearchHistory(user_id=user_id, query=query, results_count=len(results))
    db.add(history)
    await db.commit()

    return SearchResponse(
        query=query,
        corrected_query=corrected_query,
        results=results,
        total=len(results),
        cheapest_market=cheapest,
        most_expensive_market=priciest,
        avg_price=Decimal(str(avg_price)).quantize(Decimal("0.01")) if avg_price else None,
        searched_at=datetime.now(timezone.utc),
    )


async def _live_search(
    query: str, db: AsyncSession, market_ids: list | None
) -> list[ProductResultSchema]:
    result = await db.execute(select(Market).where(Market.is_active == True))
    markets = result.scalars().all()

    if market_ids:
        markets = [m for m in markets if str(m.id) in [str(mid) for mid in market_ids]]

    async def fetch(market: Market):
        try:
            scraper = ConnectorManager.get(
                market.scraper_class, market.name, market.config or {}
            )
            products = await scraper.search(query)
            await scraper.close()
            return market, products
        except Exception as exc:
            logger.error("Live search falhou em %s: %s", market.name, exc)
            return market, []

    raw = await asyncio.gather(*[fetch(m) for m in markets])

    all_results: list[ProductResultSchema] = []
    for market, products in raw:
        for p in products:
            all_results.append(
                ProductResultSchema(
                    market_id=market.id,
                    market_name=market.name,
                    market_logo=market.logo_url,
                    product_name=title_case(p.product_name),
                    brand=title_case(p.brand) if p.brand else None,
                    quantity=p.quantity,
                    price=p.price,
                    image_url=p.image_url,
                    product_url=p.product_url,
                    last_updated=p.last_updated,
                )
            )

    # Filtrar por relevância e compatibilidade de quantidade
    filtered = filter_products(query, all_results)
    for r in filtered:
        r.confidence_score = round(product_score(query, r.product_name), 1)
    return filtered


async def _db_search(
    query: str, db: AsyncSession, market_ids: list | None, category: str | None = None
) -> list[ProductResultSchema]:
    """
    Smart database search:
    1. Expands synonyms and corrects typos
    2. Pre-filters candidates via GIN trigram index (OR for broader recall)
    3. Scores and ranks by relevance using weighted scoring
    4. Caches results in Redis for 5 minutes
    """
    cache_key = _make_cache_key(query, market_ids)
    cached = await _cache_get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            return [ProductResultSchema.model_validate(item) for item in data]
        except Exception:
            pass

    from app.scrapers.search_utils import _expand_synonyms, _normalize

    key_terms = _key_terms(query)

    # Also get terms from synonym-expanded query
    expanded = _expand_synonyms(query)
    expanded_terms = [w for w in _normalize(expanded).split() if len(w) >= 2 and w not in _STOP_WORDS]

    all_search_terms = list(set(key_terms + expanded_terms))

    qty_re = re.compile(r"^\d+[a-z]{0,3}$")
    name_terms = [t for t in all_search_terms if not qty_re.match(t)]
    if not name_terms:
        name_terms = all_search_terms[:3]  # fallback

    stmt = (
        select(MarketProduct, Market)
        .join(Market, MarketProduct.market_id == Market.id)
        .where(MarketProduct.is_available == True, Market.is_active == True)
    )

    if name_terms:
        # Use OR between terms for broader recall, scoring will filter
        ilike_clauses = [func.f_unaccent(MarketProduct.name).ilike(f"%{t}%") for t in name_terms[:5]]
        if len(ilike_clauses) >= 2:
            # Require at least the first (most important) term, OR the rest
            primary = ilike_clauses[0]
            stmt = stmt.where(and_(primary, or_(*ilike_clauses[1:])) if len(ilike_clauses) > 1 else primary)
        else:
            stmt = stmt.where(ilike_clauses[0])

    if market_ids:
        stmt = stmt.where(Market.id.in_(market_ids))

    if category:
        stmt = stmt.where(MarketProduct.category == category)

    stmt = stmt.order_by(MarketProduct.price).limit(800)

    result = await db.execute(stmt)
    rows = result.all()

    candidates = [
        ProductResultSchema(
            market_id=market.id,
            market_name=market.name,
            market_logo=market.logo_url,
            product_name=title_case(mp.name),
            brand=title_case(mp.brand) if mp.brand else None,
            quantity=mp.quantity,
            price=mp.price,
            image_url=mp.image_url,
            product_url=mp.product_url,
            last_updated=mp.last_updated,
        )
        for mp, market in rows
    ]

    if not candidates:
        return []

    # Score and filter
    scored = [(c, product_score(query, c.product_name)) for c in candidates]
    relevant = [(c, s) for c, s in scored if s >= 45.0]

    if not relevant:
        return []

    for c, s in relevant:
        c.confidence_score = round(s, 1)

    # Sort by relevance first
    relevant.sort(key=lambda x: -x[1])
    results = [c for c, _ in relevant]

    # Cache
    try:
        payload = json.dumps(
            [r.model_dump(mode="json") for r in results],
            default=str,
        )
        await _cache_set(cache_key, payload)
    except Exception as exc:
        logger.debug("Falha ao cachear resultados: %s", exc)

    return results


async def trigger_scraping_jobs(query: str, market_ids: list | None, db: AsyncSession):
    from app.workers.tasks import scrape_market

    result = await db.execute(select(Market).where(Market.is_active == True))
    markets = result.scalars().all()
    if market_ids:
        markets = [m for m in markets if str(m.id) in [str(mid) for mid in market_ids]]

    jobs = []
    for market in markets:
        job = ScrapingJob(market_id=market.id, query=query, status="pending")
        db.add(job)
        await db.flush()
        scrape_market.delay(str(market.id), query, str(job.id))
        jobs.append(job)

    await db.commit()
    return jobs

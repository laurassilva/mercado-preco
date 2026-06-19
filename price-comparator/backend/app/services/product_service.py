import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.config import settings
from app.models.market import Market
from app.models.product import MarketProduct, ScrapingJob
from app.models.search_history import SearchHistory
from app.normalizer.product_normalizer import title_case
from app.scrapers.connector_manager import ConnectorManager
from app.scrapers.search_utils import filter_products, _key_terms
from app.schemas.product import ProductResult as ProductResultSchema, SearchResponse

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutos

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
    live: bool = True,
) -> SearchResponse:
    if live:
        results = await _live_search(query, db, market_ids)
    else:
        results = await _db_search(query, db, market_ids)

    # Garantir ordenação numérica por preço
    results.sort(key=lambda x: float(x.price))

    if results:
        min_price = float(results[0].price)
        max_price = float(results[-1].price)
        avg_price = sum(float(r.price) for r in results) / len(results)
        results[0].is_cheapest = True

        for r in results:
            r.difference = Decimal(str(float(r.price) - min_price)).quantize(Decimal("0.01"))
            r.difference_pct = (
                (float(r.price) - min_price) / min_price * 100
                if max_price > min_price else 0.0
            )

        cheapest = results[0].market_name
        priciest = results[-1].market_name
    else:
        avg_price = cheapest = priciest = None

    history = SearchHistory(user_id=user_id, query=query, results_count=len(results))
    db.add(history)
    await db.commit()

    return SearchResponse(
        query=query,
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
    return filter_products(query, all_results)


async def _db_search(
    query: str, db: AsyncSession, market_ids: list | None
) -> list[ProductResultSchema]:
    """
    Busca no banco local com dois níveis:
    1. Filtra candidatos no banco via ILIKE (acelerado por índice GIN trigrama)
    2. Reclassifica e filtra por relevância + compatibilidade de quantidade
    Usa Redis para cachear resultados por 5 minutos.
    """
    cache_key = _make_cache_key(query, market_ids)
    cached = await _cache_get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            return [ProductResultSchema.model_validate(item) for item in data]
        except Exception:
            pass  # cache corrompido → consulta fresca

    key_terms = _key_terms(query)
    all_terms = [t.strip() for t in query.split() if len(t.strip()) >= 2]

    stmt = (
        select(MarketProduct, Market)
        .join(Market, MarketProduct.market_id == Market.id)
        .where(MarketProduct.is_available == True, Market.is_active == True)
    )

    search_terms = key_terms if key_terms else all_terms
    if search_terms:
        stmt = stmt.where(
            or_(*[MarketProduct.name.ilike(f"%{t}%") for t in search_terms])
        )

    if market_ids:
        stmt = stmt.where(Market.id.in_(market_ids))

    stmt = stmt.order_by(MarketProduct.price).limit(1000)

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

    # Filtra por relevância + compatibilidade de quantidade (min_score 50)
    from app.scrapers.search_utils import product_score
    scored = [(c, product_score(query, c.product_name)) for c in candidates]
    relevant = [(c, s) for c, s in scored if s >= 50.0]

    if not relevant:
        return []

    relevant.sort(key=lambda x: float(x[0].price))
    results = [c for c, _ in relevant]

    # Cacheia por 5 minutos
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

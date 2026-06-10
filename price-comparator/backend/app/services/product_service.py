import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.market import Market
from app.models.product import MarketProduct, ScrapingJob
from app.models.search_history import SearchHistory
from app.scrapers.connector_manager import ConnectorManager
from app.schemas.product import ProductResult as ProductResultSchema, SearchResponse


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

    results.sort(key=lambda x: x.price)

    if results:
        min_price = results[0].price
        max_price = results[-1].price
        avg_price = sum(r.price for r in results) / len(results)
        results[0].is_cheapest = True

        for r in results:
            r.difference = r.price - min_price
            r.difference_pct = (
                float((r.price - min_price) / min_price * 100)
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
            import logging
            logging.getLogger(__name__).error(
                "Live search falhou em %s: %s", market.name, exc
            )
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
                    product_name=p.product_name,
                    brand=p.brand,
                    quantity=p.quantity,
                    price=p.price,
                    image_url=p.image_url,
                    product_url=p.product_url,
                    last_updated=p.last_updated,
                )
            )

    return all_results


async def _db_search(
    query: str, db: AsyncSession, market_ids: list | None
) -> list[ProductResultSchema]:
    """
    Busca no banco local com dois níveis:
    1. Filtra por termos-chave no banco (ILIKE OR) para trazer candidatos
    2. Reclassifica e filtra por relevância com rapidfuzz (elimina irrelevantes)
    """
    from app.scrapers.search_utils import _key_terms, filter_products, product_score

    # Extrai apenas os termos significativos (sem unidades como kg, ml, 2l)
    key_terms = _key_terms(query)
    all_terms = [t.strip() for t in query.split() if len(t.strip()) >= 2]

    stmt = (
        select(MarketProduct, Market)
        .join(Market, MarketProduct.market_id == Market.id)
        .where(MarketProduct.is_available == True, Market.is_active == True)
    )

    if key_terms:
        # OR: qualquer termo-chave presente — traz candidatos amplos
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(*[MarketProduct.name.ilike(f"%{t}%") for t in key_terms])
        )

    if market_ids:
        stmt = stmt.where(Market.id.in_(market_ids))

    stmt = stmt.order_by(MarketProduct.price).limit(1000)

    result = await db.execute(stmt)
    rows = result.all()

    # Constrói objetos e aplica filtragem por relevância
    candidates = [
        ProductResultSchema(
            market_id=market.id,
            market_name=market.name,
            market_logo=market.logo_url,
            product_name=mp.name,
            brand=mp.brand,
            quantity=mp.quantity,
            price=mp.price,
            image_url=mp.image_url,
            product_url=mp.product_url,
            last_updated=mp.last_updated,
        )
        for mp, market in rows
    ]

    # Filtra e ordena por relevância, depois por preço dentro dos relevantes
    if not candidates:
        return []

    class _Proxy:
        def __init__(self, obj): self._o = obj
        @property
        def product_name(self): return self._o.product_name
        def __getattr__(self, n): return getattr(self._o, n)

    # Usa o product_score para manter só produtos realmente relacionados
    scored = [(c, product_score(query, c.product_name)) for c in candidates]
    relevant = [(c, s) for c, s in scored if s >= 50.0]

    if not relevant:
        return []

    # Ordena por preço (objetivo primário) dentro dos relevantes
    relevant.sort(key=lambda x: float(x[0].price))
    return [c for c, _ in relevant]


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

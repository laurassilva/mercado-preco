import asyncio
import logging
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Tarefa: pesquisa por termo em um mercado ────────────────────────────────

@celery_app.task(bind=True, name="app.workers.tasks.scrape_market")
def scrape_market(self, market_id: str, query: str, job_id: str):
    return run_async(_scrape_market_async(market_id, query, job_id))


async def _scrape_market_async(market_id: str, query: str, job_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.market import Market
    from app.models.product import MarketProduct, PriceHistory, ScrapingJob
    from app.scrapers.connector_manager import ConnectorManager

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        try:
            result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                await db.commit()

            result = await db.execute(select(Market).where(Market.id == market_id))
            market = result.scalar_one_or_none()
            if not market:
                return

            scraper = ConnectorManager.get(market.scraper_class, market.name, market.config or {})
            products = await scraper.search(query)
            await scraper.close()

            inserted, updated = await _save_products_bulk(db, market.id, products)
            count = inserted + updated
            logger.info(
                "scrape_market %s: %d inseridos, %d atualizados",
                market.name, inserted, updated,
            )

            if job:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.results_count = count
            await db.commit()

        except Exception as exc:
            logger.error("scrape_market falhou para %s: %s", market_id, exc, exc_info=True)
            result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise

    await engine.dispose()


# ─── Tarefa: varredura completa de todos os produtos ─────────────────────────

@celery_app.task(bind=True, name="app.workers.tasks.crawl_all_products")
def crawl_all_products(self, market_id: str | None = None):
    return run_async(_crawl_all_async(market_id))


async def _crawl_one_market(market, Session):
    """Coleta um mercado inteiro e salva no banco."""
    from app.models.product import ScrapingJob
    from app.scrapers.connector_manager import ConnectorManager

    async with Session() as db:
        job = ScrapingJob(
            market_id=market.id,
            query="[varredura completa]",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        try:
            scraper = ConnectorManager.get(
                market.scraper_class, market.name, market.config or {}
            )

            if hasattr(scraper, "crawl_all"):
                logger.info("Iniciando varredura: %s", market.name)
                products = await scraper.crawl_all()
            else:
                products = []

            await scraper.close()

            inserted, updated = await _save_products_bulk(db, market.id, products)
            count = inserted + updated

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.results_count = count
            await db.commit()
            logger.info(
                "%s: %d inseridos, %d atualizados",
                market.name, inserted, updated,
            )
            return count

        except Exception as exc:
            logger.error("Varredura falhou em %s: %s", market.name, exc, exc_info=True)
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return 0


async def _crawl_all_async(market_id: str | None):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.market import Market

    engine = create_async_engine(settings.DATABASE_URL, pool_size=10)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        if market_id:
            result = await db.execute(
                select(Market).where(Market.id == market_id, Market.is_active == True)
            )
            markets = [result.scalar_one_or_none()]
            markets = [m for m in markets if m]
        else:
            result = await db.execute(select(Market).where(Market.is_active == True))
            markets = result.scalars().all()

    tasks = [_crawl_one_market(m, Session) for m in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total = sum(r for r in results if isinstance(r, int))
    await engine.dispose()
    logger.info("Varredura completa finalizada. Total: %d produtos processados", total)
    return total


# ─── Helper: salva/atualiza produtos no banco (BULK) ────────────────────────

async def _save_products_bulk(db, market_id, products) -> tuple[int, int]:
    """
    Salva produtos em lotes usando bulk operations.
    Muito mais rápido que SELECT individual por produto.
    """
    from decimal import Decimal
    from sqlalchemy import select, text
    from app.models.product import MarketProduct, PriceHistory, PriceAlert
    from app.normalizer.product_normalizer import title_case
    from app.services.category_service import classify_product, load_categories

    if not products:
        return 0, 0

    now = datetime.now(timezone.utc)

    # Load categories for classification
    try:
        cat_dict = await load_categories(db)
    except Exception:
        cat_dict = {}

    existing_by_url = {}
    existing_by_name = {}
    result = await db.execute(
        select(MarketProduct).where(MarketProduct.market_id == market_id)
    )
    for mp in result.scalars().all():
        if mp.product_url:
            existing_by_url[mp.product_url] = mp
        existing_by_name[(str(market_id), mp.name)] = mp

    inserted = 0
    updated = 0
    batch_new: list[MarketProduct] = []
    batch_history: list[PriceHistory] = []
    batch_alerts: list[PriceAlert] = []

    for p in products:
        try:
            clean_name = title_case(p.product_name)
            clean_brand = title_case(p.brand) if p.brand else None

            mp = None
            if p.product_url:
                mp = existing_by_url.get(p.product_url)
            if mp is None:
                mp = existing_by_name.get((str(market_id), clean_name))

            if mp:
                if mp.price != p.price:
                    batch_history.append(PriceHistory(
                        market_product_id=mp.id,
                        price=mp.price,
                        checked_at=now,
                    ))
                    diff = p.price - mp.price
                    pct = (float(diff) / float(mp.price) * 100) if mp.price != 0 else 0
                    batch_alerts.append(PriceAlert(
                        market_product_id=mp.id,
                        market_id=market_id,
                        product_name=clean_name,
                        old_price=mp.price,
                        new_price=p.price,
                        price_diff=diff,
                        price_diff_pct=Decimal(str(round(pct, 2))),
                        alert_type="increase" if diff > 0 else "decrease",
                        category=mp.category,
                        detected_at=now,
                    ))
                mp.price = p.price
                mp.name = clean_name
                mp.brand = clean_brand or mp.brand
                mp.image_url = p.image_url or mp.image_url
                mp.last_updated = now
                if p.product_url and not mp.product_url:
                    mp.product_url = p.product_url
                if mp.category is None and cat_dict:
                    mp.category = classify_product(clean_name, cat_dict)
                updated += 1
            else:
                category = classify_product(clean_name, cat_dict) if cat_dict else None
                new_mp = MarketProduct(
                    market_id=market_id,
                    name=clean_name,
                    brand=clean_brand,
                    quantity=p.quantity,
                    price=p.price,
                    image_url=p.image_url,
                    product_url=p.product_url,
                    category=category,
                )
                batch_new.append(new_mp)
                if p.product_url:
                    existing_by_url[p.product_url] = new_mp
                existing_by_name[(str(market_id), clean_name)] = new_mp
                inserted += 1

        except Exception as exc:
            logger.error("Erro ao processar produto '%s': %s", getattr(p, "product_name", "?"), exc)
            continue

    if batch_new:
        db.add_all(batch_new)
        await db.flush()
        for mp in batch_new:
            batch_history.append(PriceHistory(
                market_product_id=mp.id,
                price=mp.price,
                checked_at=now,
            ))

    if batch_history:
        db.add_all(batch_history)

    if batch_alerts:
        db.add_all(batch_alerts)

    await db.commit()
    return inserted, updated


# ─── Agendamento automático ──────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.refresh_all_prices")
def refresh_all_prices():
    """Agendado pelo Celery Beat: varre tudo a cada 6 horas."""
    logger.info("Iniciando varredura automática agendada...")
    crawl_all_products.delay(None)

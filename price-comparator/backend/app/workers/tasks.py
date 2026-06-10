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

            count = await _save_products(db, market.id, products)

            if job:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.results_count = count
            await db.commit()

        except Exception as exc:
            logger.error("scrape_market falhou para %s: %s", market_id, exc)
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
    """
    Varre TODOS os produtos de um ou todos os mercados,
    sem precisar de termo de busca.
    """
    return run_async(_crawl_all_async(market_id))


async def _crawl_all_async(market_id: str | None):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.market import Market
    from app.models.product import ScrapingJob
    from app.scrapers.connector_manager import ConnectorManager

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        if market_id:
            result = await db.execute(
                select(Market).where(Market.id == market_id, Market.is_active == True)
            )
            markets = [result.scalar_one_or_none()]
            markets = [m for m in markets if m]
        else:
            result = await db.execute(
                select(Market).where(Market.is_active == True)
            )
            markets = result.scalars().all()

        total_saved = 0

        for market in markets:
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

                # Chama crawl_all() se o scraper suportar; senão usa search com termos comuns
                if hasattr(scraper, "crawl_all"):
                    logger.info("Iniciando varredura completa: %s", market.name)
                    products = await scraper.crawl_all()
                else:
                    logger.info("Scraper sem crawl_all, usando termos comuns: %s", market.name)
                    products = []
                    for term in ["arroz", "leite", "cafe", "oleo", "acucar", "feijao"]:
                        results = await scraper.search(term)
                        products.extend(results)

                await scraper.close()

                count = await _save_products(db, market.id, products)
                total_saved += count

                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.results_count = count
                await db.commit()
                logger.info("%s: %d produtos salvos", market.name, count)

            except Exception as exc:
                logger.error("Varredura falhou em %s: %s", market.name, exc)
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

    await engine.dispose()
    logger.info("Varredura completa finalizada. Total: %d produtos", total_saved)
    return total_saved


# ─── Helper: salva/atualiza produtos no banco ────────────────────────────────

async def _save_products(db, market_id, products) -> int:
    from sqlalchemy import select
    from app.models.product import MarketProduct, PriceHistory
    from datetime import datetime, timezone

    count = 0
    for p in products:
        existing = await db.execute(
            select(MarketProduct).where(
                MarketProduct.market_id == market_id,
                MarketProduct.product_url == p.product_url,
            )
        )
        mp = existing.scalar_one_or_none()

        if mp:
            if mp.price != p.price:
                db.add(PriceHistory(market_product_id=mp.id, price=mp.price))
            mp.price = p.price
            mp.name = p.product_name
            mp.image_url = p.image_url or mp.image_url
            mp.last_updated = datetime.now(timezone.utc)
        else:
            mp = MarketProduct(
                market_id=market_id,
                name=p.product_name,
                brand=p.brand,
                quantity=p.quantity,
                price=p.price,
                image_url=p.image_url,
                product_url=p.product_url,
            )
            db.add(mp)
            await db.flush()
            db.add(PriceHistory(market_product_id=mp.id, price=p.price))

        count += 1

    await db.commit()
    return count


# ─── Agendamento automático ──────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.refresh_all_prices")
def refresh_all_prices():
    """Agendado pelo Celery Beat: varre tudo a cada 6 horas."""
    logger.info("Iniciando varredura automática agendada...")
    crawl_all_products.delay(None)

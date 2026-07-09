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
            await db.rollback()
            try:
                result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)[:500]
                    job.completed_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                pass
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
            await db.rollback()
            try:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                pass
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
    from app.models.product import MarketProduct, PriceHistory, PriceAlert, ProductMatchReview
    from app.normalizer.product_normalizer import title_case, parse_product
    from app.services.category_service import classify_product, load_categories
    from app.services.product_matching_service import load_matcher

    if not products:
        return 0, 0

    now = datetime.now(timezone.utc)

    # Load categories for classification
    try:
        cat_dict = await load_categories(db)
    except Exception:
        cat_dict = {}

    # Catálogo mestre pré-carregado em memória — matching O(1)+fuzzy sem consulta por produto
    matcher = await load_matcher(db)

    existing_by_url = {}
    existing_by_name = {}
    result = await db.execute(
        select(MarketProduct).where(MarketProduct.market_id == market_id)
    )
    for mp in result.scalars().all():
        if mp.product_url:
            existing_by_url[mp.product_url] = mp
        existing_by_name[(str(market_id), mp.name)] = mp

    # Junção por market_id em vez de IN (lista de ids) — evita estourar o limite de
    # parâmetros do driver quando o mercado tem um catálogo grande.
    result = await db.execute(
        select(ProductMatchReview)
        .join(MarketProduct, ProductMatchReview.market_product_id == MarketProduct.id)
        .where(MarketProduct.market_id == market_id, ProductMatchReview.status == "pending")
    )
    existing_reviews_by_mp = {r.market_product_id: r for r in result.scalars().all()}

    inserted = 0
    updated = 0
    batch_new: list[MarketProduct] = []
    batch_history: list[PriceHistory] = []
    batch_alerts: list[PriceAlert] = []
    pending_reviews: list[tuple] = []  # (market_product, master_product, score)

    for p in products:
        try:
            clean_name = title_case(p.product_name)
            clean_brand = title_case(p.brand) if p.brand else None
            parsed = parse_product(p.product_name)

            mp = None
            if p.product_url:
                mp = existing_by_url.get(p.product_url)
            if mp is None:
                mp = existing_by_name.get((str(market_id), clean_name))

            if mp:
                if mp.price != p.price and mp.id is not None:
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
                mp.parsed_brand = parsed.parsed_brand or mp.parsed_brand
                mp.parsed_name = parsed.parsed_name or mp.parsed_name
                mp.volume_value = parsed.volume_value or mp.volume_value
                mp.volume_unit = parsed.volume_unit or mp.volume_unit
                mp.volume_base = parsed.volume_base or mp.volume_base
                mp.volume_base_unit = parsed.volume_base_unit or mp.volume_base_unit
                mp.product_type = parsed.product_type or mp.product_type
                mp.is_kit = parsed.is_kit
                mp.is_combo = parsed.is_combo
                mp.pack_quantity = parsed.pack_quantity or mp.pack_quantity
                mp.normalized_at = now

                # Só tenta (re)vincular ao catálogo mestre se ainda não foi resolvido —
                # nunca sobrescreve um vínculo já confirmado (GTIN, similaridade ou revisão manual).
                if mp.master_product_id is None and mp.match_status in ("unmatched", "pending_review"):
                    master, status, score = matcher.match(clean_name, mp.gtin)
                    if status in ("matched_gtin", "matched_similarity"):
                        mp.master_product_id = master.id
                        mp.match_status = status
                        mp.match_confidence = Decimal(str(score))
                        mp.matched_at = now
                    elif status == "pending_review":
                        mp.match_status = status
                        mp.match_confidence = Decimal(str(score))
                        pending_reviews.append((mp, master, score))
                    else:
                        mp.match_status = "unmatched"

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
                    parsed_brand=parsed.parsed_brand,
                    parsed_name=parsed.parsed_name,
                    volume_value=parsed.volume_value,
                    volume_unit=parsed.volume_unit,
                    volume_base=parsed.volume_base,
                    volume_base_unit=parsed.volume_base_unit,
                    product_type=parsed.product_type,
                    is_kit=parsed.is_kit,
                    is_combo=parsed.is_combo,
                    pack_quantity=parsed.pack_quantity,
                    normalized_at=now,
                )

                master, status, score = matcher.match(clean_name, None)
                if status in ("matched_gtin", "matched_similarity"):
                    new_mp.master_product_id = master.id
                    new_mp.match_status = status
                    new_mp.match_confidence = Decimal(str(score))
                    new_mp.matched_at = now
                elif status == "pending_review":
                    new_mp.match_status = status
                    new_mp.match_confidence = Decimal(str(score))
                    pending_reviews.append((new_mp, master, score))

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
        batch_history = [h for h in batch_history if h.market_product_id is not None]
        db.add_all(batch_history)

    if batch_alerts:
        batch_alerts = [a for a in batch_alerts if a.market_product_id is not None]
        db.add_all(batch_alerts)

    for mp, master, score in pending_reviews:
        review = existing_reviews_by_mp.get(mp.id)
        if review is None:
            review = ProductMatchReview(market_product_id=mp.id)
            db.add(review)
        review.candidate_master_product_id = master.id
        review.similarity_score = Decimal(str(score))
        review.match_reasons = {"query": mp.name, "candidate": master.canonical_name}

    await db.flush()

    return inserted, updated


# ─── Tarefa: importação da planilha mestre de GTIN ──────────────────────────

@celery_app.task(bind=True, name="app.workers.tasks.import_master_products")
def import_master_products(self, batch_id: str, file_path: str):
    return run_async(_import_master_products_async(batch_id, file_path))


async def _import_master_products_async(batch_id: str, file_path: str):
    import os
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.product import MasterProductImportBatch
    from app.services.master_product_importer import import_master_products_from_xlsx

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with Session() as db:
            result = await db.execute(
                select(MasterProductImportBatch).where(MasterProductImportBatch.id == batch_id)
            )
            batch = result.scalar_one_or_none()
            if not batch:
                return

            try:
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                await import_master_products_from_xlsx(db, batch, file_bytes)
            except Exception as exc:
                logger.error("Falha ao importar planilha mestre: %s", exc, exc_info=True)
                await db.rollback()
                batch.status = "failed"
                batch.errors = [{"row": 0, "message": str(exc)[:500]}]
                batch.finished_at = datetime.now(timezone.utc)
                await db.commit()
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass
        await engine.dispose()


# ─── Tarefa: reprocessamento do motor de matching contra o catálogo mestre ──

@celery_app.task(name="app.workers.tasks.reprocess_unmatched_task")
def reprocess_unmatched_task():
    return run_async(_reprocess_unmatched_async())


async def _reprocess_unmatched_async():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.core.config import settings
    from app.services.product_matching_service import reprocess_unmatched

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        stats = await reprocess_unmatched(db)

    await engine.dispose()
    return stats


# ─── Agendamento automático ──────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.refresh_all_prices")
def refresh_all_prices():
    """Agendado pelo Celery Beat: varre tudo a cada 6 horas."""
    logger.info("Iniciando varredura automática agendada...")
    crawl_all_products.delay(None)


# ─── Tarefa: re-normalização de produtos existentes ────────────────────────

@celery_app.task(name="app.workers.tasks.normalize_existing_products")
def normalize_existing_products():
    """Re-normalize all existing products that haven't been normalized yet."""
    return run_async(_normalize_existing_async())


async def _normalize_existing_async():
    from app.normalizer.product_normalizer import parse_product
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select, func
    from app.core.config import settings
    from app.models.product import MarketProduct

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    total = 0

    async with Session() as db:
        result = await db.execute(
            select(func.count()).select_from(MarketProduct).where(MarketProduct.normalized_at == None)
        )
        pending = result.scalar() or 0
        logger.info("Re-normalization: %d products pending", pending)

    batch_size = 500
    while True:
        async with Session() as db:
            result = await db.execute(
                select(MarketProduct)
                .where(MarketProduct.normalized_at == None)
                .limit(batch_size)
            )
            products = result.scalars().all()
            if not products:
                break

            for mp in products:
                try:
                    parsed = parse_product(mp.name)
                    mp.parsed_brand = parsed.parsed_brand
                    mp.parsed_name = parsed.parsed_name
                    mp.volume_value = parsed.volume_value
                    mp.volume_unit = parsed.volume_unit
                    mp.volume_base = parsed.volume_base
                    mp.volume_base_unit = parsed.volume_base_unit
                    mp.product_type = parsed.product_type
                    mp.is_kit = parsed.is_kit
                    mp.is_combo = parsed.is_combo
                    mp.pack_quantity = parsed.pack_quantity
                    mp.normalized_at = now
                except Exception as exc:
                    logger.debug("Normalize failed for %s: %s", mp.name, exc)

            await db.commit()
            total += len(products)
            logger.info("Re-normalized %d products (total: %d)", len(products), total)

    await engine.dispose()
    logger.info("Re-normalization complete: %d products processed", total)
    return total

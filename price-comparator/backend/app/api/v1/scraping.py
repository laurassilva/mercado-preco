import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.models.market import Market
from app.models.product import ScrapingJob
from app.schemas.product import ScrapingJobCreate, ScrapingJobResponse
from app.services.product_service import trigger_scraping_jobs

router = APIRouter(prefix="/scraping", tags=["Coleta"])


@router.post("/trigger", response_model=list[ScrapingJobResponse])
async def trigger(
    data: ScrapingJobCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Dispara coleta por termo de busca em todos os mercados ativos."""
    return await trigger_scraping_jobs(data.query, data.market_ids, db)


@router.post("/crawl-all")
async def crawl_all(
    market_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Dispara varredura COMPLETA de todos os produtos (sem precisar de termo de busca).
    Varre todas as categorias de cada mercado ativo.
    """
    from app.workers.tasks import crawl_all_products

    if market_id:
        result = await db.execute(select(Market).where(Market.id == market_id))
        market = result.scalar_one_or_none()
        if not market:
            raise HTTPException(404, "Mercado não encontrado")
        crawl_all_products.delay(str(market_id))
        return {"message": f"Varredura completa iniciada para {market.name}"}

    crawl_all_products.delay(None)
    return {"message": "Varredura completa iniciada para todos os mercados ativos"}


@router.get("/jobs", response_model=list[ScrapingJobResponse])
async def list_jobs(
    limit: int = Query(100, le=500),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = (
        select(ScrapingJob)
        .order_by(ScrapingJob.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(ScrapingJob.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job não encontrado")
    return job

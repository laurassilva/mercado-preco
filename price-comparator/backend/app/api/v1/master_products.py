import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc, and_

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_admin_or_gestor
from app.models.product import MasterProduct, MarketProduct, PriceHistory, ProductMatchReview, MasterProductImportBatch
from app.models.market import Market
from app.models.user import User
from app.schemas.product import MasterProductImportBatchResponse
from app.services.product_matching_service import create_master_product_from_market_product
from app.workers.tasks import import_master_products, reprocess_unmatched_task

router = APIRouter(prefix="/master-products", tags=["Catálogo Mestre"])

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_gtin_query(q: str) -> str | None:
    digits = re.sub(r"\D", "", q)
    return digits.zfill(14) if len(digits) in (8, 12, 13, 14) else None


# ─── Busca / listagem do Catálogo Mestre ─────────────────────────────────────

@router.get("/")
async def search_master_products(
    q: Optional[str] = Query(None, min_length=2),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Busca o Produto Mestre primeiro (por GTIN ou nome/marca/categoria), nunca o produto capturado."""
    from app.scrapers.search_utils import _key_terms

    stmt = (
        select(
            MasterProduct.id,
            MasterProduct.canonical_name,
            MasterProduct.gtin,
            MasterProduct.brand,
            MasterProduct.manufacturer,
            MasterProduct.quantity,
            MasterProduct.category,
            MasterProduct.subcategory,
            MasterProduct.image_url,
            sqlfunc.count(MarketProduct.id).label("market_count"),
            sqlfunc.min(MarketProduct.price).label("min_price"),
            sqlfunc.max(MarketProduct.price).label("max_price"),
            sqlfunc.avg(MarketProduct.price).label("avg_price"),
        )
        .outerjoin(
            MarketProduct,
            and_(MarketProduct.master_product_id == MasterProduct.id, MarketProduct.is_available == True),
        )
        .where(MasterProduct.is_active == True)
        .group_by(MasterProduct.id)
        .having(sqlfunc.count(MarketProduct.id) > 0)
        .order_by(MasterProduct.canonical_name)
    )

    if q:
        gtin_query = _normalize_gtin_query(q)
        if gtin_query:
            stmt = stmt.where(MasterProduct.gtin == gtin_query)
        else:
            key_terms = _key_terms(q)
            for term in key_terms:
                stmt = stmt.where(
                    sqlfunc.f_unaccent(MasterProduct.canonical_name).ilike(f"%{term}%")
                    | sqlfunc.f_unaccent(MasterProduct.brand).ilike(f"%{term}%")
                )

    if category:
        stmt = stmt.where(MasterProduct.category == category)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": str(row.id),
            "canonical_name": row.canonical_name,
            "gtin": row.gtin,
            "brand": row.brand,
            "manufacturer": row.manufacturer,
            "quantity": row.quantity,
            "category": row.category,
            "subcategory": row.subcategory,
            "image_url": row.image_url,
            "market_count": row.market_count,
            "min_price": float(row.min_price) if row.min_price else None,
            "max_price": float(row.max_price) if row.max_price else None,
            "avg_price": round(float(row.avg_price), 2) if row.avg_price else None,
        }
        for row in rows
    ]


@router.get("/stats")
async def master_product_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_master_products = (await db.execute(select(sqlfunc.count()).select_from(MasterProduct))).scalar() or 0

    matched_count = (await db.execute(
        select(sqlfunc.count()).select_from(MarketProduct)
        .where(MarketProduct.match_status.in_(["matched_gtin", "matched_similarity", "matched_legacy"]))
    )).scalar() or 0
    pending_review_count = (await db.execute(
        select(sqlfunc.count()).select_from(MarketProduct).where(MarketProduct.match_status == "pending_review")
    )).scalar() or 0
    unmatched_count = (await db.execute(
        select(sqlfunc.count()).select_from(MarketProduct).where(MarketProduct.match_status == "unmatched")
    )).scalar() or 0

    multi_market = (await db.execute(
        select(sqlfunc.count()).select_from(
            select(MasterProduct.id)
            .join(MarketProduct, MarketProduct.master_product_id == MasterProduct.id)
            .group_by(MasterProduct.id)
            .having(sqlfunc.count(sqlfunc.distinct(MarketProduct.market_id)) >= 2)
            .subquery()
        )
    )).scalar() or 0

    return {
        "total_master_products": total_master_products,
        "matched_count": matched_count,
        "pending_review_count": pending_review_count,
        "unmatched_count": unmatched_count,
        "multi_market_products": multi_market,
    }


@router.get("/{master_product_id}/offers")
async def master_product_offers(
    master_product_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Estilo Booking.com: todos os mercados que possuem este Produto Mestre, ordenado por menor preço."""
    master_result = await db.execute(select(MasterProduct).where(MasterProduct.id == master_product_id))
    master = master_result.scalar_one_or_none()
    if not master:
        raise HTTPException(404, "Produto mestre não encontrado")

    result = await db.execute(
        select(MarketProduct, Market.name.label("market_name"), Market.logo_url.label("market_logo"))
        .join(Market, MarketProduct.market_id == Market.id)
        .where(
            MarketProduct.master_product_id == master_product_id,
            MarketProduct.is_available == True,
        )
        .order_by(MarketProduct.price)
    )
    rows = result.all()
    if not rows:
        raise HTTPException(404, "Nenhuma oferta disponível para este produto")

    min_price = min(float(mp.price) for mp, _, _ in rows if mp.price is not None)

    market_product_ids = [mp.id for mp, _, _ in rows]
    history_result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.market_product_id.in_(market_product_ids))
        .order_by(PriceHistory.checked_at.desc())
    )
    history_by_mp: dict[uuid.UUID, list] = {}
    for h in history_result.scalars().all():
        history_by_mp.setdefault(h.market_product_id, [])
        if len(history_by_mp[h.market_product_id]) < 10:
            history_by_mp[h.market_product_id].append(
                {"price": float(h.price), "checked_at": h.checked_at.isoformat()}
            )

    offers = []
    for mp, market_name, market_logo in rows:
        price = float(mp.price) if mp.price is not None else None
        diff = round(price - min_price, 2) if price is not None else None
        diff_pct = round((diff / min_price) * 100, 2) if diff is not None and min_price else None
        offers.append({
            "market_product_id": str(mp.id),
            "market_id": str(mp.market_id),
            "market_name": market_name,
            "market_logo": market_logo,
            "product_name": mp.name,
            "price": price,
            "original_price": float(mp.original_price) if mp.original_price else None,
            "is_promotion": mp.is_promotion,
            "product_url": mp.product_url,
            "last_updated": mp.last_updated.isoformat() if mp.last_updated else None,
            "difference": diff,
            "difference_pct": diff_pct,
            "is_cheapest": price == min_price,
            "history": history_by_mp.get(mp.id, []),
        })

    return {
        "master_product_id": str(master.id),
        "canonical_name": master.canonical_name,
        "gtin": master.gtin,
        "brand": master.brand,
        "image_url": master.image_url,
        "offers": offers,
    }


# ─── Reprocessamento (substitui o antigo "Reagrupar Tudo") ───────────────────

@router.post("/reprocess-unmatched", status_code=202)
async def reprocess(_=Depends(require_admin)):
    """
    Reprocessa produtos capturados ainda não vinculados contra o catálogo mestre atual.
    Roda em background (Celery) — sobre uma base grande, isso pode levar minutos e
    estouraria o timeout de uma requisição HTTP síncrona.
    """
    reprocess_unmatched_task.delay()
    return {"message": "Reprocessamento iniciado em segundo plano"}


# ─── Importação da planilha mestre de GTIN ───────────────────────────────────

@router.post("/import", response_model=MasterProductImportBatchResponse, status_code=202)
async def import_gtin_spreadsheet(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Envie um arquivo .xlsx")

    batch = MasterProductImportBatch(filename=file.filename, created_by=user.id)
    db.add(batch)
    await db.flush()
    await db.commit()
    await db.refresh(batch)

    file_path = UPLOAD_DIR / f"{batch.id}.xlsx"
    contents = await file.read()
    file_path.write_bytes(contents)

    import_master_products.delay(str(batch.id), str(file_path))

    return batch


@router.get("/import/{batch_id}", response_model=MasterProductImportBatchResponse)
async def import_status(batch_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(MasterProductImportBatch).where(MasterProductImportBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Importação não encontrada")
    return batch


@router.get("/imports", response_model=list[MasterProductImportBatchResponse])
async def import_history(
    limit: int = Query(20, le=100), db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(
        select(MasterProductImportBatch).order_by(MasterProductImportBatch.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ─── Fila de revisão manual ───────────────────────────────────────────────────

@router.get("/reviews")
async def list_reviews(
    status_filter: str = Query("pending", alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin_or_gestor),
):
    stmt = (
        select(ProductMatchReview, MarketProduct.name.label("mp_name"), Market.name.label("market_name"),
               MasterProduct.canonical_name.label("candidate_name"))
        .join(MarketProduct, ProductMatchReview.market_product_id == MarketProduct.id)
        .join(Market, MarketProduct.market_id == Market.id)
        .outerjoin(MasterProduct, ProductMatchReview.candidate_master_product_id == MasterProduct.id)
        .where(ProductMatchReview.status == status_filter)
        .order_by(ProductMatchReview.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": str(review.id),
            "market_product_id": str(review.market_product_id),
            "market_product_name": mp_name,
            "market_name": market_name,
            "candidate_master_product_id": str(review.candidate_master_product_id) if review.candidate_master_product_id else None,
            "candidate_canonical_name": candidate_name,
            "suggested_gtin": review.suggested_gtin,
            "similarity_score": float(review.similarity_score) if review.similarity_score else None,
            "status": review.status,
            "created_at": review.created_at.isoformat(),
        }
        for review, mp_name, market_name, candidate_name in rows
    ]


@router.post("/reviews/{review_id}/approve")
async def approve_review(
    review_id: str,
    master_product_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin_or_gestor),
):
    """Confirma o vínculo — usa o candidato sugerido, ou um master_product_id informado manualmente."""
    result = await db.execute(select(ProductMatchReview).where(ProductMatchReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review or review.status != "pending":
        raise HTTPException(404, "Revisão não encontrada ou já resolvida")

    target_id = master_product_id or (str(review.candidate_master_product_id) if review.candidate_master_product_id else None)
    if not target_id:
        raise HTTPException(400, "Nenhum produto mestre candidato ou informado")

    mp_result = await db.execute(select(MarketProduct).where(MarketProduct.id == review.market_product_id))
    mp = mp_result.scalar_one_or_none()
    if not mp:
        raise HTTPException(404, "Produto capturado não encontrado")

    mp.master_product_id = target_id
    mp.match_status = "matched_similarity"
    mp.matched_at = datetime.now(timezone.utc)

    review.status = "approved"
    review.reviewed_by = user.id
    review.reviewed_at = datetime.now(timezone.utc)
    review.resolution_master_product_id = target_id

    await db.commit()
    return {"message": "Vínculo aprovado"}


@router.post("/reviews/{review_id}/reject")
async def reject_review(
    review_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin_or_gestor),
):
    result = await db.execute(select(ProductMatchReview).where(ProductMatchReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review or review.status != "pending":
        raise HTTPException(404, "Revisão não encontrada ou já resolvida")

    mp_result = await db.execute(select(MarketProduct).where(MarketProduct.id == review.market_product_id))
    mp = mp_result.scalar_one_or_none()
    if mp:
        mp.match_status = "unmatched"

    review.status = "rejected"
    review.reviewed_by = user.id
    review.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    return {"message": "Revisão rejeitada"}


@router.post("/reviews/{review_id}/create-new")
async def create_new_from_review(
    review_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin_or_gestor),
):
    """Cria um Produto Mestre novo a partir do produto capturado e já vincula."""
    result = await db.execute(select(ProductMatchReview).where(ProductMatchReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review or review.status != "pending":
        raise HTTPException(404, "Revisão não encontrada ou já resolvida")

    mp_result = await db.execute(select(MarketProduct).where(MarketProduct.id == review.market_product_id))
    mp = mp_result.scalar_one_or_none()
    if not mp:
        raise HTTPException(404, "Produto capturado não encontrado")

    master = create_master_product_from_market_product(mp, source="manual")
    db.add(master)
    await db.flush()

    mp.master_product_id = master.id
    mp.match_status = "matched_similarity"
    mp.match_confidence = 100
    mp.matched_at = datetime.now(timezone.utc)

    review.status = "approved"
    review.reviewed_by = user.id
    review.reviewed_at = datetime.now(timezone.utc)
    review.resolution_master_product_id = master.id

    await db.commit()
    return {"message": "Produto mestre criado e vinculado", "master_product_id": str(master.id)}

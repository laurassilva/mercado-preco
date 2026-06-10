from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.product import SearchResponse
from app.services.product_service import search_products
from app.services.report_service import generate_pdf, generate_excel, generate_csv

router = APIRouter(prefix="/reports", tags=["Relatórios"])


@router.get("/pdf")
async def export_pdf(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera PDF com comparação de preços para o produto pesquisado."""
    result = await search_products(q, db, current_user.id)
    pdf_bytes = generate_pdf(result)
    filename = f"comparacao_{q.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/excel")
async def export_excel(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera planilha Excel com comparação de preços."""
    result = await search_products(q, db, current_user.id)
    excel_bytes = generate_excel(result)
    filename = f"comparacao_{q.replace(' ', '_')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv")
async def export_csv(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera CSV com comparação de preços."""
    result = await search_products(q, db, current_user.id)
    csv_text = generate_csv(result)
    filename = f"comparacao_{q.replace(' ', '_')}.csv"
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

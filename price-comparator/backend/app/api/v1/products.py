import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.product import SearchResponse
from app.services.product_service import search_products

router = APIRouter(prefix="/products", tags=["Produtos"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, description="Termo de busca"),
    market_ids: Optional[str] = Query(None, description="IDs separados por vírgula"),
    live: bool = Query(True, description="True=scraping ao vivo | False=banco de dados local"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pesquisa produtos.
    - live=true (padrão): consulta ao vivo nos sites dos mercados.
    - live=false: busca no banco de dados local (resultado de varreduras anteriores).
    """
    parsed_market_ids = None
    if market_ids:
        try:
            parsed_market_ids = [
                uuid.UUID(mid.strip())
                for mid in market_ids.split(",")
                if mid.strip()
            ]
        except ValueError:
            parsed_market_ids = None

    return await search_products(
        query=q,
        db=db,
        user_id=current_user.id,
        market_ids=parsed_market_ids,
        live=live,
    )

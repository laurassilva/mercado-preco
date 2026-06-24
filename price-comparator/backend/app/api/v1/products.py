import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import MarketProduct
from app.models.user import User
from app.schemas.product import SearchResponse
from app.services.product_service import search_products

router = APIRouter(prefix="/products", tags=["Produtos"])


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=1, description="Parcial do termo"),
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Autocomplete: retorna sugestões de produtos baseadas no que o usuário está digitando."""
    from app.scrapers.search_utils import _normalize, _correct_typo

    term = _normalize(q)
    if len(term) < 2:
        return {"suggestions": []}

    # Correct potential typo
    words = term.split()
    corrected_words = [_correct_typo(w) if len(w) >= 3 else w for w in words]
    corrected = " ".join(corrected_words)

    # Search using both original and corrected terms
    search_variants = list(set([term, corrected]))

    all_suggestions: list[str] = []
    for variant in search_variants:
        ilike_pattern = f"%{variant}%"
        stmt = (
            select(MarketProduct.name)
            .where(
                MarketProduct.is_available == True,
                MarketProduct.is_kit == False,
                func.f_unaccent(MarketProduct.name).ilike(ilike_pattern),
            )
            .distinct()
            .limit(limit * 3)
        )
        result = await db.execute(stmt)
        names = [row[0] for row in result.all()]
        all_suggestions.extend(names)

    # Deduplicate and score by relevance
    from app.scrapers.search_utils import product_score
    seen = set()
    scored = []
    for name in all_suggestions:
        name_lower = name.lower()
        if name_lower in seen:
            continue
        seen.add(name_lower)
        score = product_score(q, name)
        if score > 30:
            scored.append({"name": name, "score": score})

    scored.sort(key=lambda x: -x["score"])

    # Return top suggestions as clean product names
    from app.normalizer.product_normalizer import title_case
    suggestions = [title_case(s["name"]) for s in scored[:limit]]

    return {"suggestions": suggestions}


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, description="Termo de busca"),
    market_ids: Optional[str] = Query(None, description="IDs separados por vírgula"),
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
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
        category=category,
        live=live,
    )

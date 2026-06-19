import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.market import Market
from app.schemas.market import MarketCreate, MarketUpdate, MarketResponse

router = APIRouter(prefix="/markets", tags=["Mercados"])

_CONNECTOR_LABELS = {
    "brasao":      {"label": "Brasão Supermercados",  "description": "Scraper real – brasao.com.br (HTML server-side)"},
    "superalfa":   {"label": "Super Alfa",             "description": "Scraper real – superalfanumclick.com.br"},
    "mock":        {"label": "Demonstração (Mock)",    "description": "Dados fictícios. Use para testes ou mercados sem scraper dedicado."},
    "vtex":        {"label": "VTEX Genérico",          "description": "API pública VTEX. Informe base_url no config. Ex: {\"base_url\": \"https://www.loja.com.br\"}"},
    "comper":      {"label": "Comper Supermercados",   "description": "Scraper VTEX – comper.com.br. Config: {\"base_url\": \"https://www.comper.com.br\"}"},
    "deliveryfort":{"label": "DeliveryFort",           "description": "Scraper VTEX – deliveryfort.com.br. Config: {\"base_url\": \"https://www.deliveryfort.com.br\"}"},
    "unicooper":   {"label": "Unicooper Supermercados","description": "Scraper Mercafacil – unicoopersupermercados.com.br"},
    "osuper":      {"label": "osuper Genérico",        "description": "Plataforma osuper (SPA React). Informe base_url no config."},
    "superroyal":  {"label": "Super Royal",            "description": "Scraper osuper – superroyal.com.br. Config: {\"base_url\": \"https://superroyal.com.br\"}"},
    "caita":       {"label": "Caita Supermercados",    "description": "Scraper osuper – caitasupermercados.com.br. Config: {\"base_url\": \"https://caitasupermercados.com.br\"}"},
}


@router.get("/connectors")
async def list_connectors(_=Depends(get_current_user)):
    """Lista conectores disponíveis com label e descrição."""
    from app.scrapers.connector_manager import ConnectorManager
    keys = ConnectorManager.available_connectors()
    return [
        {"key": k, **_CONNECTOR_LABELS.get(k, {"label": k, "description": "Conector customizado"})}
        for k in keys
    ]


@router.get("/", response_model=list[MarketResponse])
async def list_markets(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Market).order_by(Market.name))
    return result.scalars().all()


@router.post("/", response_model=MarketResponse, status_code=201)
async def create_market(data: MarketCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    market = Market(**data.model_dump())
    db.add(market)
    await db.commit()
    await db.refresh(market)
    # Dispara varredura automática para popular o banco com os produtos do novo mercado
    try:
        from app.workers.tasks import crawl_all_products
        crawl_all_products.delay(str(market.id))
    except Exception:
        pass  # Não falha o cadastro se o worker não estiver disponível
    return market


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(404, "Mercado não encontrado")
    return market


@router.patch("/{market_id}", response_model=MarketResponse)
async def update_market(
    market_id: uuid.UUID, data: MarketUpdate,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(404, "Mercado não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(market, k, v)
    await db.commit()
    await db.refresh(market)
    return market


@router.delete("/{market_id}", status_code=204)
async def delete_market(market_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(404, "Mercado não encontrado")
    await db.delete(market)
    await db.commit()

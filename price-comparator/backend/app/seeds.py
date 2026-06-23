"""Seeds executados uma vez na inicialização: cria admin e cadastra mercados reais."""
import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.market import Market
from app.models.category import Category
from app.services.category_service import DEFAULT_CATEGORIES

logger = logging.getLogger(__name__)

MARKETS = [
    {
        "name": "Brasão Supermercados – Avenida",
        "url": "https://www.brasao.com.br/avenida",
        "logo_url": "https://www.brasao.com.br/favicon.ico",
        "integration_type": "scraping",
        "scraper_class": "brasao",
        "is_active": True,
        "config": {
            "base_url": "https://www.brasao.com.br",
            "store_path": "/avenida",
        },
    },
    {
        "name": "Super Alfa",
        "url": "https://superalfanumclick.com.br",
        "logo_url": "https://superalfanumclick.com.br/favicon.ico",
        "integration_type": "scraping",
        "scraper_class": "superalfa",
        "is_active": True,
        "config": {
            "base_url": "https://superalfanumclick.com.br",
        },
    },
    {
        "name": "Comper Supermercados",
        "url": "https://www.comper.com.br",
        "logo_url": None,
        "integration_type": "scraping",
        "scraper_class": "comper",
        "is_active": True,
        "config": {"base_url": "https://www.comper.com.br"},
    },
    {
        "name": "DeliveryFort",
        "url": "https://www.deliveryfort.com.br",
        "logo_url": None,
        "integration_type": "scraping",
        "scraper_class": "deliveryfort",
        "is_active": True,
        "config": {"base_url": "https://www.deliveryfort.com.br"},
    },
    {
        "name": "Unicooper Supermercados",
        "url": "https://www.unicoopersupermercados.com.br",
        "logo_url": None,
        "integration_type": "scraping",
        "scraper_class": "unicooper",
        "is_active": True,
        "config": {},
    },
    {
        "name": "Super Royal",
        "url": "https://superroyal.com.br",
        "logo_url": None,
        "integration_type": "scraping",
        "scraper_class": "superroyal",
        "is_active": True,
        "config": {
            "base_url": "https://superroyal.com.br",
            "store_id": 18,
            "instance_id": 8,
        },
    },
    {
        "name": "Caita Supermercados",
        "url": "https://caitasupermercados.com.br",
        "logo_url": None,
        "integration_type": "scraping",
        "scraper_class": "caita",
        "is_active": True,
        "config": {
            "base_url": "https://caitasupermercados.com.br",
            "store_id": 1102,
            "instance_id": 19,
        },
    },
    {
        "name": "Passarela Supermercados",
        "url": "https://www.passarelaemcasa.com.br",
        "logo_url": None,
        "integration_type": "scraping",
        "scraper_class": "passarela",
        "is_active": True,
        "config": {
            "domain": "passarelaemcasa.com.br",
            "org_id": "344",
            "filial_id": "1",
            "cd_id": "1",
            "login_key": "df072f85df9bf7dd71b6811c34bdbaa4f219d98775b56cff9dfa5f8ca1bf8469",
            "base_url": "https://www.passarelaemcasa.com.br",
        },
    },
]


async def run_seeds():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # Admin user
        existing = await db.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        if not existing.scalar_one_or_none():
            db.add(User(
                email=settings.FIRST_ADMIN_EMAIL,
                name=settings.FIRST_ADMIN_NAME,
                password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role="admin",
            ))
            logger.info("Usuário admin criado: %s", settings.FIRST_ADMIN_EMAIL)

        # Mercados reais (remove os antigos e recria)
        existing_markets = (await db.execute(select(Market))).scalars().all()
        existing_names = {m.name for m in existing_markets}

        for market_data in MARKETS:
            if market_data["name"] not in existing_names:
                db.add(Market(**market_data))
                logger.info("Mercado cadastrado: %s", market_data["name"])

        # Remove mercados de demo antigos (mock) se existirem
        old_demo_names = {
            "Assaí Atacadista", "Carrefour", "Pão de Açúcar",
            "Makro", "Extra", "Dia Supermercados",
        }
        for m in existing_markets:
            if m.name in old_demo_names:
                await db.delete(m)
                logger.info("Mercado demo removido: %s", m.name)

        # Categorias padrão
        existing_cats = (await db.execute(select(Category))).scalars().all()
        existing_cat_names = {c.name for c in existing_cats}

        for name, keywords in DEFAULT_CATEGORIES.items():
            if name not in existing_cat_names:
                db.add(Category(name=name, keywords=json.dumps(keywords, ensure_ascii=False)))
                logger.info("Categoria cadastrada: %s", name)

        await db.commit()

    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seeds())

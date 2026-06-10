"""Seeds executados uma vez na inicialização: cria admin e cadastra mercados reais."""
import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.market import Market

logger = logging.getLogger(__name__)

# Apenas os dois mercados reais solicitados
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

        await db.commit()

    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seeds())

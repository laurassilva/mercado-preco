from fastapi import APIRouter
from app.api.v1 import auth, users, markets, products, history, dashboard, scraping, reports

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(markets.router)
api_router.include_router(products.router)
api_router.include_router(history.router)
api_router.include_router(dashboard.router)
api_router.include_router(scraping.router)
api_router.include_router(reports.router)

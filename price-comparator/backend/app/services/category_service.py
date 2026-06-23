"""Serviço de classificação automática de produtos por categoria."""
import json
import logging
import time
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category

logger = logging.getLogger(__name__)

_cache: dict[str, list[str]] = {}
_cache_ts: float = 0
_CACHE_TTL = 600  # 10 minutes


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def classify_product(product_name: str, categories: dict[str, list[str]] | None = None) -> str | None:
    cats = categories or _cache
    if not cats:
        return None

    normalized = _normalize(product_name)
    best_category = None
    best_score = 0

    for category, keywords in cats.items():
        for keyword in keywords:
            kw_norm = _normalize(keyword)
            if kw_norm in normalized:
                score = len(kw_norm)
                if score > best_score:
                    best_score = score
                    best_category = category

    return best_category


async def load_categories(db: AsyncSession) -> dict[str, list[str]]:
    global _cache, _cache_ts
    now = time.time()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    result = await db.execute(select(Category).where(Category.is_active == True))
    categories = result.scalars().all()
    _cache = {cat.name: json.loads(cat.keywords) for cat in categories}
    _cache_ts = now
    return _cache


def invalidate_cache():
    global _cache, _cache_ts
    _cache = {}
    _cache_ts = 0


DEFAULT_CATEGORIES = {
    "Bebidas": ["cerveja", "refrigerante", "suco", "agua mineral", "vinho", "energetico", "cha", "achocolatado", "isotônico", "coca-cola", "pepsi", "guarana", "tonica", "vodka", "whisky", "gin", "espumante", "champagne"],
    "Carnes": ["carne", "frango", "bovina", "suina", "peixe", "file", "costela", "linguica", "salsicha", "hamburguer", "picanha", "alcatra", "patinho", "acém", "cupim", "contra file", "maminha"],
    "Hortifruti": ["alface", "tomate", "cebola", "batata", "banana", "maca", "laranja", "limao", "abacaxi", "melancia", "cenoura", "pepino", "alho", "morango", "uva", "manga", "mamao"],
    "Laticínios": ["queijo", "iogurte", "manteiga", "requeijao", "creme de leite", "leite condensado", "nata", "cream cheese", "leite"],
    "Padaria": ["pao", "bolo", "biscoito", "bolacha", "torrada", "croissant", "rosca"],
    "Limpeza": ["detergente", "sabao", "desinfetante", "agua sanitaria", "amaciante", "alvejante", "esponja", "limpador", "multiuso", "cloro"],
    "Higiene": ["shampoo", "sabonete", "pasta de dente", "creme dental", "escova dental", "desodorante", "papel higienico", "absorvente", "fralda", "condicionador"],
    "Mercearia": ["arroz", "feijao", "macarrao", "oleo", "azeite", "acucar", "sal", "farinha", "molho", "tempero", "extrato", "vinagre", "maionese", "catchup", "mostarda", "sardinha", "atum", "ervilha", "milho"],
    "Frios": ["presunto", "mortadela", "salame", "peito de peru", "apresuntado", "bacon", "copa"],
    "Congelados": ["pizza congelada", "lasanha congelada", "nuggets", "empanado", "sorvete", "hamburguer congelado", "polpa"],
    "Pet Shop": ["racao", "ração", "petisco", "areia", "antipulga", "coleira", "vermifugo"],
}

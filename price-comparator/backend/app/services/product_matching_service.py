"""Serviço de agrupamento inteligente de produtos (Product Master)."""
import logging
import re
import unicodedata
from decimal import Decimal

from rapidfuzz import fuzz
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import MarketProduct, ProductGroup
from app.normalizer.product_normalizer import (
    normalize_text, extract_quantity, normalize_quantity_to_base,
    quantities_are_equivalent,
)

logger = logging.getLogger(__name__)

_BRANDS = [
    "coca cola", "coca-cola", "pepsi", "guarana antarctica", "fanta",
    "skol", "brahma", "heineken", "budweiser", "stella artois", "corona",
    "tio joao", "camil", "kicaldo", "urbano",
    "italac", "piracanjuba", "parmalat", "elegê", "aurora", "tirol",
    "sadia", "perdigão", "seara", "friboi", "marfrig",
    "omo", "ariel", "ace", "brilhante", "surf",
    "neve", "personal", "scott", "mili",
    "colgate", "oral-b", "close up", "sorriso",
    "dove", "rexona", "nivea", "pantene", "head shoulders",
    "nescafe", "nescau", "pilao", "melitta", "tres coracoes", "caboclo",
    "tang", "clight", "del valle",
    "presidente", "renata", "barilla", "adria", "galo",
    "liza", "soya", "salada", "cocamar",
    "union", "cajamar", "alto alegre",
    "qualy", "doriana", "claybom",
    "schweppes", "sprite", "fruki", "antarctica", "sarandi",
]


def _normalize_for_match(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_brand(name: str) -> str | None:
    norm = _normalize_for_match(name)
    best = None
    best_len = 0
    for brand in _BRANDS:
        brand_norm = _normalize_for_match(brand)
        if brand_norm in norm and len(brand_norm) > best_len:
            best = brand
            best_len = len(brand_norm)
    return best


def compute_product_key(name: str) -> str:
    """
    Canonical key for O(1) product grouping.
    Normalizes name, removes quantity tokens, sorts words.
    """
    norm = _normalize_for_match(name)

    val, unit = extract_quantity(name)
    qty_key = ""
    if val and unit:
        base_val, base_unit = normalize_quantity_to_base(val, unit)
        if base_val is not None:
            qty_key = f"_{int(base_val)}{base_unit}"
        else:
            qty_key = f"_{val}{unit}"

    clean = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:kg|g|gr|ml|l|lt|litros?|un|cx|pct|fardo|lata|garrafa|sache)\b",
        "", norm, flags=re.IGNORECASE,
    ).strip()
    clean = re.sub(r"\s+", " ", clean)

    sorted_words = " ".join(sorted(clean.split()))
    return sorted_words + qty_key


def products_match(name_a: str, name_b: str, threshold: int = 75) -> bool:
    qty_match = quantities_are_equivalent(name_a, name_b)
    if qty_match is False:
        return False
    key_a = compute_product_key(name_a)
    key_b = compute_product_key(name_b)
    if key_a == key_b:
        return True
    clean_a = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:kg|g|gr|ml|l|lt|litros?|un|cx|pct)\b",
        "", _normalize_for_match(name_a), flags=re.IGNORECASE,
    ).strip()
    clean_b = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:kg|g|gr|ml|l|lt|litros?|un|cx|pct)\b",
        "", _normalize_for_match(name_b), flags=re.IGNORECASE,
    ).strip()
    return fuzz.token_sort_ratio(clean_a, clean_b) >= threshold


async def group_products_for_market(db: AsyncSession, market_id) -> int:
    """Group ungrouped products using O(n) key lookup."""
    result = await db.execute(
        select(MarketProduct).where(
            MarketProduct.market_id == market_id,
            MarketProduct.product_group_id.is_(None),
            MarketProduct.is_available == True,
        )
    )
    ungrouped = result.scalars().all()
    if not ungrouped:
        return 0

    groups_result = await db.execute(select(ProductGroup))
    key_to_group: dict[str, ProductGroup] = {}
    for g in groups_result.scalars().all():
        key_to_group[compute_product_key(g.canonical_name)] = g

    new_groups: list[ProductGroup] = []

    for mp in ungrouped:
        key = compute_product_key(mp.name)
        group = key_to_group.get(key)
        if group:
            mp.product_group_id = group.id
        else:
            group = ProductGroup(
                canonical_name=mp.name,
                brand=extract_brand(mp.name),
                quantity=None,
                unit=None,
                category=mp.category,
            )
            val, unit = extract_quantity(mp.name)
            if val and unit:
                group.quantity = f"{val}{unit}"
                group.unit = unit
            new_groups.append(group)
            key_to_group[key] = group

    if new_groups:
        db.add_all(new_groups)
        await db.flush()
        for mp in ungrouped:
            if mp.product_group_id is None:
                key = compute_product_key(mp.name)
                g = key_to_group.get(key)
                if g and g.id:
                    mp.product_group_id = g.id

    await db.commit()
    logger.info("Grouped %d products for market %s", len(ungrouped), market_id)
    return len(ungrouped)


async def regroup_all_products(db: AsyncSession) -> int:
    """Re-group ALL products using O(n) key-based matching."""
    await db.execute(MarketProduct.__table__.update().values(product_group_id=None))
    await db.execute(ProductGroup.__table__.delete())
    await db.commit()

    result = await db.execute(
        select(MarketProduct).where(MarketProduct.is_available == True)
    )
    all_products = result.scalars().all()

    key_to_group: dict[str, ProductGroup] = {}
    new_groups: list[ProductGroup] = []

    for mp in all_products:
        key = compute_product_key(mp.name)
        if key not in key_to_group:
            brand = extract_brand(mp.name)
            val, unit = extract_quantity(mp.name)
            group = ProductGroup(
                canonical_name=mp.name,
                brand=brand,
                quantity=f"{val}{unit}" if val and unit else None,
                unit=unit,
                category=mp.category,
            )
            new_groups.append(group)
            key_to_group[key] = group

    db.add_all(new_groups)
    await db.flush()

    for mp in all_products:
        key = compute_product_key(mp.name)
        group = key_to_group.get(key)
        if group:
            mp.product_group_id = group.id

    await db.commit()
    logger.info("Regrouped %d products into %d groups", len(all_products), len(new_groups))
    return len(all_products)

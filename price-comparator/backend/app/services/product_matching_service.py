"""
Motor de matching do Catálogo Mestre de Produtos.

Ordem de resolução para cada MarketProduct capturado:
  1. GTIN exato          -> matched_gtin       (confiança 100)
  2. Bucket O(1) + fuzzy  -> matched_similarity (score >= AUTO_LINK_THRESHOLD)
                          -> pending_review     (REVIEW_THRESHOLD <= score < AUTO_LINK_THRESHOLD)
  3. Caso contrário       -> unmatched

O bucket é a mesma ideia de chave canônica já usada no agrupamento antigo (compute_product_key),
mas agora usada só para reduzir os candidatos comparados por fuzzy score (evita O(n²) quando a
base crescer para centenas de milhares de produtos) — nunca cria um MasterProduct novo sozinho.
Criação de MasterProduct fica restrita à importação da planilha ou à fila de revisão manual.
"""
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import MarketProduct, MasterProduct, ProductMatchReview
from app.normalizer.product_normalizer import parse_product
from app.scrapers.search_utils import product_score_v2

logger = logging.getLogger(__name__)

AUTO_LINK_THRESHOLD = 90.0
REVIEW_THRESHOLD = 70.0


def _alnum(text: str) -> str:
    """Remove tudo que não for letra/número. A lista BRANDS tem grafias como
    'Coca-Cola' e 'Coca Cola' como entradas distintas — sem isso, essas duas
    variantes da mesma marca cairiam em buckets diferentes e nunca seriam
    comparadas pelo fuzzy score, resultando em falso unmatched."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def compute_product_key(name: str) -> str:
    """Chave canônica para bucket O(1): marca + nome (ordenado) + quantidade normalizada."""
    parsed = parse_product(name)
    brand_key = _alnum(parsed.parsed_brand or "")
    name_key = " ".join(sorted((parsed.parsed_name or "").lower().split()))
    qty_key = f"{parsed.volume_base}{parsed.volume_base_unit}" if parsed.volume_base is not None else ""
    return f"{brand_key}|{name_key}|{qty_key}"


class MasterProductMatcher:
    """Índice em memória do catálogo mestre, para matching O(1)+fuzzy sem consultas por produto."""

    def __init__(self, masters: list[MasterProduct]):
        self._by_gtin: dict[str, MasterProduct] = {m.gtin: m for m in masters if m.gtin}
        self._by_key: dict[str, list[MasterProduct]] = {}
        for m in masters:
            self._by_key.setdefault(compute_product_key(m.canonical_name), []).append(m)

    def match(self, mp_name: str, mp_gtin: str | None) -> tuple[MasterProduct | None, str, float | None]:
        """Retorna (master ou None, match_status, confidence)."""
        if mp_gtin and mp_gtin in self._by_gtin:
            return self._by_gtin[mp_gtin], "matched_gtin", 100.0

        candidates = self._by_key.get(compute_product_key(mp_name), [])
        if not candidates:
            return None, "unmatched", None

        best_master, best_score = None, 0.0
        for master in candidates:
            score, _ = product_score_v2(mp_name, master.canonical_name)
            if score > best_score:
                best_master, best_score = master, score

        if best_master and best_score >= AUTO_LINK_THRESHOLD:
            return best_master, "matched_similarity", best_score
        if best_master and best_score >= REVIEW_THRESHOLD:
            return best_master, "pending_review", best_score
        return None, "unmatched", None


async def load_matcher(db: AsyncSession) -> MasterProductMatcher:
    result = await db.execute(select(MasterProduct).where(MasterProduct.is_active == True))
    return MasterProductMatcher(list(result.scalars().all()))


def create_master_product_from_market_product(mp: MarketProduct, source: str = "manual") -> MasterProduct:
    """Cria um novo MasterProduct a partir dos dados já parseados de um MarketProduct."""
    return MasterProduct(
        canonical_name=mp.parsed_name or mp.name,
        brand=mp.parsed_brand or mp.brand,
        quantity=mp.quantity,
        unit=mp.volume_base_unit,
        volume_base=mp.volume_base,
        volume_base_unit=mp.volume_base_unit,
        category=mp.category,
        gtin=mp.gtin,
        gtin_source=source if mp.gtin else None,
    )


async def reprocess_unmatched(db: AsyncSession) -> dict:
    """
    Reprocessa todos os MarketProduct com status unmatched/matched_legacy contra o
    catálogo mestre atual (útil logo após importar a planilha de GTIN).
    Substitui o antigo `regroup_all_products` (que criava ProductGroup cegamente por nome).
    """
    now = datetime.now(timezone.utc)
    matcher = await load_matcher(db)

    result = await db.execute(
        select(MarketProduct).where(
            MarketProduct.match_status.in_(["unmatched", "matched_legacy"]),
            MarketProduct.is_available == True,
        )
    )
    products = list(result.scalars().all())

    # Fila de revisão pendente é tipicamente pequena (curadoria manual) — busca sem filtro por
    # lista de IDs para não estourar o limite de parâmetros do driver quando a base é grande.
    existing_reviews = await db.execute(
        select(ProductMatchReview).where(ProductMatchReview.status == "pending")
    )
    reviews_by_mp = {r.market_product_id: r for r in existing_reviews.scalars().all()}

    counts = {"matched_gtin": 0, "matched_similarity": 0, "pending_review": 0, "unmatched": 0}

    for mp in products:
        master, status, score = matcher.match(mp.name, mp.gtin)
        counts[status] += 1

        if status in ("matched_gtin", "matched_similarity"):
            mp.master_product_id = master.id
            mp.match_status = status
            mp.match_confidence = Decimal(str(score))
            mp.matched_at = now
        elif status == "pending_review":
            mp.match_status = status
            mp.match_confidence = Decimal(str(score))
            review = reviews_by_mp.get(mp.id)
            if review is None:
                review = ProductMatchReview(market_product_id=mp.id)
                db.add(review)
            review.candidate_master_product_id = master.id
            review.similarity_score = Decimal(str(score))
            review.match_reasons = {"query": mp.name, "candidate": master.canonical_name}
        else:
            mp.match_status = "unmatched"

    await db.commit()
    logger.info("Reprocessados %d produtos: %s", len(products), counts)
    return {"total": len(products), **counts}

"""
Utilitários de filtragem e scoring de produtos por relevância.
Usa rapidfuzz token_set_ratio + penalidade por quantidade incompatível.
"""
import re
import unicodedata

from rapidfuzz import fuzz


_STOP = {
    "de", "do", "da", "dos", "das", "com", "sem", "para", "por",
    "kg", "g", "gr", "ml", "lt", "l", "un", "pc", "cx", "pct",
    "und", "emb", "pacote", "caixa", "lata", "pet", "vidro", "tp",
}

_PET_MARKERS = re.compile(
    r"\b(para cao|para caes|para gato|para gatos|alimento cao|alimento caes|"
    r"racao|racoes|pet food|dog|cat food|coleira|antipulga|vermifugo|"
    r"aquario|passaro|hamster)\b",
    re.IGNORECASE,
)

_KIT_MARKERS = re.compile(
    r"\b(kit|pack|combo|fardo|caixa c\s*/|c\s*/\s*\d+|leve \d+ pague|"
    r"\d+\s*un\b|\d+\s*unid)\b"
    r"|[+]"
    r"|\b\d+lt\s*/\s*\w",
    re.IGNORECASE,
)

_ZERO_MARKERS_NORM = re.compile(
    r"\b(zero|sem acucar|0 acucar|diet|light|low carb|sugar free)\b",
)

_ZERO_MARKERS_RAW = re.compile(
    r"0\s*%",
)

_RETURNABLE_MARKERS_NORM = re.compile(
    r"\b(retornavel|vasilhame|casco)\b",
)


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.strip()


def _key_terms(query: str) -> list[str]:
    words = _normalize(query).split()
    return [w for w in words if len(w) >= 2 and w not in _STOP]


def _term_present(term: str, p_norm: str) -> bool:
    if re.search(r"\b" + re.escape(term) + r"\b", p_norm):
        return True
    m = re.match(r"^(\d+)([a-z]{1,3})$", term)
    if m:
        num, unit = m.groups()
        return bool(re.search(rf"\b{re.escape(num)}\s*{re.escape(unit)}", p_norm))
    return False


def _query_mentions(query: str, pattern: re.Pattern) -> bool:
    return bool(pattern.search(query))


def product_score(query: str, product_name: str) -> float:
    """
    Retorna score de 0-100 de relevância entre query e nome do produto.

    Filtra automaticamente:
    - Kits/packs/combos (a menos que a query mencione kit/pack)
    - Zero/Diet/Light quando a query pede original (e vice-versa)
    - Retornáveis (a menos que a query mencione retornável)
    - Produtos pet quando a query não menciona pet
    """
    from app.normalizer.product_normalizer import quantities_are_equivalent

    q_norm = _normalize(query)
    p_norm = _normalize(product_name)

    # --- Filtros de exclusão ---

    # Pet
    if _PET_MARKERS.search(p_norm) and not _PET_MARKERS.search(q_norm):
        return 0.0

    # Kits: exclui se produto é kit mas query não pede kit
    if _KIT_MARKERS.search(product_name) and not _query_mentions(query, _KIT_MARKERS):
        return 0.0

    # Retornáveis: exclui se produto é retornável mas query não pede (usa texto normalizado)
    if _RETURNABLE_MARKERS_NORM.search(p_norm) and not _RETURNABLE_MARKERS_NORM.search(q_norm):
        return 0.0

    # Zero/Diet vs Original
    product_is_zero = bool(_ZERO_MARKERS_NORM.search(p_norm)) or bool(_ZERO_MARKERS_RAW.search(product_name))
    query_is_zero = bool(_ZERO_MARKERS_NORM.search(q_norm)) or bool(_ZERO_MARKERS_RAW.search(query))
    if product_is_zero and not query_is_zero:
        return 0.0
    if query_is_zero and not product_is_zero:
        return 0.0

    # --- Scoring normal ---

    base = fuzz.token_set_ratio(q_norm, p_norm)

    key = _key_terms(query)
    if not key:
        return base

    qty_match = quantities_are_equivalent(query, product_name)
    if qty_match is False:
        return 0.0

    present = sum(1 for t in key if _term_present(t, p_norm))
    coverage = present / len(key)

    if coverage == 0:
        return 0.0

    if len(key) >= 2 and coverage < 0.75:
        return 0.0

    if len(key) >= 2:
        primary = next((t for t in key if not re.match(r"^\d", t)), None)
        if primary and not _term_present(primary, p_norm):
            return 0.0

    final = base * (0.5 + 0.5 * coverage)
    return final


def filter_products(query: str, products: list, min_score: float = 55.0) -> list:
    scored = [(p, product_score(query, p.product_name)) for p in products]
    relevant = [(p, s) for p, s in scored if s >= min_score]
    relevant.sort(key=lambda x: -x[1])
    return [p for p, _ in relevant]

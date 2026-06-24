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


def product_score_v2(query: str, product_name: str) -> tuple[float, dict]:
    """
    Weighted scoring: 40% brand, 30% name, 20% volume, 10% type.
    Returns (score_0_to_100, breakdown_dict).
    """
    from app.normalizer.product_normalizer import parse_product

    q_parsed = parse_product(query)
    p_parsed = parse_product(product_name)

    q_norm = _normalize(query)
    p_norm = _normalize(product_name)

    # ---- HARD FILTERS ----
    if _PET_MARKERS.search(p_norm) and not _PET_MARKERS.search(q_norm):
        return 0.0, {}

    if (p_parsed.is_kit or p_parsed.is_combo) and not (q_parsed.is_kit or q_parsed.is_combo):
        return 0.0, {}

    if _RETURNABLE_MARKERS_NORM.search(p_norm) and not _RETURNABLE_MARKERS_NORM.search(q_norm):
        return 0.0, {}

    # Type mismatch
    if p_parsed.product_type and q_parsed.product_type:
        if p_parsed.product_type != q_parsed.product_type:
            return 0.0, {}
    elif p_parsed.product_type in ("zero", "diet", "light") and not q_parsed.product_type:
        return 0.0, {}
    elif q_parsed.product_type in ("zero", "diet", "light") and not p_parsed.product_type:
        return 0.0, {}

    # Volume mismatch
    if q_parsed.volume_base is not None and p_parsed.volume_base is not None:
        if q_parsed.volume_base_unit == p_parsed.volume_base_unit:
            if q_parsed.volume_base != p_parsed.volume_base:
                return 0.0, {}

    # ---- WEIGHTED SCORING ----

    # Brand (40%)
    brand_score = 100.0
    if q_parsed.parsed_brand:
        if p_parsed.parsed_brand:
            brand_score = fuzz.token_sort_ratio(
                _normalize(q_parsed.parsed_brand),
                _normalize(p_parsed.parsed_brand),
            )
        elif _normalize(q_parsed.parsed_brand) in p_norm:
            brand_score = 80.0
        else:
            brand_score = 0.0

    # Name (30%)
    q_name = _normalize(q_parsed.parsed_name) if q_parsed.parsed_name else q_norm
    p_name = _normalize(p_parsed.parsed_name) if p_parsed.parsed_name else p_norm
    name_score = float(fuzz.token_set_ratio(q_name, p_name))

    key = _key_terms(query)
    if key:
        present = sum(1 for t in key if _term_present(t, p_norm))
        coverage = present / len(key) if key else 0
        name_score = name_score * (0.6 + 0.4 * coverage)
        if len(key) >= 2 and coverage < 0.5:
            return 0.0, {}

    # Volume (20%)
    volume_score = 100.0
    if q_parsed.volume_base is not None:
        if p_parsed.volume_base is not None:
            if (q_parsed.volume_base_unit == p_parsed.volume_base_unit
                    and q_parsed.volume_base == p_parsed.volume_base):
                volume_score = 100.0
            else:
                volume_score = 0.0
        else:
            volume_score = 50.0

    # Type (10%)
    type_score = 100.0
    if q_parsed.product_type and p_parsed.product_type:
        type_score = 100.0 if q_parsed.product_type == p_parsed.product_type else 0.0

    final = (brand_score * 0.40) + (name_score * 0.30) + (volume_score * 0.20) + (type_score * 0.10)

    breakdown = {
        "brand": round(brand_score, 1),
        "name": round(name_score, 1),
        "volume": round(volume_score, 1),
        "type": round(type_score, 1),
    }
    return round(final, 1), breakdown


def product_score(query: str, product_name: str) -> float:
    score, _ = product_score_v2(query, product_name)
    return score


def filter_products(query: str, products: list, min_score: float = 55.0) -> list:
    scored = [(p, product_score(query, p.product_name)) for p in products]
    relevant = [(p, s) for p, s in scored if s >= min_score]
    relevant.sort(key=lambda x: -x[1])
    return [p for p, _ in relevant]

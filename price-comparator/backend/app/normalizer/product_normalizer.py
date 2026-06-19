import re
from decimal import Decimal
from rapidfuzz import fuzz


UNIT_PATTERNS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(kg|g|gr|ml|l|lt|litro|litros|unid|un|pç|cx|caixa|pacote|fardo|lata|garrafa|sache)",
    re.IGNORECASE,
)

STOP_WORDS = {"de", "do", "da", "dos", "das", "com", "sem", "para", "em", "ao", "à"}

_UNIT_NORM = {
    "lt": "L", "litro": "L", "litros": "L", "l": "L",
    "kg": "kg", "g": "g", "gr": "g", "ml": "ml",
    "unid": "un", "un": "un", "pç": "un",
    "cx": "cx", "caixa": "cx", "pacote": "pct",
    "fardo": "fardo", "lata": "lata", "garrafa": "garrafa",
    "sache": "sachê",
}


def normalize_text(text: str) -> str:
    """Lowercase, strip accents, punctuation, stop words."""
    import unicodedata
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


def extract_quantity(text: str) -> tuple[str | None, str | None]:
    """Return (value_str, normalized_unit) from text if a quantity is found."""
    match = UNIT_PATTERNS.search(text)
    if match:
        value = match.group(1).replace(",", ".")
        unit = match.group(2).lower()
        return value, _UNIT_NORM.get(unit, unit)
    return None, None


def normalize_quantity_to_base(value_str: str, unit: str) -> tuple[Decimal | None, str | None]:
    """
    Convert quantity to a common base unit for comparison:
    - All volumes → ml  (L→ml, lt→ml)
    - All weights → g   (kg→g)
    Returns (normalized_value, base_unit) or (None, None) if unit is unknown.
    """
    try:
        value = Decimal(value_str)
    except Exception:
        return None, None

    u = unit.lower()
    if u == "ml":
        return value, "ml"
    if u in ("l", "lt", "litro", "litros"):
        return value * 1000, "ml"
    if u == "g":
        return value, "g"
    if u == "kg":
        return value * 1000, "g"

    return None, None


def quantities_are_equivalent(name_a: str, name_b: str) -> bool | None:
    """
    Compare the quantities present in two product name strings.

    Returns:
      True  → quantities match (or neither name has a quantity → treated as equivalent)
      False → quantities differ (e.g. 2L vs 200ml)
      None  → one name has a quantity and the other does not (inconclusive)
    """
    val_a, unit_a = extract_quantity(name_a)
    val_b, unit_b = extract_quantity(name_b)

    if val_a is None and val_b is None:
        return True

    if val_a is None or val_b is None:
        return None  # inconclusive — don't hard-reject

    norm_a, base_a = normalize_quantity_to_base(val_a, unit_a)
    norm_b, base_b = normalize_quantity_to_base(val_b, unit_b)

    if norm_a is None or norm_b is None:
        # Can't normalize to base → raw string comparison
        return val_a == val_b and unit_a == unit_b

    if base_a != base_b:
        return False  # different dimensions (volume vs weight)

    return norm_a == norm_b


def products_are_similar(name_a: str, name_b: str, threshold: int = 72) -> bool:
    """
    Return True only if two product names refer to the same product AND the same variant.
    Quantity mismatch (e.g. 2L vs 200ml) is treated as a hard rejection.
    """
    qty_match = quantities_are_equivalent(name_a, name_b)
    if qty_match is False:
        return False

    a = normalize_text(name_a)
    b = normalize_text(name_b)

    # Remove quantity tokens before text similarity to avoid inflating the score
    qty_re = re.compile(
        r"\d+(?:[.,]\d+)?\s*(?:kg|g|gr|ml|l|lt|litros?|un|cx|pct|fardo|lata|garrafa|sache)",
        re.IGNORECASE,
    )
    a_no_qty = qty_re.sub("", a).strip()
    b_no_qty = qty_re.sub("", b).strip()

    if not a_no_qty or not b_no_qty:
        return fuzz.token_sort_ratio(a, b) >= threshold

    return fuzz.token_sort_ratio(a_no_qty, b_no_qty) >= threshold


def extract_features(name: str) -> dict:
    """
    Extract structured features from a product name for intelligent comparison.
    Returns: main_desc, quantity_value, quantity_unit, quantity_base_value, quantity_base_unit
    """
    val, unit = extract_quantity(name)
    norm_val, base_unit = normalize_quantity_to_base(val, unit) if val else (None, None)

    clean = UNIT_PATTERNS.sub("", name).strip()
    clean = re.sub(r"\s+", " ", clean)

    return {
        "main_desc": normalize_text(clean),
        "quantity_value": val,
        "quantity_unit": unit,
        "quantity_base_value": float(norm_val) if norm_val is not None else None,
        "quantity_base_unit": base_unit,
    }


def title_case(name: str) -> str:
    """
    Padroniza o nome do produto: primeira letra de cada palavra maiúscula.
    Ex: "leite integral italac tp 1l" → "Leite Integral Italac Tp 1L"
    """
    if not name:
        return name
    return name.strip().title()


def canonical_name(name: str) -> str:
    """Return a cleaned canonical product name for grouping."""
    normalized = normalize_text(name)
    return " ".join(sorted(normalized.split()))

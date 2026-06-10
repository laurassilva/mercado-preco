import re
from rapidfuzz import fuzz


UNIT_PATTERNS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|lt|litro|litros|unid|un|pç|cx|caixa|pacote|fardo|lata|garrafa|sache)",
    re.IGNORECASE,
)

STOP_WORDS = {"de", "do", "da", "dos", "das", "com", "sem", "para", "em", "ao", "à"}


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
    """Return (value, unit) from product name if found."""
    match = UNIT_PATTERNS.search(text)
    if match:
        value = match.group(1).replace(",", ".")
        unit = match.group(2).lower()
        unit_map = {"lt": "L", "litro": "L", "litros": "L", "l": "L",
                    "kg": "kg", "g": "g", "ml": "ml",
                    "unid": "un", "un": "un", "pç": "un",
                    "cx": "cx", "caixa": "cx", "pacote": "pct",
                    "fardo": "fardo", "lata": "lata", "garrafa": "garrafa",
                    "sache": "sachê"}
        return value, unit_map.get(unit, unit)
    return None, None


def products_are_similar(name_a: str, name_b: str, threshold: int = 72) -> bool:
    """Return True if two product names likely refer to the same product."""
    a = normalize_text(name_a)
    b = normalize_text(name_b)
    return fuzz.token_sort_ratio(a, b) >= threshold


def canonical_name(name: str) -> str:
    """Return a cleaned canonical product name for grouping."""
    normalized = normalize_text(name)
    return " ".join(sorted(normalized.split()))

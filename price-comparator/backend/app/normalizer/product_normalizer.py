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


from dataclasses import dataclass


@dataclass
class ParsedProduct:
    original_name: str
    parsed_brand: str | None
    parsed_name: str
    volume_value: Decimal | None
    volume_unit: str | None
    volume_base: Decimal | None
    volume_base_unit: str | None
    product_type: str | None
    is_kit: bool
    is_combo: bool
    pack_quantity: int | None


_KIT_RE = re.compile(
    r"\b(?:kit|pack|fardo|caixa)\s*(?:c\s*/\s*)?(\d+)?\s*(?:un|unid|und|lata|pet|garrafa)?\b"
    r"|\b(\d+)\s*(?:un|unid|und)\b"
    r"|\bleve\s+(\d+)\s*pague\b",
    re.IGNORECASE,
)

_COMBO_RE = re.compile(r"\bcombo\b|\+", re.IGNORECASE)

_TYPE_PATTERNS = [
    (re.compile(r"\b(?:zero|sem a[cç][uú]car|sugar free|0\s*%\s*a[cç][uú]car)\b", re.IGNORECASE), "zero"),
    (re.compile(r"\bdie(?:t|ta)\b", re.IGNORECASE), "diet"),
    (re.compile(r"\b(?:light|lite)\b", re.IGNORECASE), "light"),
    (re.compile(r"\b(?:semi[\s-]?desnatado)\b", re.IGNORECASE), "semi_desnatado"),
    (re.compile(r"\bdesnatado\b", re.IGNORECASE), "desnatado"),
    (re.compile(r"\bintegral\b", re.IGNORECASE), "integral"),
    (re.compile(r"\blow\s*carb\b", re.IGNORECASE), "low_carb"),
]

BRANDS = [
    "Coca-Cola", "Coca Cola", "Pepsi", "Guaraná Antarctica", "Guarana Antarctica",
    "Fanta", "Sprite", "Kuat", "Dolly", "Tubaina",
    "Skol", "Brahma", "Antarctica", "Heineken", "Budweiser", "Stella Artois",
    "Itaipava", "Crystal", "Original", "Bohemia", "Devassa", "Colorado",
    "Nestlé", "Nestle", "Nescafé", "Nescafe", "Nescau", "Mucilon",
    "Italac", "Piracanjuba", "Elegê", "Elege", "Parmalat", "Vigor", "Danone",
    "Tirol", "Itambé", "Itambe", "Quatá", "Quata", "Nilza", "Shefa",
    "Sadia", "Perdigão", "Perdigao", "Aurora", "Seara", "Frimesa", "Copacol",
    "BRF", "Marfrig", "JBS", "Minerva", "Friboi",
    "Tio João", "Tio Joao", "Camil", "Kicaldo", "Prato Fino", "Urbano",
    "Pilecco Nobre", "Namorado", "Panelão", "Panelaco",
    "União", "Uniao", "Caravelas", "Alto Alegre", "Guarani", "Da Barra",
    "Dona Benta", "Sol", "Renata", "Adria", "Barilla", "Galo",
    "Liza", "Soya", "Concordia", "Salada", "Coamo",
    "Ypê", "Ype", "Brilhante", "Omo", "Ariel", "Ace", "Tixan",
    "Comfort", "Downy", "Mon Bijou", "Fofo",
    "Veja", "Cif", "Ajax", "Pinho Sol", "Pato", "Harpic", "Lysol",
    "Colgate", "Oral-B", "Sensodyne", "Close Up",
    "Dove", "Lux", "Palmolive", "Protex", "Nivea",
    "Rexona", "Axe", "Old Spice", "Bozzano",
    "Pantene", "Head Shoulders", "TRESemmé", "TRESemme", "Seda", "Elseve",
    "Huggies", "Pampers", "Babysec", "Personal",
    "Neve", "Hig", "Mili",
    "Pedigree", "Whiskas", "Golden", "Premier", "Royal Canin",
    "3 Corações", "3 Coracoes", "Melitta", "Pilão", "Pilao", "Café Pelé", "Cafe Pele",
    "Toddy", "Ovomaltine", "Toddynho",
    "Tang", "Clight", "Mid",
    "Gatorade", "Powerade", "Monster", "Red Bull",
    "Leão", "Leao", "Matte Leão", "Matte Leao",
    "Yoki", "Kitano", "Sazon", "Knorr", "Maggi",
    "Hellmanns", "Hellmann's", "Heinz", "Fugini",
    "Quero", "Predilecta", "Elefante", "Pomarola", "Tarantella",
    "Bauducco", "Visconti", "Marilan", "Fortaleza", "Piraquê", "Piraque",
    "Lacta", "Garoto", "Nestlé", "Arcor", "Ferrero",
    "Presidente", "Catupiry", "Polenghi", "Vigor", "Tirolez",
    "Philadelphia", "Danubio",
    "Kodilar", "Jasmine", "Vitao", "Mae Terra", "Mãe Terra",
    "Qualitá", "Qualita", "Carrefour", "Great Value", "Dia",
    "Member's Mark", "Members Mark",
]

_BRAND_RE = None


def _get_brand_re():
    global _BRAND_RE
    if _BRAND_RE is None:
        sorted_brands = sorted(BRANDS, key=len, reverse=True)
        escaped = [re.escape(b) for b in sorted_brands]
        _BRAND_RE = re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)
    return _BRAND_RE


def _extract_brand(name: str) -> tuple[str | None, str]:
    """Extract brand from product name. Returns (brand, name_without_brand)."""
    pattern = _get_brand_re()
    match = pattern.search(name)
    if match:
        brand = match.group(1)
        clean = name[:match.start()] + name[match.end():]
        clean = re.sub(r"\s{2,}", " ", clean).strip()
        for b in BRANDS:
            if b.lower() == brand.lower():
                brand = b
                break
        return brand, clean
    return None, name


def _detect_kit(name: str) -> tuple[bool, bool, int | None, str]:
    """Detect kit/combo and extract pack quantity. Returns (is_kit, is_combo, pack_qty, cleaned_name)."""
    is_kit = False
    is_combo = False
    pack_qty = None
    working = name

    combo_match = _COMBO_RE.search(working)
    if combo_match:
        is_combo = True
        working = working[:combo_match.start()] + working[combo_match.end():]

    kit_match = _KIT_RE.search(working)
    if kit_match:
        is_kit = True
        qty = kit_match.group(1) or kit_match.group(2) or kit_match.group(3)
        if qty:
            pack_qty = int(qty)
        working = working[:kit_match.start()] + working[kit_match.end():]

    working = re.sub(r"\s{2,}", " ", working).strip()
    return is_kit, is_combo, pack_qty, working


def _detect_type(name: str) -> str | None:
    """Detect product type variant (zero, diet, integral, etc.)."""
    norm = normalize_text(name)
    for pattern, ptype in _TYPE_PATTERNS:
        if pattern.search(name) or pattern.search(norm):
            return ptype
    return None


def parse_product(name: str) -> ParsedProduct:
    """Parse a product name into structured components."""
    original = name
    working = name.strip()

    # 1. Kit/combo detection
    is_kit, is_combo, pack_qty, working = _detect_kit(working)

    # 2. Type detection
    product_type = _detect_type(working)

    # 3. Quantity extraction
    vol_val, vol_unit = extract_quantity(working)
    vol_base, vol_base_unit = (None, None)
    volume_value = None
    if vol_val and vol_unit:
        try:
            volume_value = Decimal(vol_val)
        except Exception:
            pass
        vol_base, vol_base_unit = normalize_quantity_to_base(vol_val, vol_unit)
        # Remove quantity from working name
        qty_match = UNIT_PATTERNS.search(working)
        if qty_match:
            working = working[:qty_match.start()] + working[qty_match.end():]
            working = re.sub(r"\s{2,}", " ", working).strip()

    # 4. Brand extraction
    brand, working = _extract_brand(working)

    # 5. Clean remaining name
    parsed_name = re.sub(r"[-–/]", " ", working)
    parsed_name = re.sub(r"[^a-zA-ZÀ-ÿ0-9\s]", "", parsed_name)
    parsed_name = re.sub(r"\s{2,}", " ", parsed_name).strip()
    parsed_name = title_case(parsed_name) if parsed_name else title_case(original)

    # Normalize unit for display
    display_unit = _UNIT_NORM.get(vol_unit, vol_unit) if vol_unit else None

    return ParsedProduct(
        original_name=original,
        parsed_brand=brand,
        parsed_name=parsed_name,
        volume_value=volume_value,
        volume_unit=display_unit,
        volume_base=vol_base,
        volume_base_unit=vol_base_unit,
        product_type=product_type,
        is_kit=is_kit,
        is_combo=is_combo,
        pack_quantity=pack_qty,
    )

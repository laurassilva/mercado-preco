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

# Indicadores de produto para animais/ração — filtra resultado quando
# a query NÃO menciona explicitamente ração/animal
_PET_MARKERS = re.compile(
    r"\b(para cao|para caes|para gato|para gatos|alimento cao|alimento caes|"
    r"racao|racoes|pet food|dog|cat food|coleira|antipulga|vermifugo|"
    r"aquario|passaro|hamster)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Remove acentos, hífens viram espaço, lowercase."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.strip()


def _key_terms(query: str) -> list[str]:
    """Extrai os termos significativos da query (sem stop words e unitários puros)."""
    words = _normalize(query).split()
    return [w for w in words if len(w) >= 2 and w not in _STOP]


def _term_present(term: str, p_norm: str) -> bool:
    """Verifica se um termo está no produto, com flexibilidade para unidades de medida.

    "1l" coincide com "1lt", "1 l", "1litro"; "5kg" coincide com "5 kg", "5kgs".
    """
    if re.search(r"\b" + re.escape(term) + r"\b", p_norm):
        return True
    # Para termos numérico+unidade (ex: "1l", "350ml"), aceita variantes do sufixo
    m = re.match(r"^(\d+)([a-z]{1,3})$", term)
    if m:
        num, unit = m.groups()
        return bool(re.search(rf"\b{re.escape(num)}\s*{re.escape(unit)}", p_norm))
    return False


def product_score(query: str, product_name: str) -> float:
    """
    Retorna score de 0-100 de relevância entre query e nome do produto.

    Estratégia:
    1. token_set_ratio geral (normaliza ordem e tokens extra)
    2. Penaliza com 0 quando a query especifica uma quantidade incompatível
    3. Exige que o primeiro termo significativo (não numérico) esteja presente
       — evita falsos positivos por adjetivos/unidades comuns (ex: "integral")
    4. Recompensa cobertura proporcional dos termos-chave
    """
    from app.normalizer.product_normalizer import quantities_are_equivalent

    q_norm = _normalize(query)
    p_norm = _normalize(product_name)

    # Filtra produtos para animais/ração quando a query não menciona pet/animal
    if _PET_MARKERS.search(p_norm) and not _PET_MARKERS.search(q_norm):
        return 0.0

    base = fuzz.token_set_ratio(q_norm, p_norm)

    key = _key_terms(query)
    if not key:
        return base

    # Verificação de compatibilidade de quantidade
    qty_match = quantities_are_equivalent(query, product_name)
    if qty_match is False:
        return 0.0

    # Cobertura: quantos termos-chave aparecem no nome do produto
    present = sum(1 for t in key if _term_present(t, p_norm))
    coverage = present / len(key)

    if coverage == 0:
        return 0.0

    # Para queries com 2+ termos: exige pelo menos 75% de cobertura.
    # Para 2 termos: ambos devem estar (50% < 75%).
    # Para 3 termos: todos devem estar (67% < 75%).
    # Para 4+ termos: permite faltar 1 (75% passa).
    if len(key) >= 2 and coverage < 0.75:
        return 0.0

    # O primeiro termo não-numérico (nome do produto) DEVE estar presente.
    # Ex: "água de coco integral 1l" não deve casar com "leite integral 1l"
    if len(key) >= 2:
        primary = next((t for t in key if not re.match(r"^\d", t)), None)
        if primary and not _term_present(primary, p_norm):
            return 0.0

    final = base * (0.5 + 0.5 * coverage)
    return final


def filter_products(query: str, products: list, min_score: float = 55.0) -> list:
    """
    Filtra lista de ProductResult mantendo apenas os relevantes.
    Nunca retorna produtos com score abaixo de min_score.
    Ordena por relevância decrescente.
    """
    scored = [(p, product_score(query, p.product_name)) for p in products]
    relevant = [(p, s) for p, s in scored if s >= min_score]
    relevant.sort(key=lambda x: -x[1])
    return [p for p, _ in relevant]

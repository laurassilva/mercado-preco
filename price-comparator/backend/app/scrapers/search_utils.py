"""
Utilitários de filtragem e scoring de produtos por relevância.
Usa rapidfuzz token_set_ratio que é superior ao partial_ratio para nomes de produtos.
"""
import re
import unicodedata
from decimal import Decimal

from rapidfuzz import fuzz


# Palavras que não são termos de produto significativos (unidades, preposições, etc.)
_STOP = {
    "de", "do", "da", "dos", "das", "com", "sem", "para", "por",
    "kg", "g", "gr", "ml", "lt", "l", "un", "pc", "cx", "pct",
    "und", "emb", "pacote", "caixa", "lata", "pet", "vidro", "tp",
}


def _normalize(text: str) -> str:
    """Remove acentos, hífens viram espaço, lowercase."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.strip()


def _key_terms(query: str) -> list[str]:
    """Extrai os termos significativos da query (sem stop words e unitários)."""
    words = _normalize(query).split()
    return [w for w in words if len(w) >= 2 and w not in _STOP]


def product_score(query: str, product_name: str) -> float:
    """
    Retorna score de 0-100 de relevância entre query e nome do produto.

    Estratégia:
    1. token_set_ratio geral (normaliza ordem e tokens extra)
    2. Penaliza se nenhum termo-chave da query aparece no nome
    3. Recompensa correspondências exatas de substring
    """
    q_norm = _normalize(query)
    p_norm = _normalize(product_name)

    # Score base: token_set_ratio funciona bem com descrições de produto
    base = fuzz.token_set_ratio(q_norm, p_norm)

    # Termos chave obrigatórios
    key = _key_terms(query)
    if not key:
        return base

    # Quantos termos chave aparecem no nome como palavra completa
    present = sum(1 for t in key if re.search(r"\b" + re.escape(t) + r"\b", p_norm))
    coverage = present / len(key)

    # Se nenhum termo aparece no nome, produto é irrelevante
    if coverage == 0:
        return 0.0

    # Boost proporcional à cobertura
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

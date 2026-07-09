"""
Testes do motor de matching do Catálogo Mestre (compute_product_key + MasterProductMatcher).
Não usam banco de dados — MasterProduct/MarketProduct são instanciados em memória.
"""
from app.models.product import MasterProduct
from app.services.product_matching_service import compute_product_key, MasterProductMatcher


def _matcher(*masters: MasterProduct) -> MasterProductMatcher:
    return MasterProductMatcher(list(masters))


def test_gtin_exact_match_wins_even_with_unrelated_name():
    master = MasterProduct(canonical_name="Coca-Cola Original 2L", brand="Coca-Cola", gtin="07894900011517")
    matcher = _matcher(master)

    result_master, status, confidence = matcher.match("Nome Completamente Diferente", "07894900011517")

    assert result_master is master
    assert status == "matched_gtin"
    assert confidence == 100.0


def test_brand_spelling_variants_share_the_same_bucket():
    # "Coca-Cola" e "Coca Cola" são duas entradas distintas na lista de marcas do
    # normalizer — sem normalizar a chave, essas grafias cairiam em buckets
    # diferentes e nunca seriam comparadas pelo fuzzy score.
    assert compute_product_key("Coca-Cola Original 2L") == compute_product_key("Coca Cola 2L Original")


def test_same_product_different_wording_auto_links_by_similarity():
    master = MasterProduct(canonical_name="Coca-Cola Original 2L", brand="Coca-Cola", gtin=None)
    matcher = _matcher(master)

    result_master, status, confidence = matcher.match("Coca Cola 2L Original", None)

    assert result_master is master
    assert status == "matched_similarity"
    assert confidence >= 90.0


def test_different_volume_is_never_auto_linked():
    master = MasterProduct(canonical_name="Coca-Cola Original 2L", brand="Coca-Cola", gtin=None)
    matcher = _matcher(master)

    result_master, status, _ = matcher.match("Coca-Cola Original 200ML", None)

    assert result_master is None
    assert status == "unmatched"


def test_no_candidates_in_bucket_is_unmatched():
    master = MasterProduct(canonical_name="Nescau 2.0 Achocolatado 400g", brand="Nescau", gtin=None)
    matcher = _matcher(master)

    result_master, status, _ = matcher.match("Sabao em Po Omo 1kg", None)

    assert result_master is None
    assert status == "unmatched"


def test_matcher_never_returns_a_master_for_unmatched_status():
    """Invariante importante: nenhum código deve tratar match_status=unmatched como
    tendo um master válido — o motor nunca deve devolver um objeto junto de 'unmatched'."""
    master = MasterProduct(canonical_name="Nescau 2.0 Achocolatado 400g", brand="Nescau", gtin=None)
    matcher = _matcher(master)

    result_master, status, confidence = matcher.match("Produto sem nenhuma relação", None)

    assert status == "unmatched"
    assert result_master is None
    assert confidence is None

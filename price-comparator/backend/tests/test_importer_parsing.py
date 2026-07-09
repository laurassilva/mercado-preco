"""
Testes do parsing de linhas da planilha mestre de GTIN (mapeamento de cabeçalho,
normalização de quantidade e do campo "ativo"). Não tocam banco de dados.
"""
from app.services.master_product_importer import (
    _apply_quantity,
    _map_row,
    _normalize_header,
    _parse_is_active,
)


def test_normalize_header_handles_accents_and_spacing():
    assert _normalize_header("Código de Barras") == "codigo_de_barras"
    assert _normalize_header("  Nome do Produto ") == "nome_do_produto"
    assert _normalize_header("GTIN") == "gtin"


def test_map_row_accepts_pt_and_en_header_variants():
    headers = ["EAN", "Nome", "Marca", "Categoria", "Peso", "Unidade"]
    values = ("7894900011517", "Coca-Cola 2L", "Coca-Cola", "Bebidas", "2", "L")

    raw = _map_row(headers, values)

    assert raw["gtin"] == "7894900011517"
    assert raw["canonical_name"] == "Coca-Cola 2L"
    assert raw["brand"] == "Coca-Cola"
    assert raw["category"] == "Bebidas"
    assert raw["_qty"] == "2"
    assert raw["_unit"] == "L"


def test_map_row_ignores_unknown_columns_and_blank_cells():
    headers = ["Coluna Desconhecida", "Nome"]
    values = ("valor irrelevante", "")

    raw = _map_row(headers, values)

    assert "canonical_name" not in raw  # célula vazia não deve virar valor
    assert len(raw) == 0


def test_apply_quantity_derives_normalized_volume_base():
    raw = {"_qty": "2", "_unit": "L"}
    _apply_quantity(raw)

    assert raw["quantity"] == "2L"
    assert raw["unit"] == "L"
    assert raw["volume_base"] == 2000  # normalizado para ml
    assert raw["volume_base_unit"] == "ml"


def test_apply_quantity_is_noop_without_qty():
    raw = {"brand": "Coca-Cola"}
    _apply_quantity(raw)
    assert raw == {"brand": "Coca-Cola"}


def test_parse_is_active_defaults_to_true_when_absent():
    assert _parse_is_active(None) is True


def test_parse_is_active_recognizes_falsy_strings():
    for value in ("0", "false", "nao", "não", "inativo", "n"):
        assert _parse_is_active(value) is False


def test_parse_is_active_recognizes_truthy_strings():
    assert _parse_is_active("sim") is True
    assert _parse_is_active("1") is True
    assert _parse_is_active(True) is True

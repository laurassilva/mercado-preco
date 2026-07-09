"""
Testes do validador de GTIN (dígito verificador GS1 mod-10) usado pelo importador
da planilha mestre. Os códigos válidos abaixo são exemplos oficiais/amplamente
usados de EAN-8, UPC-12, EAN-13 e GTIN-14 — não inventados.
"""
import pytest

from app.services.master_product_importer import validate_gtin


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("4006381333931", "04006381333931"),  # EAN-13 (exemplo clássico de teste)
        ("036000291452", "00036000291452"),  # UPC-12
        ("00012345678905", "00012345678905"),  # GTIN-14 (exemplo oficial GS1)
        ("96385074", "00000096385074"),  # EAN-8
        ("123456789012", "00123456789012"),  # UPC-12
    ],
)
def test_valid_gtin_normalizes_to_14_digits(raw, expected):
    assert validate_gtin(raw) == expected


def test_accepts_formatted_input_with_separators():
    # planilhas de usuário costumam trazer o código formatado com espaços/traços
    assert validate_gtin("4006-3813-33931") == "04006381333931"
    assert validate_gtin(" 4006381333931 ") == "04006381333931"


@pytest.mark.parametrize(
    "raw",
    [
        "4006381333930",  # dígito verificador errado (último dígito alterado)
        "12345",  # tamanho inválido (nem 8, 12, 13 nem 14 dígitos)
        "abcdefgh",  # sem dígitos
        "",
        None,
        "123456789",  # 9 dígitos — não é um tamanho GTIN válido
    ],
)
def test_invalid_gtin_returns_none(raw):
    assert validate_gtin(raw) is None

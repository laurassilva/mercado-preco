import asyncio
import random
from decimal import Decimal
from rapidfuzz import fuzz
from app.scrapers.base_scraper import BaseScraper, ProductResult

# Catalog of Brazilian market products with price ranges per market segment
# Prices are realistic (R$) as of 2024. Each market has a multiplier applied.
PRODUCT_CATALOG = [
    {
        "keywords": ["coca cola", "coca-cola", "coca", "refrigerante coca"],
        "name": "Coca-Cola Original",
        "brand": "Coca-Cola",
        "variants": [
            {"quantity": "2L", "base_price": Decimal("8.50"), "image": "https://via.placeholder.com/150?text=Coca-Cola+2L"},
            {"quantity": "1L", "base_price": Decimal("5.20"), "image": "https://via.placeholder.com/150?text=Coca-Cola+1L"},
            {"quantity": "350ml", "base_price": Decimal("2.90"), "image": "https://via.placeholder.com/150?text=Coca-Cola+350ml"},
        ],
    },
    {
        "keywords": ["pepsi", "pepsi cola", "refrigerante pepsi"],
        "name": "Pepsi Cola",
        "brand": "PepsiCo",
        "variants": [
            {"quantity": "2L", "base_price": Decimal("7.80"), "image": "https://via.placeholder.com/150?text=Pepsi+2L"},
            {"quantity": "350ml", "base_price": Decimal("2.50"), "image": "https://via.placeholder.com/150?text=Pepsi+350ml"},
        ],
    },
    {
        "keywords": ["arroz tio joao", "arroz tio joão", "arroz", "tio joao"],
        "name": "Arroz Agulhinha",
        "brand": "Tio João",
        "variants": [
            {"quantity": "5kg", "base_price": Decimal("24.90"), "image": "https://via.placeholder.com/150?text=Arroz+5kg"},
            {"quantity": "1kg", "base_price": Decimal("5.40"), "image": "https://via.placeholder.com/150?text=Arroz+1kg"},
        ],
    },
    {
        "keywords": ["feijao", "feijão", "feijao carioca", "feijão carioca"],
        "name": "Feijão Carioca",
        "brand": "Camil",
        "variants": [
            {"quantity": "1kg", "base_price": Decimal("7.50"), "image": "https://via.placeholder.com/150?text=Feijao+1kg"},
            {"quantity": "500g", "base_price": Decimal("4.20"), "image": "https://via.placeholder.com/150?text=Feijao+500g"},
        ],
    },
    {
        "keywords": ["leite integral", "leite", "leite parmalat", "leite longa vida"],
        "name": "Leite Integral UHT",
        "brand": "Parmalat",
        "variants": [
            {"quantity": "1L", "base_price": Decimal("4.50"), "image": "https://via.placeholder.com/150?text=Leite+1L"},
            {"quantity": "12x1L", "base_price": Decimal("49.90"), "image": "https://via.placeholder.com/150?text=Leite+Caixa"},
        ],
    },
    {
        "keywords": ["oleo soja", "óleo soja", "oleo de soja", "oleo liza", "liza"],
        "name": "Óleo de Soja Refinado",
        "brand": "Liza",
        "variants": [
            {"quantity": "900ml", "base_price": Decimal("6.90"), "image": "https://via.placeholder.com/150?text=Oleo+900ml"},
            {"quantity": "1.8L", "base_price": Decimal("12.90"), "image": "https://via.placeholder.com/150?text=Oleo+1.8L"},
        ],
    },
    {
        "keywords": ["acucar", "açúcar", "açucar", "acucar uniao", "acucar cristal", "uniao"],
        "name": "Açúcar Cristal",
        "brand": "União",
        "variants": [
            {"quantity": "1kg", "base_price": Decimal("4.20"), "image": "https://via.placeholder.com/150?text=Acucar+1kg"},
            {"quantity": "5kg", "base_price": Decimal("19.90"), "image": "https://via.placeholder.com/150?text=Acucar+5kg"},
        ],
    },
    {
        "keywords": ["macarrao", "macarrão", "espaguete", "macarrao renata", "renata"],
        "name": "Macarrão Espaguete",
        "brand": "Renata",
        "variants": [
            {"quantity": "500g", "base_price": Decimal("3.60"), "image": "https://via.placeholder.com/150?text=Macarrao+500g"},
        ],
    },
    {
        "keywords": ["cerveja brahma", "brahma", "cerveja", "brahma lata"],
        "name": "Cerveja Brahma Pilsen",
        "brand": "Ambev",
        "variants": [
            {"quantity": "350ml lata", "base_price": Decimal("3.10"), "image": "https://via.placeholder.com/150?text=Brahma+350ml"},
            {"quantity": "600ml long neck", "base_price": Decimal("5.50"), "image": "https://via.placeholder.com/150?text=Brahma+600ml"},
        ],
    },
    {
        "keywords": ["detergente", "detergente ype", "ypê", "ype"],
        "name": "Detergente Líquido Neutro",
        "brand": "Ypê",
        "variants": [
            {"quantity": "500ml", "base_price": Decimal("2.50"), "image": "https://via.placeholder.com/150?text=Detergente+500ml"},
        ],
    },
    {
        "keywords": ["papel higienico", "papel higiênico", "neve", "folha dupla"],
        "name": "Papel Higiênico Folha Dupla",
        "brand": "Neve",
        "variants": [
            {"quantity": "12 rolos", "base_price": Decimal("14.90"), "image": "https://via.placeholder.com/150?text=Papel+Higienico"},
            {"quantity": "4 rolos", "base_price": Decimal("5.80"), "image": "https://via.placeholder.com/150?text=Papel+Higienico"},
        ],
    },
    {
        "keywords": ["sabao po", "sabão em pó", "sabao em po", "omo", "ariel"],
        "name": "Sabão em Pó",
        "brand": "OMO",
        "variants": [
            {"quantity": "1kg", "base_price": Decimal("17.90"), "image": "https://via.placeholder.com/150?text=Sabao+1kg"},
            {"quantity": "3kg", "base_price": Decimal("46.90"), "image": "https://via.placeholder.com/150?text=Sabao+3kg"},
        ],
    },
    {
        "keywords": ["cafe", "café", "cafe pilao", "pilao", "pilão", "cafe torrado"],
        "name": "Café Torrado e Moído",
        "brand": "Pilão",
        "variants": [
            {"quantity": "500g", "base_price": Decimal("18.90"), "image": "https://via.placeholder.com/150?text=Cafe+500g"},
            {"quantity": "250g", "base_price": Decimal("10.50"), "image": "https://via.placeholder.com/150?text=Cafe+250g"},
        ],
    },
    {
        "keywords": ["biscoito oreo", "oreo", "biscoito recheado"],
        "name": "Biscoito Recheado Chocolate",
        "brand": "Oreo",
        "variants": [
            {"quantity": "144g", "base_price": Decimal("5.20"), "image": "https://via.placeholder.com/150?text=Oreo+144g"},
        ],
    },
    {
        "keywords": ["frango", "frango inteiro", "peito frango", "coxa frango"],
        "name": "Frango Inteiro Resfriado",
        "brand": "Sadia",
        "variants": [
            {"quantity": "kg", "base_price": Decimal("9.90"), "image": "https://via.placeholder.com/150?text=Frango"},
        ],
    },
]

# Price multipliers per market archetype (wholesale/atacado = cheaper, premium = more expensive)
MARKET_MULTIPLIERS = {
    "atacado": 0.82,
    "atacarejo": 0.86,
    "supermercado_economico": 0.92,
    "supermercado_padrao": 1.00,
    "supermercado_premium": 1.12,
    "hipermercado": 0.95,
}


class MockScraper(BaseScraper):
    """
    Demonstration scraper that returns realistic Brazilian market data.
    Replace with real scraper implementations for production use.
    """

    MARKET_TYPE_MAP = {
        "assaí": "atacado",
        "assai": "atacado",
        "makro": "atacarejo",
        "atacadão": "atacado",
        "atacadao": "atacado",
        "extra": "hipermercado",
        "carrefour": "hipermercado",
        "pão de açúcar": "supermercado_premium",
        "pao de acucar": "supermercado_premium",
        "santa helena": "supermercado_padrao",
        "dia": "supermercado_economico",
    }

    def _get_multiplier(self) -> float:
        market_lower = self.market_name.lower()
        for key, mtype in self.MARKET_TYPE_MAP.items():
            if key in market_lower:
                return MARKET_MULTIPLIERS[mtype]
        return MARKET_MULTIPLIERS["supermercado_padrao"]

    def _matches_query(self, product: dict, query: str) -> bool:
        query_lower = query.lower().strip()
        for keyword in product["keywords"]:
            if fuzz.partial_ratio(query_lower, keyword) >= 70:
                return True
        full_name = product["name"].lower()
        if fuzz.partial_ratio(query_lower, full_name) >= 65:
            return True
        if product.get("brand") and fuzz.partial_ratio(query_lower, product["brand"].lower()) >= 80:
            return True
        return False

    async def search(self, query: str) -> list[ProductResult]:
        await asyncio.sleep(random.uniform(0.1, 0.4))

        multiplier = self._get_multiplier()
        results: list[ProductResult] = []

        for product in PRODUCT_CATALOG:
            if not self._matches_query(product, query):
                continue

            for variant in product["variants"]:
                # Add slight random variation (±5%) to simulate real price fluctuation
                price_variation = Decimal(str(random.uniform(0.95, 1.05)))
                final_price = (variant["base_price"] * Decimal(str(multiplier)) * price_variation).quantize(
                    Decimal("0.01")
                )

                market_url = self.config.get("url", "https://example.com")
                slug = product["name"].lower().replace(" ", "-")

                results.append(
                    ProductResult(
                        market_name=self.market_name,
                        product_name=f"{product['name']} {variant['quantity']}",
                        brand=product["brand"],
                        quantity=variant["quantity"],
                        price=final_price,
                        image_url=variant["image"],
                        product_url=f"{market_url}/produto/{slug}",
                    )
                )

        return results

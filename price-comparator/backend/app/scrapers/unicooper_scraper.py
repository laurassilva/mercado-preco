"""
Scraper para Unicooper Supermercados (plataforma Mercafacil).
Site: https://www.unicoopersupermercados.com.br/loja
"""
import asyncio
import logging
import re
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper, ProductResult
from app.scrapers.search_utils import filter_products

logger = logging.getLogger(__name__)

BASE_URL = "https://www.unicoopersupermercados.com.br"

CRAWL_CATEGORIES = [
    "/loja/mercearia-basica",
    "/loja/bebidas",
    "/loja/laticinios-e-frios",
    "/loja/carnes-e-aves",
    "/loja/higiene-e-beleza",
    "/loja/limpeza",
    "/loja/hortifruti",
    "/loja/congelados-e-refrigerados",
    "/loja/padaria-e-confeitaria",
    "/loja/cereais-e-graos",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

PRICE_RE = re.compile(r"R\$\s*([\d]+[.,][\d]+)")
JUNK_RE = re.compile(r"^\+?\d+$|^Add$|^add$", re.IGNORECASE)


def _parse_price(text: str) -> Decimal | None:
    m = PRICE_RE.search(text)
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(",", "."))
    except Exception:
        return None


def _extract_name_and_price(a_tag) -> tuple[str, Decimal | None]:
    """
    Parseia o card Mercafacil extraindo nome e preço.

    Nome: prioritariamente do atributo alt da imagem (sempre limpo).
    Preço: primeiro R$ encontrado no texto do card.
    """
    # 1. Nome: alt da imagem é sempre o nome limpo
    img = a_tag.select_one("img[alt]")
    name = (img.get("alt") or "").strip() if img else ""

    # 2. Preço: primeiro R$ no texto
    full_text = a_tag.get_text()
    price: Decimal | None = None
    m = PRICE_RE.search(full_text)
    if m:
        try:
            price = Decimal(m.group(1).replace(",", "."))
        except Exception:
            pass

    return name, price


def _parse_page(html: str, market_name: str) -> list[ProductResult]:
    soup = BeautifulSoup(html, "lxml")
    products: list[ProductResult] = []
    seen: set[str] = set()

    for a in soup.select('a[href*="/loja/produto/m/"]'):
        try:
            href = a.get("href", "")
            product_url = f"{BASE_URL}{href}" if href.startswith("/") else href

            name, price = _extract_name_and_price(a)

            if not name or len(name) < 3 or name in seen:
                continue
            if not price or price <= 0:
                continue

            img = a.select_one("img[src]")
            image_url = img.get("src") if img else None

            seen.add(name)
            products.append(
                ProductResult(
                    market_name=market_name,
                    product_name=name,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                )
            )
        except Exception as exc:
            logger.debug("Unicooper parse error: %s", exc)

    return products


class UnicooperScraper(BaseScraper):

    async def _fetch(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.text
                logger.warning("Unicooper HTTP %s: %s", r.status_code, url)
        except Exception as exc:
            logger.error("Unicooper fetch error [%s]: %s", url, exc)
        return None

    async def search(self, query: str) -> list[ProductResult]:
        url = f"{BASE_URL}/loja/busca?q={query}"
        html = await self._fetch(url)
        if not html:
            return []
        products = _parse_page(html, self.market_name)
        return filter_products(query, products, min_score=55.0)

    async def crawl_all(self) -> list[ProductResult]:
        all_results: list[ProductResult] = []
        seen_names: set[str] = set()

        search_terms = [
            "arroz", "feijao", "acucar", "sal", "oleo", "leite", "cafe",
            "macarrao", "farinha", "sabao", "detergente", "cerveja", "refrigerante",
            "frango", "carne", "queijo", "iogurte", "manteiga", "pao",
            "suco", "agua", "vinho", "biscoito", "bolacha", "chocolate",
            "margarina", "presunto", "mortadela", "salsicha", "linguica",
            "shampoo", "condicionador", "desodorante", "papel", "amaciante",
            "molho", "extrato", "catchup", "maionese", "vinagre", "azeite",
            "cereal", "aveia", "granola", "cha", "achocolatado", "nescau",
            "salgadinho", "pipoca", "amendoim", "sardinha", "atum", "milho",
            "ervilha", "creme", "requeijao", "cream cheese", "tomate",
            "batata", "cebola", "alho", "banana", "maca", "laranja",
            "sorvete", "pizza", "lasanha", "hamburguer", "nuggets",
            "whisky", "vodka", "gin", "tonica", "energetico",
            "fralda", "absorvente", "escova", "creme dental",
            "racao", "pet", "limpador", "alvejante", "esponja",
        ]

        for term in search_terms:
            page = 1
            while True:
                url = f"{BASE_URL}/loja/busca?q={term}&page={page}"
                html = await self._fetch(url)
                if not html:
                    break
                products = _parse_page(html, self.market_name)
                if not products:
                    break
                new = [p for p in products if p.product_name not in seen_names]
                for p in new:
                    seen_names.add(p.product_name)
                all_results.extend(new)
                if len(products) < 20:
                    break
                page += 1
                await asyncio.sleep(0.4)
            await asyncio.sleep(0.3)

        logger.info("Unicooper total: %d produtos", len(all_results))
        return all_results

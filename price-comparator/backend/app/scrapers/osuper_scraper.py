"""
Scraper para lojas da plataforma osuper.com.br via API sense.osuper.com.br.
Suporta: Super Royal, Caita Supermercados e similares.

Config obrigatório no banco:
  instance_id: int  — ID da instância osuper (ex: 8 para Super Royal, 19 para Caita)
  store_id: int     — ID da loja (ex: 18 para Super Royal, 1102 para Caita)
  base_url: str     — URL do site (para links de produto)
"""
import asyncio
import logging
from decimal import Decimal

import httpx

from app.scrapers.base_scraper import BaseScraper, ProductResult
from app.scrapers.search_utils import filter_products

logger = logging.getLogger(__name__)

SENSE_BASE = "https://sense.osuper.com.br"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _parse_hits(hits: list, market_name: str, base_url: str) -> list[ProductResult]:
    results = []
    for item in hits:
        try:
            name = (item.get("name") or "").strip()
            if not name:
                continue

            pricing = item.get("pricing") or {}
            price_val = pricing.get("promotionalPrice") or pricing.get("price")
            if not price_val or float(price_val) <= 0:
                continue

            slug = item.get("slug", "")
            image_url = item.get("image") or None
            product_url = f"{base_url}/produto/{slug}" if slug else base_url
            brand = (item.get("brandName") or "").strip() or None

            results.append(
                ProductResult(
                    market_name=market_name,
                    product_name=name,
                    brand=brand,
                    price=Decimal(str(price_val)),
                    image_url=image_url,
                    product_url=product_url,
                )
            )
        except Exception as exc:
            logger.debug("OsuperScraper parse error: %s", exc)
    return results


class OsuperScraper(BaseScraper):
    """
    Scraper para lojas na plataforma osuper via API sense.osuper.com.br.
    Não usa Playwright — chamadas HTTP diretas à API REST.
    """

    @property
    def instance_id(self) -> str:
        return str(self.config.get("instance_id", ""))

    @property
    def store_id(self) -> str:
        return str(self.config.get("store_id", ""))

    @property
    def base_url(self) -> str:
        return self.config.get("base_url", "").rstrip("/")

    def _sense_url(self, path: str) -> str:
        return f"{SENSE_BASE}/{self.instance_id}/{self.store_id}/{path}"

    async def _get(self, url: str, params: dict | None = None) -> dict | None:
        try:
            async with httpx.AsyncClient(
                headers={**HEADERS, "Origin": self.base_url, "Referer": f"{self.base_url}/"},
                timeout=20,
                follow_redirects=True,
            ) as client:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    logger.warning("OsuperScraper HTTP %s: %s", r.status_code, url)
                    return None
                return r.json()
        except Exception as exc:
            logger.error("OsuperScraper fetch error [%s]: %s", url, exc)
            return None

    async def search(self, query: str) -> list[ProductResult]:
        if not self.instance_id or not self.store_id:
            logger.error(
                "OsuperScraper [%s]: instance_id e store_id são obrigatórios no config",
                self.market_name,
            )
            return []

        url = self._sense_url("search")
        data = await self._get(url, params={
            "search": query,
            "size": 50,
            "from": 0,
            "sortField": "_score",
            "sortOrder": "desc",
            "brands": "",
            "categories": "",
            "tags": "",
        })
        if not data:
            return []

        hits = data.get("hits", [])
        products = _parse_hits(hits, self.market_name, self.base_url)
        return filter_products(query, products, min_score=55.0)

    async def _crawl_category_page(
        self, client: httpx.AsyncClient, category: str, page: int = 0, size: int = 50
    ) -> list[dict]:
        url = self._sense_url(f"category/{category}")
        try:
            r = await client.get(url, params={
                "sortField": "sales_count",
                "sortOrder": "desc",
                "size": size,
                "from": page * size,
            })
            if r.status_code != 200:
                return []
            return r.json().get("hits", [])
        except Exception as exc:
            logger.debug("OsuperScraper crawl cat %s page %s: %s", category, page, exc)
            return []

    async def crawl_all(self) -> list[ProductResult]:
        if not self.instance_id or not self.store_id:
            return []

        all_results: list[ProductResult] = []
        seen_ids: set[str] = set()

        # Get category list from sense API
        cat_url = self._sense_url("categories")
        cat_data = await self._get(cat_url)
        categories: list[str] = []
        if cat_data and isinstance(cat_data, list):
            for c in cat_data:
                cid = c.get("id") or c.get("slug")
                if cid:
                    categories.append(str(cid))

        if not categories:
            # Fallback: try common category slugs via category search
            logger.info("OsuperScraper [%s]: buscando por termos genéricos", self.market_name)
            generic_terms = [
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
            for term in generic_terms:
                offset = 0
                while offset < 500:
                    url = self._sense_url("search")
                    data = await self._get(url, params={
                        "search": term, "size": 50, "from": offset,
                        "sortField": "sales_count", "sortOrder": "desc",
                    })
                    if not data:
                        break
                    hits = data.get("hits", [])
                    if not hits:
                        break
                    new = [h for h in hits if h.get("id") not in seen_ids]
                    for h in new:
                        seen_ids.add(h.get("id", ""))
                    all_results.extend(_parse_hits(new, self.market_name, self.base_url))
                    if len(hits) < 50:
                        break
                    offset += 50
                    await asyncio.sleep(0.3)
            logger.info("OsuperScraper [%s]: %d produtos", self.market_name, len(all_results))
            return all_results

        # Crawl by category
        async with httpx.AsyncClient(
            headers={**HEADERS, "Origin": self.base_url, "Referer": f"{self.base_url}/"},
            timeout=20,
        ) as client:
            for cat in categories:
                page = 0
                while True:
                    hits = await self._crawl_category_page(client, cat, page)
                    if not hits:
                        break
                    new = [h for h in hits if h.get("id") not in seen_ids]
                    for h in new:
                        seen_ids.add(h.get("id", ""))
                    all_results.extend(_parse_hits(new, self.market_name, self.base_url))
                    if len(hits) < 50:
                        break
                    page += 1
                    await asyncio.sleep(0.3)
                logger.info("OsuperScraper [%s] cat %s: %d total", self.market_name, cat, len(all_results))

        logger.info("OsuperScraper [%s]: total %d produtos", self.market_name, len(all_results))
        return all_results

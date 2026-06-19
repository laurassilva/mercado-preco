"""
Scraper genérico para lojas VTEX via API pública REST.
Suporta: Comper, DeliveryFort e qualquer VTEX com API aberta.

Uso: registrar o conector com config {"base_url": "https://www.loja.com.br"}
"""
import asyncio
import logging
import re
from decimal import Decimal

import httpx

from app.scrapers.base_scraper import BaseScraper, ProductResult
from app.scrapers.search_utils import filter_products

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class VtexScraper(BaseScraper):
    """
    Coleta produtos de lojas baseadas em VTEX via API pública.
    API: GET /api/catalog_system/pub/products/search/{query}?_from=0&_to=49
    """

    @property
    def base_url(self) -> str:
        return self.config.get("base_url", "").rstrip("/")

    def _parse_products(self, data: list) -> list[ProductResult]:
        results: list[ProductResult] = []
        for item in data:
            try:
                name = item.get("productName", "").strip()
                brand = item.get("brand", "").strip()
                link_text = item.get("linkText", "")
                product_url = f"{self.base_url}/{link_text}/p" if link_text else None

                vtex_items = item.get("items", [])
                if not vtex_items:
                    continue

                for vtex_item in vtex_items:
                    sellers = vtex_item.get("sellers", [])
                    if not sellers:
                        continue
                    offer = sellers[0].get("commertialOffer", {})
                    if not offer.get("IsAvailable", False):
                        continue
                    price_val = offer.get("Price", 0)
                    if not price_val or price_val <= 0:
                        continue

                    imgs = vtex_item.get("images", [])
                    image_url = imgs[0].get("imageUrl") if imgs else None

                    item_name = vtex_item.get("name", name).strip() or name

                    results.append(
                        ProductResult(
                            market_name=self.market_name,
                            product_name=item_name,
                            brand=brand or None,
                            price=Decimal(str(price_val)),
                            image_url=image_url,
                            product_url=product_url,
                        )
                    )
            except Exception as exc:
                logger.debug("VtexScraper item parse error: %s", exc)

        return results

    async def search(self, query: str) -> list[ProductResult]:
        if not self.base_url:
            logger.error("VtexScraper: base_url não configurada para %s", self.market_name)
            return []

        url = f"{self.base_url}/api/catalog_system/pub/products/search/{query}?_from=0&_to=49"
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
                r = await client.get(url)
                if r.status_code not in (200, 206):
                    logger.warning("VtexScraper HTTP %s para %s", r.status_code, self.market_name)
                    return []
                data = r.json()
                if not isinstance(data, list):
                    return []
                products = self._parse_products(data)
        except Exception as exc:
            logger.error("VtexScraper search error [%s]: %s", self.market_name, exc)
            return []

        return filter_products(query, products, min_score=55.0)

    async def crawl_all(self) -> list[ProductResult]:
        """Varre por categorias usando a árvore de categorias VTEX."""
        if not self.base_url:
            return []

        cat_url = f"{self.base_url}/api/catalog_system/pub/category/tree/2"
        all_results: list[ProductResult] = []
        seen_names: set[str] = set()

        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
                r = await client.get(cat_url)
                if r.status_code not in (200, 206):
                    logger.warning("VtexScraper category tree HTTP %s", r.status_code)
                    return []
                categories = r.json()
        except Exception as exc:
            logger.error("VtexScraper category tree error: %s", exc)
            return []

        # Coletar IDs de todas as sub-categorias
        cat_ids: list[int] = []
        for dept in categories:
            cat_ids.append(dept["id"])
            for sub in dept.get("children", []):
                cat_ids.append(sub["id"])

        logger.info("VtexScraper [%s]: varrendo %d categorias", self.market_name, len(cat_ids))

        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
            for cat_id in cat_ids:
                try:
                    r = await client.get(
                        f"{self.base_url}/api/catalog_system/pub/products/search/"
                        f"?fq=C:{cat_id}&_from=0&_to=49",
                        timeout=20,
                    )
                    if r.status_code not in (200, 206):
                        continue
                    data = r.json()
                    if not isinstance(data, list):
                        continue
                    products = self._parse_products(data)
                    new = [p for p in products if p.product_name not in seen_names]
                    for p in new:
                        seen_names.add(p.product_name)
                    all_results.extend(new)
                    await asyncio.sleep(0.3)
                except Exception as exc:
                    logger.debug("VtexScraper cat %s error: %s", cat_id, exc)

        logger.info("VtexScraper [%s]: total %d produtos", self.market_name, len(all_results))
        return all_results

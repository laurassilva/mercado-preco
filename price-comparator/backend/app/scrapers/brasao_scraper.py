"""
Scraper real para Brasão Supermercados - Loja Avenida
Site: https://www.brasao.com.br/avenida
Método: httpx + BeautifulSoup (HTML server-side renderizado)
"""
import asyncio
import re
import logging
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.brasao.com.br"
STORE_PREFIX = "/avenida"

CRAWL_CATEGORIES = [
    "/avenida/frutas-e-verduras-42",
    "/avenida/acougue-resfriado-34",
    "/avenida/acougue-congelado-29",
    "/avenida/bebidas-189",
    "/avenida/cereais-18",
    "/avenida/higiene-e-perfumaria-192",
    "/avenida/limpeza-1",
    "/avenida/matinais-59",
    "/avenida/mercearia-salgada-enlatado-e-conservas-3",
    "/avenida/mercearia-doce-bombonieres-213",
    "/avenida/mercearia-doce-50",
    "/avenida/pet-shop-211",
    "/avenida/pas-resfriados-lacteos-massas-fiambreria-20",
    "/avenida/pas-congelados-sobremesa-pratos-prontos-mas-2694",
    "/avenida/bazar-53",
    "/avenida/padaria-brasao-333",
    "/avenida/promocoes-99999",
]

PRICE_RE = re.compile(r"R\$\s*([\d]+[.,][\d]+)")
SKIP_LABELS = {
    "add", "atacado", "oferta", "desconto", "promoção", "promocao",
    "novo", "ver", "mais", "comprar", "quantidade", "un", "kg", "lt",
    "unidade", "leve", "pague", "combo", "kit", "destaque",
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class BrasaoScraper(BaseScraper):

    def _parse_page(self, html: str) -> list[ProductResult]:
        soup = BeautifulSoup(html, "lxml")
        product_links = soup.find_all("a", href=re.compile(r"/avenida/produto/m/"))

        results: list[ProductResult] = []
        for link in product_links:
            href = link.get("href", "")
            if not href:
                continue

            parts = [t.strip() for t in link.stripped_strings if t.strip()]
            all_text = " ".join(parts)

            prices = PRICE_RE.findall(all_text)
            if not prices:
                continue

            try:
                price = Decimal(prices[0].replace(",", "."))
                if price <= 0:
                    continue
            except Exception:
                continue

            # Nome: texto substancial que não é preço nem rótulo de UI
            name = ""
            for part in parts:
                stripped = part.strip()
                if len(stripped) < 5:
                    continue
                if re.match(r"^(R\$|\d)", stripped):
                    continue
                if not re.search(r"[A-Za-zÀ-ÿ]", stripped):
                    continue
                if stripped.lower() in SKIP_LABELS:
                    continue
                name = stripped
                break

            if not name:
                continue

            img_tag = link.find("img")
            image_url = img_tag.get("src") if img_tag else None
            product_url = f"{BASE_URL}{href}"

            results.append(
                ProductResult(
                    market_name=self.market_name,
                    product_name=name,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                )
            )

        return results

    async def _fetch_page(
        self, client: httpx.AsyncClient, url: str
    ) -> list[ProductResult]:
        try:
            resp = await client.get(url, timeout=25)
            if resp.status_code != 200:
                return []
            return self._parse_page(resp.text)
        except Exception as exc:
            logger.warning("Brasão fetch error [%s]: %s", url, exc)
            return []

    async def search(self, query: str) -> list[ProductResult]:
        """Pesquisa ao vivo no site do Brasão com filtragem estrita por relevância."""
        from app.scrapers.search_utils import filter_products

        search_url = f"{BASE_URL}{STORE_PREFIX}/busca?q={query.replace(' ', '+')}"
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
            products = await self._fetch_page(client, search_url)

        if not products:
            return []

        return filter_products(query, products, min_score=55.0)

    async def _crawl_category(self, client: httpx.AsyncClient, cat_path: str) -> list[ProductResult]:
        results: list[ProductResult] = []
        seen_urls: set[str] = set()
        page = 1
        empty_pages = 0
        while True:
            url = f"{BASE_URL}{cat_path}?page={page}"
            products = await self._fetch_page(client, url)
            if not products:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                page += 1
                continue
            empty_pages = 0
            new = [p for p in products if p.product_url not in seen_urls]
            if not new and page > 1:
                break
            for p in new:
                seen_urls.add(p.product_url)
            results.extend(new)
            page += 1
            await asyncio.sleep(0.05)
        return results

    async def crawl_all(self) -> list[ProductResult]:
        """Varre TODAS as categorias em paralelo (4 simultâneas)."""
        sem = asyncio.Semaphore(4)
        all_results: list[ProductResult] = []
        seen_urls: set[str] = set()

        async def _do(client, cat):
            async with sem:
                return await self._crawl_category(client, cat)

        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
            tasks = [_do(client, cat) for cat in CRAWL_CATEGORIES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    new = [p for p in r if p.product_url not in seen_urls]
                    for p in new:
                        seen_urls.add(p.product_url)
                    all_results.extend(new)

        logger.info("Brasão – varredura concluída: %d produtos", len(all_results))
        return all_results

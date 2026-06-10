"""
Scraper real para Super Alfa Supermercados
Site: https://superalfanumclick.com.br/
Método: Playwright (React SPA) + BeautifulSoup para parse do HTML renderizado
"""
import asyncio
import re
import unicodedata
import logging
from decimal import Decimal

from app.scrapers.playwright_scraper import PlaywrightScraper
from app.scrapers.base_scraper import ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://superalfanumclick.com.br"

CRAWL_CATEGORIES = [
    "/categorias/carnes",
    "/categorias/laticinios-e-frios",
    "/categorias/congelados",
    "/categorias/bebidas",
    "/categorias/mercearia",
    "/categorias/hortifruti",
    "/categorias/higiene-e-beleza",
    "/categorias/limpeza",
    "/categorias/infantil",
    "/categorias/padaria",
    "/categorias/saudaveis",
    "/categorias/pet-shop",
    "/categorias/bazar-e-utilidades",
    "/categorias/aurora-alimentos",
]

PRICE_RE = re.compile(r"R\$\s*([\d]+[.,][\d]+)")
SKIP_LABELS = {
    "oferta", "promoção", "promocao", "desconto", "atacado",
    "novo", "ver mais", "comprar", "add", "kg", "un", "lt",
    "ver", "mais", "leve", "pague", "patrocinado", "carregando",
}


def _slugify(text: str) -> str:
    """Converte nome de produto em slug para URL de busca."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    # Pega as primeiras 4 palavras para URL de busca legível
    words = [w for w in text.split("-") if w][:4]
    return "-".join(words)


class SuperAlfaScraper(PlaywrightScraper):

    def _parse_html(self, html: str, category_url: str = "") -> list[ProductResult]:
        """Parse do HTML renderizado pelo React para extrair produtos."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        products: list[ProductResult] = []
        seen: set[str] = set()

        # Cards são links com classe flex-col que contêm preço
        candidates = soup.find_all("a")
        for a in candidates:
            cls = " ".join(a.get("class", []))
            text = a.get_text(separator="\n").strip()

            if "R$" not in text:
                continue
            if "flex-col" not in cls and "cursor-pointer" not in cls:
                if len(text) < 15:
                    continue

            prices = PRICE_RE.findall(text)
            if not prices:
                continue

            # Nome: linha substancial que não é preço nem rótulo UI
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            name = ""
            for line in lines:
                if re.match(r"^(R\$|\d+[.,]|\d+%|[-+]?\d+[°º]?$)", line):
                    continue
                if len(line) < 5:
                    continue
                if not re.search(r"[A-Za-zÀ-ÿ]", line):
                    continue
                if line.lower() in SKIP_LABELS:
                    continue
                name = line
                break

            if not name or name in seen:
                continue
            seen.add(name)

            try:
                price = Decimal(prices[0].replace(",", "."))
                if price <= 0:
                    continue
            except Exception:
                continue

            img = a.find("img")
            image_url = img.get("src") if img else None

            # URL do produto: usa busca específica pelo nome (o site não expõe URLs individuais)
            slug = _slugify(name)
            product_url = f"{BASE_URL}/busca/{slug}" if slug else BASE_URL

            products.append(
                ProductResult(
                    market_name=self.market_name,
                    product_name=name,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                )
            )

        return products

    async def _extract_products(self, category_url: str = "") -> list[ProductResult]:
        try:
            html = await self._page.content()
        except Exception as exc:
            logger.warning("SuperAlfa content error: %s", exc)
            return []
        return self._parse_html(html, category_url)

    async def _scroll_to_load_all(self) -> None:
        """Rola até o fim e clica em 'Ver mais' para carregar todos os produtos."""
        prev_height = 0
        for _ in range(30):
            height = await self._page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                break
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.2)
            prev_height = height

            # Clica em botões de "carregar mais" se existirem
            try:
                for btn_text in ["Ver mais", "Carregar mais", "ver mais"]:
                    btns = await self._page.query_selector_all(
                        f"button:has-text('{btn_text}'), [class*='load-more'], [class*='ver-mais']"
                    )
                    for btn in btns:
                        if await btn.is_visible():
                            await btn.click()
                            await asyncio.sleep(1.5)
            except Exception:
                pass

    async def search(self, query: str) -> list[ProductResult]:
        """Pesquisa ao vivo no site do Super Alfa com filtragem estrita."""
        from app.scrapers.search_utils import filter_products

        await self._launch()
        try:
            term = re.sub(r"\s+", "-", query.strip().lower())
            url = f"{BASE_URL}/busca/{term}"
            await self._page.goto(url, timeout=35000, wait_until="load")
            await asyncio.sleep(3)
            await self._scroll_to_load_all()
            products = await self._extract_products(url)
        except Exception as exc:
            logger.error("SuperAlfa search error: %s", exc)
            return []
        finally:
            await self.close()

        return filter_products(query, products, min_score=55.0)

    async def _crawl_category(self, cat_path: str) -> list[ProductResult]:
        """Varre uma categoria completa com scroll para carregar tudo."""
        await self._launch()
        try:
            url = f"{BASE_URL}{cat_path}"
            await self._page.goto(url, timeout=35000, wait_until="load")
            await asyncio.sleep(3)
            await self._scroll_to_load_all()
            products = await self._extract_products(url)
            logger.info("SuperAlfa %s: %d produtos", cat_path, len(products))
            return products
        except Exception as exc:
            logger.error("SuperAlfa categoria [%s] falhou: %s", cat_path, exc)
            return []
        finally:
            await self.close()

    async def crawl_all(self) -> list[ProductResult]:
        """Varre todas as categorias sem precisar de termo de busca."""
        all_results: list[ProductResult] = []
        seen_names: set[str] = set()

        for cat_path in CRAWL_CATEGORIES:
            logger.info("SuperAlfa – varrendo: %s", cat_path)
            try:
                products = await self._crawl_category(cat_path)
                new = [p for p in products if p.product_name not in seen_names]
                for p in new:
                    seen_names.add(p.product_name)
                all_results.extend(new)
            except Exception as exc:
                logger.error("Falha em %s: %s", cat_path, exc)
            await asyncio.sleep(1)

        logger.info("SuperAlfa – total: %d produtos únicos", len(all_results))
        return all_results

"""
Playwright-based scraper skeleton.
Extend this class to implement real scraping for a specific market website.

Example usage:
    class CarrefourScraper(PlaywrightScraper):
        BASE_URL = "https://www.carrefour.com.br"

        async def search(self, query: str) -> list[ProductResult]:
            await self._launch()
            await self._page.goto(f"{self.BASE_URL}/busca?q={query}")
            await self._page.wait_for_selector(".product-card", timeout=15000)
            cards = await self._page.query_selector_all(".product-card")
            results = []
            for card in cards:
                name = await card.inner_text(".product-name")
                price_text = await card.inner_text(".product-price")
                ...
            await self.close()
            return results

    ConnectorManager.register("carrefour", CarrefourScraper)
"""
from __future__ import annotations
from app.scrapers.base_scraper import BaseScraper, ProductResult
from app.core.config import settings


class PlaywrightScraper(BaseScraper):
    """Base class for Playwright-driven scrapers."""

    def __init__(self, market_name: str, config: dict):
        super().__init__(market_name, config)
        self._browser = None
        self._page = None

    async def _launch(self) -> None:
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            self._page = await self._browser.new_page()
            await self._page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
            if hasattr(self, "_pw") and self._pw:
                await self._pw.stop()
                self._pw = None
        except Exception:
            pass

    async def search(self, query: str) -> list[ProductResult]:
        raise NotImplementedError("Implement search() in your subclass")

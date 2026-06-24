"""
Scraper para lojas da plataforma VIPCommerce via API REST.
Suporta: Passarela e similares.

Config obrigatório no banco:
  domain: str     — domínio do site (ex: passarelaemcasa.com.br)
  org_id: str     — ID da organização na VIPCommerce (ex: 344)
  filial_id: str  — ID da filial (ex: 1)
  cd_id: str      — ID do centro de distribuição (ex: 1)
"""
import asyncio
import logging
from decimal import Decimal

import httpx

from app.scrapers.base_scraper import BaseScraper, ProductResult
from app.scrapers.search_utils import filter_products

logger = logging.getLogger(__name__)

SERVICES_BASE = "https://services.vipcommerce.com.br"
IMAGE_BASE = "https://produto-assets-vipcommerce-com-br.br-se1.magaluobjects.com/250x250"


class VipcommerceScraper(BaseScraper):

    @property
    def domain(self) -> str:
        return self.config.get("domain", "")

    @property
    def org_id(self) -> str:
        return str(self.config.get("org_id", ""))

    @property
    def filial_id(self) -> str:
        return str(self.config.get("filial_id", "1"))

    @property
    def cd_id(self) -> str:
        return str(self.config.get("cd_id", "1"))

    @property
    def _api_base(self) -> str:
        return f"{SERVICES_BASE}/api-admin/v1/org/{self.org_id}"

    @property
    def _path_prefix(self) -> str:
        return f"/filial/{self.filial_id}/centro_distribuicao/{self.cd_id}/loja"

    @property
    def _login_key(self) -> str:
        return self.config.get("login_key", "")

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        r = await client.post(
            f"{self._api_base}/auth/loja/login",
            json={
                "domain": self.domain,
                "username": "loja",
                "key": self._login_key,
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "organizationid": self.org_id,
                "domainkey": self.domain,
            },
        )
        if r.status_code != 200:
            logger.warning("VipcommerceScraper login HTTP %s: %s", r.status_code, r.text[:100])
            return ""
        data = r.json()
        return data.get("data", "")

    def _auth_headers(self, token: str) -> dict:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "organizationid": self.org_id,
            "domainkey": self.domain,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    def _parse_products(self, items: list, base_url: str) -> list[ProductResult]:
        results = []
        for item in items:
            try:
                name = (item.get("descricao") or "").strip()
                if not name:
                    continue
                price_str = item.get("preco") or item.get("preco_oferta") or "0"
                price = Decimal(str(price_str))
                if price <= 0:
                    continue
                if not item.get("disponivel", True):
                    continue

                img = item.get("imagem", "")
                image_url = f"{IMAGE_BASE}/{img}" if img else None
                slug = item.get("link", "")
                product_url = f"https://{self.domain}/produto/{slug}" if slug else None

                results.append(ProductResult(
                    market_name=self.market_name,
                    product_name=name,
                    price=price,
                    image_url=image_url,
                    product_url=product_url,
                ))
            except Exception as exc:
                logger.debug("VipcommerceScraper parse error: %s", exc)
        return results

    async def search(self, query: str) -> list[ProductResult]:
        if not self.org_id or not self.domain:
            logger.error("VipcommerceScraper: org_id e domain obrigatórios")
            return []

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            token = await self._get_token(client)
            if not token:
                logger.error("VipcommerceScraper: falha na autenticação")
                return []

            h = self._auth_headers(token)
            term = query.replace(" ", "+")
            url = (
                f"{self._api_base}{self._path_prefix}"
                f"/buscas/produtos/termo/{term}?page=1"
            )
            r = await client.get(url, headers=h)
            if r.status_code != 200:
                logger.warning("VipcommerceScraper search HTTP %s", r.status_code)
                return []

            data = r.json()
            items = data.get("data", {}).get("produtos", [])
            products = self._parse_products(items, f"https://{self.domain}")

        return filter_products(query, products, min_score=55.0)

    async def _crawl_term(self, client: httpx.AsyncClient, h: dict, term: str, seen_ids: set) -> list[ProductResult]:
        results: list[ProductResult] = []
        page = 1
        while page <= 10:
            url = (
                f"{self._api_base}{self._path_prefix}"
                f"/buscas/produtos/termo/{term}?page={page}"
            )
            try:
                r = await client.get(url, headers=h)
                if r.status_code != 200:
                    break
                data = r.json()
                items = data.get("data", {}).get("produtos", [])
                if not items:
                    break
                new_items = [it for it in items if it.get("produto_id") not in seen_ids]
                for it in new_items:
                    seen_ids.add(it.get("produto_id"))
                results.extend(self._parse_products(new_items, f"https://{self.domain}"))
                if len(items) < 20:
                    break
                page += 1
                await asyncio.sleep(0.05)
            except Exception as exc:
                logger.debug("VipcommerceScraper search %s page %s: %s", term, page, exc)
                break
        return results

    async def crawl_all(self) -> list[ProductResult]:
        if not self.org_id or not self.domain:
            return []

        all_results: list[ProductResult] = []
        seen_ids: set[int] = set()

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

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            token = await self._get_token(client)
            if not token:
                logger.error("VipcommerceScraper: falha na autenticação para crawl")
                return []

            h = self._auth_headers(token)
            sem = asyncio.Semaphore(4)

            async def _do(t):
                async with sem:
                    return await self._crawl_term(client, h, t, seen_ids)

            results = await asyncio.gather(*[_do(t) for t in search_terms], return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_results.extend(r)

        logger.info("VipcommerceScraper [%s]: total %d produtos", self.market_name, len(all_results))
        return all_results

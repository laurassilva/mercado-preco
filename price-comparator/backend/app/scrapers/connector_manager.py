from typing import Type
from app.scrapers.base_scraper import BaseScraper


class ConnectorManager:
    """
    Registro de conectores de mercado.
    Para adicionar um novo mercado: ConnectorManager.register("chave", MinhaClasseScraper)
    """

    _registry: dict[str, Type[BaseScraper]] = {}

    @classmethod
    def register(cls, key: str, scraper_class: Type[BaseScraper]) -> None:
        cls._registry[key] = scraper_class

    @classmethod
    def get(cls, key: str, market_name: str, config: dict) -> BaseScraper:
        scraper_class = cls._registry.get(key)
        if scraper_class is None:
            raise ValueError(
                f"Conector '{key}' não registrado. "
                f"Disponíveis: {list(cls._registry.keys())}"
            )
        return scraper_class(market_name, config)

    @classmethod
    def available_connectors(cls) -> list[str]:
        return list(cls._registry.keys())


# Registro dos conectores reais
from app.scrapers.brasao_scraper import BrasaoScraper  # noqa
from app.scrapers.superalfa_scraper import SuperAlfaScraper  # noqa
from app.scrapers.mock_scraper import MockScraper  # noqa (mantido para testes)
from app.scrapers.vtex_scraper import VtexScraper  # noqa
from app.scrapers.unicooper_scraper import UnicooperScraper  # noqa
from app.scrapers.osuper_scraper import OsuperScraper  # noqa
from app.scrapers.vipcommerce_scraper import VipcommerceScraper  # noqa

ConnectorManager.register("brasao", BrasaoScraper)
ConnectorManager.register("superalfa", SuperAlfaScraper)
ConnectorManager.register("mock", MockScraper)
ConnectorManager.register("vtex", VtexScraper)       # genérico VTEX (Comper, DeliveryFort, etc.)
ConnectorManager.register("comper", VtexScraper)     # Comper Supermercados (VTEX)
ConnectorManager.register("deliveryfort", VtexScraper)  # DeliveryFort (VTEX)
ConnectorManager.register("unicooper", UnicooperScraper)  # Unicooper (Mercafacil)
ConnectorManager.register("osuper", OsuperScraper)   # genérico osuper (Super Royal, Caita)
ConnectorManager.register("superroyal", OsuperScraper)   # Super Royal
ConnectorManager.register("caita", OsuperScraper)    # Caita Supermercados
ConnectorManager.register("vipcommerce", VipcommerceScraper)  # genérico VIPCommerce
ConnectorManager.register("passarela", VipcommerceScraper)    # Passarela Supermercados

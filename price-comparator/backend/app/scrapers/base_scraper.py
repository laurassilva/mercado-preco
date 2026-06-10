from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone


@dataclass
class ProductResult:
    market_name: str
    product_name: str
    price: Decimal
    brand: str | None = None
    quantity: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseScraper(ABC):
    """
    Base class for all market scrapers/connectors.
    Subclass this and register with ConnectorManager to add a new market.
    """

    def __init__(self, market_name: str, config: dict):
        self.market_name = market_name
        self.config = config

    @abstractmethod
    async def search(self, query: str) -> list[ProductResult]:
        """Search for products matching query and return results."""
        ...

    async def get_product_details(self, url: str) -> ProductResult | None:
        """Optional: fetch detailed info for a single product page."""
        return None

    async def close(self) -> None:
        """Clean up resources (e.g., close browser)."""
        pass

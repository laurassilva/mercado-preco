from datetime import datetime
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    keywords: list[str]


class CategoryUpdate(BaseModel):
    name: str | None = None
    keywords: list[str] | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    keywords: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_keywords(cls, obj):
        import json
        return cls(
            id=str(obj.id),
            name=obj.name,
            keywords=json.loads(obj.keywords),
            is_active=obj.is_active,
            created_at=obj.created_at,
        )


class CategoryStats(BaseModel):
    category: str
    products_count: int
    alerts_today: int
    avg_price: float | None
    min_price: float | None
    max_price: float | None

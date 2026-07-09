"""
Importador da planilha mestre de GTIN.

Lê o arquivo em modo streaming (openpyxl read_only), valida e normaliza cada linha,
e faz upsert em lote (INSERT ... ON CONFLICT (gtin) DO UPDATE) diretamente via SQLAlchemy
Core — evita N+1 do ORM e permite importar milhares de registros com poucas roundtrips.
"""
import io
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import MasterProduct, MasterProductImportBatch
from app.normalizer.product_normalizer import extract_quantity, normalize_quantity_to_base

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
MAX_STORED_ERRORS = 500

_HEADER_MAP = {
    "gtin": "gtin", "ean": "gtin", "ean13": "gtin", "codigo_barras": "gtin", "codigo_de_barras": "gtin",
    "nome": "canonical_name", "nome_padrao": "canonical_name", "nome_do_produto": "canonical_name",
    "descricao_produto": "canonical_name", "descricao_do_produto": "canonical_name", "produto": "canonical_name",
    "marca": "brand",
    "fabricante": "manufacturer",
    "categoria": "category",
    "subcategoria": "subcategory",
    "descricao": "description",
    "peso": "_qty", "volume": "_qty", "quantidade": "_qty",
    "unidade": "_unit",
    "imagem": "image_url", "imagem_url": "image_url", "url_imagem": "image_url", "url_da_imagem": "image_url",
    "ativo": "is_active",
}

_UPDATE_COLUMNS = (
    "canonical_name", "brand", "manufacturer", "category", "subcategory",
    "description", "quantity", "unit", "volume_base", "volume_base_unit",
    "image_url", "is_active", "gtin_source", "updated_at",
)


def _normalize_header(h) -> str:
    h = str(h or "").strip().lower()
    h = unicodedata.normalize("NFD", h)
    h = "".join(c for c in h if unicodedata.category(c) != "Mn")
    h = re.sub(r"\s+", "_", h)
    return h


def validate_gtin(raw) -> str | None:
    """Normaliza para GTIN-14 (zero-padding) e valida o dígito verificador (algoritmo GS1 mod-10).
    Aceita GTIN-8/12/13/14. Retorna None se inválido ou ausente."""
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) not in (8, 12, 13, 14):
        return None
    payload, check = digits[:-1], int(digits[-1])
    total = 0
    for i, d in enumerate(reversed(payload)):
        total += int(d) * (3 if i % 2 == 0 else 1)
    expected = (10 - (total % 10)) % 10
    if expected != check:
        return None
    return digits.zfill(14)


def _map_row(headers: list, values: tuple) -> dict:
    raw = {}
    for h, v in zip(headers, values):
        key = _HEADER_MAP.get(_normalize_header(h))
        if key and v is not None and str(v).strip() != "":
            raw[key] = v
    return raw


def _apply_quantity(raw: dict) -> None:
    qty = raw.pop("_qty", None)
    unit = raw.pop("_unit", None)
    if qty is None:
        return
    text = f"{qty}{unit or ''}".strip()
    val, u = extract_quantity(text)
    if val and u:
        base_val, base_unit = normalize_quantity_to_base(val, u)
        raw["volume_base"] = base_val
        raw["volume_base_unit"] = base_unit
        raw["quantity"] = f"{val}{u}"
        raw["unit"] = u


def _parse_is_active(raw_value) -> bool:
    if raw_value is None:
        return True
    if isinstance(raw_value, bool):
        return raw_value
    text = str(raw_value).strip().lower()
    return text not in ("0", "false", "nao", "não", "inativo", "n")


async def import_master_products_from_xlsx(
    db: AsyncSession, batch: MasterProductImportBatch, file_bytes: bytes
) -> None:
    import openpyxl

    batch.status = "processing"
    batch.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = next(rows_iter, None)
    except Exception as exc:
        batch.status = "failed"
        batch.errors = [{"row": 0, "message": f"Falha ao ler planilha: {exc}"}]
        batch.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return

    if not headers:
        batch.status = "failed"
        batch.errors = [{"row": 0, "message": "Planilha vazia"}]
        batch.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return

    existing_result = await db.execute(select(MasterProduct.gtin).where(MasterProduct.gtin.isnot(None)))
    existing_gtins = {g for (g,) in existing_result.all()}

    now = datetime.now(timezone.utc)
    total = 0
    inserted = 0
    updated = 0
    error_count = 0
    errors: list[dict] = []
    chunk: list[dict] = []

    async def flush_chunk():
        if not chunk:
            return
        stmt = pg_insert(MasterProduct.__table__).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["gtin"],
            index_where=MasterProduct.__table__.c.gtin.isnot(None),
            set_={c: stmt.excluded[c] for c in _UPDATE_COLUMNS},
        )
        await db.execute(stmt)
        chunk.clear()

    for row_num, values in enumerate(rows_iter, start=2):
        if values is None or all(v is None for v in values):
            continue
        total += 1
        raw = _map_row(list(headers), values)

        gtin = validate_gtin(raw.get("gtin"))
        if not gtin:
            error_count += 1
            if len(errors) < MAX_STORED_ERRORS:
                errors.append({"row": row_num, "message": f"GTIN inválido ou ausente: {raw.get('gtin')!r}"})
            continue
        if not raw.get("canonical_name"):
            error_count += 1
            if len(errors) < MAX_STORED_ERRORS:
                errors.append({"row": row_num, "message": "Nome do produto ausente"})
            continue

        _apply_quantity(raw)

        row_data = {
            "id": uuid.uuid4(),
            "gtin": gtin,
            "canonical_name": str(raw["canonical_name"]).strip(),
            "brand": str(raw["brand"]).strip() if raw.get("brand") else None,
            "manufacturer": str(raw["manufacturer"]).strip() if raw.get("manufacturer") else None,
            "category": str(raw["category"]).strip() if raw.get("category") else None,
            "subcategory": str(raw["subcategory"]).strip() if raw.get("subcategory") else None,
            "description": str(raw["description"]).strip() if raw.get("description") else None,
            "quantity": raw.get("quantity"),
            "unit": raw.get("unit"),
            "volume_base": raw.get("volume_base"),
            "volume_base_unit": raw.get("volume_base_unit"),
            "image_url": str(raw["image_url"]).strip() if raw.get("image_url") else None,
            "is_active": _parse_is_active(raw.get("is_active")),
            "gtin_source": "import",
            "created_at": now,
            "updated_at": now,
        }

        if gtin in existing_gtins:
            updated += 1
        else:
            inserted += 1
            existing_gtins.add(gtin)

        chunk.append(row_data)
        if len(chunk) >= CHUNK_SIZE:
            await flush_chunk()
            await db.commit()

    await flush_chunk()

    batch.status = "completed"
    batch.total_rows = total
    batch.inserted_count = inserted
    batch.updated_count = updated
    batch.error_count = error_count
    batch.errors = errors
    batch.finished_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(
        "Importação de catálogo mestre concluída: %d linhas, %d inseridos, %d atualizados, %d erros",
        total, inserted, updated, error_count,
    )

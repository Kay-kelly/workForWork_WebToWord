"""
excel_to_shared.py

把 Excel row 轉成 SharedData。
第一版只做最小必要的欄位整理與驗證。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from uuid import NAMESPACE_URL, uuid5

from models.shared_data import SharedData


CONTROL_FIELDS = {
    "project_id",
    "test_id",
    "batch_sequence_id",
    "template_id",
    "row_number",
}


def normalize_excel_row(
    raw_row: dict,
    *,
    project_id: str,
    test_id: str,
) -> SharedData:
    """
    將 Excel 原始列資料轉成 SharedData。

    第一版先固定一個 project 與一個 test type，
    其他業務欄位則整理後放進 payload。
    """
    row_number = raw_row.get("row_number")
    if not isinstance(row_number, int):
        raise ValueError("Excel row 缺少有效的 row_number，無法建立 SharedData。")

    normalized_payload: dict[str, object] = {}

    for raw_key, raw_value in raw_row.items():
        normalized_key = normalize_field_name(raw_key)
        if not normalized_key or normalized_key in CONTROL_FIELDS:
            continue

        normalized_payload[normalized_key] = normalize_field_value(raw_value)

    batch_sequence_id = _resolve_batch_sequence_id(raw_row, row_number)
    record_id = build_record_id(
        project_id=project_id,
        test_id=test_id,
        batch_sequence_id=batch_sequence_id,
    )

    return SharedData(
        record_id=record_id,
        project_id=project_id,
        test_id=test_id,
        batch_sequence_id=batch_sequence_id,
        payload=normalized_payload,
        source_info={
            "source_type": "excel",
            "row_number": row_number,
        },
    )


def normalize_field_name(raw_key: object) -> str:
    """把欄位名稱整理成穩定的 payload key。"""
    if raw_key is None:
        return ""

    key_text = str(raw_key).strip().lower()
    if not key_text:
        return ""

    normalized = re.sub(r"\W+", "_", key_text, flags=re.UNICODE).strip("_")
    return normalized


def normalize_field_value(raw_value: object) -> object:
    """把 Excel value 轉成較穩定的內部值。"""
    if raw_value is None:
        return None

    if isinstance(raw_value, datetime):
        return raw_value.isoformat(sep=" ", timespec="seconds")

    if isinstance(raw_value, date):
        return raw_value.isoformat()

    if isinstance(raw_value, str):
        return raw_value.strip()

    if isinstance(raw_value, (int, float, bool)):
        return raw_value

    return str(raw_value).strip()


def build_record_id(*, project_id: str, test_id: str, batch_sequence_id: str) -> str:
    """使用穩定規則產生 record_id。"""
    seed = f"{project_id}:{test_id}:{batch_sequence_id}"
    return str(uuid5(NAMESPACE_URL, seed))


def _resolve_batch_sequence_id(raw_row: dict, row_number: int) -> str:
    """優先使用整理後的 batch_sequence_id，否則退回列號。"""
    raw_value = raw_row.get("batch_sequence_id")
    normalized_value = normalize_field_value(raw_value)

    if normalized_value is None or str(normalized_value).strip() == "":
        return f"excel-row-{row_number}"

    return str(normalized_value).strip()

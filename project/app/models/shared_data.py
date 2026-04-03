"""
shared_data.py

第一版 SharedData 薄模型。
這一層只保留系統內部需要的最小結構，
避免後續圖片或 Word 輸出直接吃 raw input。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SharedData:
    """系統內部共用的標準資料層。"""

    record_id: str
    project_id: str
    test_id: str
    batch_sequence_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    source_info: dict[str, Any] = field(default_factory=dict)

    def get_value(self, field_name: str, default: Any = None) -> Any:
        """從整理後的 payload 取值。"""
        return self.payload.get(field_name, default)

    @property
    def row_number(self) -> int | None:
        """保留來源列號，方便除錯與追蹤。"""
        row_number = self.source_info.get("row_number")
        return row_number if isinstance(row_number, int) else None

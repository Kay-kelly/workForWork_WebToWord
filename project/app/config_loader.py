"""
config_loader.py

負責：
- 載入 config/mapping.json
- 驗證 schema 結構
- 將 templates 陣列轉換為 template_id -> template config 的 lookup dict
- 提供主程式查詢 template 設定的介面

業務語意：
- template_image = 模板底圖
- source = 對應 Excel 欄位名稱
- x, y = 文字在圖片上的定位座標
"""

import json
from pathlib import Path


class ConfigLoader:
    """
    載入並管理 mapping.json 設定內容。

    職責：
    1. 從指定路徑讀取 JSON 設定
    2. 驗證根結構、template 結構與 field 結構
    3. 補齊 global 區塊中的預設值
    4. 將 templates 陣列轉為方便查找的 dict
    """

    def __init__(self, config_path):
        """
        初始化設定載入器。

        參數：
        config_path (Path | str)
            mapping.json 的路徑
        """
        self.config_path = Path(config_path)
        self.raw_config = self._load_json()
        # 提前完成驗證，讓後續程式可以假設設定結構是穩定且可用的。
        self._validate_root(self.raw_config)
        self.global_config = self.raw_config["global"]
        self.templates = self._build_template_lookup(self.raw_config["templates"])

    def _load_json(self):
        """
        讀取 mapping.json 並轉為 Python dict。

        回傳：
        dict
            解析後的 JSON 設定內容
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"找不到 mapping 設定檔：{self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"mapping.json 的 JSON 格式不合法：{self.config_path}"
                ) from exc

    def _validate_root(self, config_data):
        """
        驗證最外層設定結構，並補齊 global 預設值。

        參數：
        config_data (dict)
            最外層設定內容
        """
        required_root_keys = ["global", "templates"]
        for key in required_root_keys:
            if key not in config_data:
                raise ValueError(f"mapping.json 缺少必要欄位：'{key}'")

        if not isinstance(config_data["global"], dict):
            raise ValueError("'global' 欄位必須是物件。")

        if not isinstance(config_data["templates"], list):
            raise ValueError("'templates' 欄位必須是陣列。")

        global_config = config_data["global"]
        global_config.setdefault("default_font_size", 24)
        global_config.setdefault("default_color", "#000000")
        global_config.setdefault("default_align", "left")

    def _build_template_lookup(self, templates):
        """
        將 templates 陣列轉為以 template_id 為 key 的查找表。

        參數：
        templates (list)
            mapping.json 中的 templates 陣列

        回傳：
        dict
            以 template_id 為 key 的 template 設定 dict
        """
        template_lookup = {}

        for index, template in enumerate(templates, start=1):
            self._validate_template(template, index)
            # 將 template 陣列轉為 dict，之後主程式可用 template_id 快速查找。
            template_id = template["template_id"]

            if template_id in template_lookup:
                raise ValueError(f"發現重複的 template_id：'{template_id}'")

            template_lookup[template_id] = template

        return template_lookup

    def _validate_template(self, template, index):
        """
        驗證單一 template 的必要欄位與型別。

        參數：
        template (dict)
            單一模板設定
        index (int)
            模板在 templates 陣列中的位置，方便錯誤訊息定位
        """
        if not isinstance(template, dict):
            raise ValueError(f"第 {index} 個 template 必須是物件。")

        required_template_keys = ["template_id", "template_image", "fields"]
        for key in required_template_keys:
            if key not in template:
                raise ValueError(
                    f"第 {index} 個 template 缺少必要欄位：'{key}'"
                )

        if not isinstance(template["template_id"], str) or not template["template_id"].strip():
            raise ValueError(
                f"第 {index} 個 template 的 'template_id' 不合法，必須是非空白字串。"
            )

        if not isinstance(template["template_image"], str) or not template["template_image"].strip():
            raise ValueError(
                f"Template '{template['template_id']}' 的 'template_image' 不合法，必須是非空白字串。"
            )

        if not isinstance(template["fields"], list):
            raise ValueError(
                f"Template '{template['template_id']}' 的 'fields' 不合法，必須是陣列。"
            )

        for field_index, field in enumerate(template["fields"], start=1):
            self._validate_field(template["template_id"], field, field_index)

    def _validate_field(self, template_id, field, field_index):
        """
        驗證單一 field 設定的必要欄位與基本型別。

        業務語意：
        - source = 對應 Excel 欄位名稱
        - x, y = 文字在圖片上的定位座標

        參數：
        template_id (str)
            所屬模板 ID
        field (dict)
            單一欄位設定
        field_index (int)
            欄位在 fields 陣列中的位置，方便錯誤訊息定位
        """
        if not isinstance(field, dict):
            raise ValueError(
                f"Template '{template_id}' 的第 {field_index} 個 field 必須是物件。"
            )

        required_field_keys = ["source", "x", "y"]
        for key in required_field_keys:
            if key not in field:
                raise ValueError(
                    "Template '{template_id}' 的第 {field_index} 個 field 缺少必要欄位：'{key}'".format(
                        template_id=template_id,
                        field_index=field_index,
                        key=key,
                    )
                )

        if not isinstance(field["source"], str) or not field["source"].strip():
            raise ValueError(
                f"Template '{template_id}' 的第 {field_index} 個 field，'source' 不合法，必須是非空白字串。"
            )

        if not isinstance(field["x"], (int, float)):
            raise ValueError(
                f"Template '{template_id}' 的第 {field_index} 個 field，'x' 不合法，必須是數字。"
            )

        if not isinstance(field["y"], (int, float)):
            raise ValueError(
                f"Template '{template_id}' 的第 {field_index} 個 field，'y' 不合法，必須是數字。"
            )

    def get_template(self, template_id):
        """
        根據 template_id 取得對應模板設定。

        參數：
        template_id (str)
            Excel 中指定的模板 ID

        回傳：
        dict
            對應的 template 設定
        """
        if template_id not in self.templates:
            raise KeyError(f"找不到對應的 template_id：'{template_id}'")

        return self.templates[template_id]

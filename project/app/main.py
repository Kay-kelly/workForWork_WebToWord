"""
main.py

負責：
- 取得專案基底路徑
- 載入 mapping.json 設定
- 讀取 Excel 資料
- 依每列的 template_id 選擇模板
- 呼叫 renderer 產生圖片並輸出到 output/

業務語意：
- output_name = 最終輸出檔名
- template_image = 模板底圖
"""

import sys
from pathlib import Path

from config_loader import ConfigLoader
from excel_reader import read_excel_rows
from renderer import render_image


def get_base_dir():
    """
    取得程式執行時使用的基底目錄。

    為什麼要同時支援開發模式與 exe 模式：
    - 開發模式下，程式通常以 `python app/main.py` 執行，設定檔與資料檔位於 project 根目錄
    - 未來若打包成 exe，程式入口位置會改變，因此需改以 exe 所在目錄作為基底

    回傳：
    Path
        專案根目錄或 exe 所在目錄
    """
    if getattr(sys, "frozen", False):
        # exe 模式：以執行檔所在目錄作為 config / data / output 的基準位置。
        return Path(sys.executable).resolve().parent

    # 開發模式：main.py 位於 app/ 底下，因此 project 根目錄是上一層。
    return Path(__file__).resolve().parent.parent


def build_output_filename(row_data, template_id):
    """
    根據 Excel 列資料產生輸出檔名。

    規則：
    1. 若 Excel 有提供 output_name，優先使用
    2. 若沒有，使用 template_id + row_number
    3. 若檔名未包含 .png，則自動補上副檔名

    業務語意：
    - output_name = 最終輸出檔名

    參數：
    row_data (dict)
        單列 Excel 資料
    template_id (str)
        該列對應的模板 ID

    回傳：
    str
        最終輸出檔名
    """
    output_name = row_data.get("output_name")
    if output_name is not None and str(output_name).strip() != "":
        file_name = str(output_name).strip()
    else:
        file_name = f"{template_id}_{row_data['row_number']}"

    if not file_name.lower().endswith(".png"):
        file_name = f"{file_name}.png"

    return file_name


def main():
    """
    MVP 主流程入口。

    資料流程：
    1. 先決定基底路徑
    2. 由基底路徑推導 config / data / output 實際位置
    3. 載入 mapping.json
    4. 讀取 Excel 每一列資料
    5. 依 template_id 找對應模板
    6. 呼叫 renderer 產生 PNG
    7. 將結果輸出到 output/
    """
    base_dir = get_base_dir()

    # 所有核心路徑都由同一個 base_dir 推導，確保開發模式與 exe 模式一致。
    config_path = base_dir / "config" / "mapping.json"
    excel_path = base_dir / "data" / "input.xlsx"
    output_dir = base_dir / "output"

    # 若 output/ 不存在則自動建立，避免首次執行時因資料夾缺失而失敗。
    output_dir.mkdir(parents=True, exist_ok=True)

    config = ConfigLoader(config_path)
    rows = read_excel_rows(excel_path)
    debug_grid = config.global_config.get("debug_grid", False)

    if "--debug" in sys.argv:
        debug_grid = True

    for row_data in rows:
        # 每列都必須有 template_id，才能決定要套用哪一張模板圖片。
        template_id = row_data.get("template_id")
        if template_id is None or str(template_id).strip() == "":
            raise ValueError(
                f"Excel 第 {row_data['row_number']} 列缺少 template_id。"
            )

        template_id = str(template_id).strip()
        template_config = config.get_template(template_id)
        output_filename = build_output_filename(row_data, template_id)
        output_path = output_dir / output_filename

        try:
            # 將單列資料與對應模板交給 renderer，產出最終 PNG。
            render_image(
                template_config=template_config,
                row_data=row_data,
                global_config=config.global_config,
                base_dir=base_dir,
                output_path=output_path,
                debug_grid=debug_grid,
            )
            print(f"已產生圖片：{output_path}")
        except Exception as exc:
            raise RuntimeError(
                f"處理 Excel 第 {row_data['row_number']} 列、template_id '{template_id}' 時失敗。"
            ) from exc


if __name__ == "__main__":
    """
    命令列執行入口。

    目的：
    - 直接執行 main()
    - 若發生錯誤，輸出簡潔錯誤訊息並以非 0 狀態碼結束
    """
    try:
        main()
    except Exception as exc:
        print(f"錯誤：{exc}")
        sys.exit(1)
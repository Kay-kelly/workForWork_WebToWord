"""
pipeline_main.py

新的 MVP pipeline 入口。
先保留舊 main.py，可獨立執行最小流程：
shared data -> generate_image -> overlay_text
"""

import sys
from pathlib import Path

from config_loader import ConfigLoader
from excel_reader import read_excel_rows
from normalizers.excel_to_shared import normalize_excel_row
from pipelines.runner import run_pipeline


DEFAULT_PROJECT_ID = "mvp_project"
DEFAULT_TEST_ID = "mvp_image_report"
DEFAULT_IMAGE_TEMPLATE_ID = "A"

MVP_PIPELINE_STEPS = [
    {"step": "generate_image", "artifact_key": "base_image"},
    {"step": "overlay_text", "input_artifact_key": "base_image"},
]


def get_base_dir() -> Path:
    """比照舊入口，取得 project 根目錄。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def main() -> None:
    """執行第一版最小 pipeline。"""
    base_dir = get_base_dir()
    config_path = base_dir / "config" / "mapping.json"
    excel_path = base_dir / "data" / "input.xlsx"
    output_dir = base_dir / "output" / "pipeline_mvp"

    config = ConfigLoader(config_path)
    template_config = config.get_template(DEFAULT_IMAGE_TEMPLATE_ID)
    raw_rows = read_excel_rows(excel_path)

    debug_grid = config.global_config.get("debug_grid", False)
    if "--debug" in sys.argv:
        debug_grid = True

    if not raw_rows:
        print("沒有可處理的 Excel 資料。")
        return

    for raw_row in raw_rows:
        shared_data = normalize_excel_row(
            raw_row,
            project_id=DEFAULT_PROJECT_ID,
            test_id=DEFAULT_TEST_ID,
        )

        final_output_path = run_pipeline(
            shared_data,
            pipeline_steps=MVP_PIPELINE_STEPS,
            template_config=template_config,
            global_config=config.global_config,
            base_dir=base_dir,
            output_dir=output_dir,
            debug_grid=debug_grid,
        )
        print(f"完成 MVP pipeline: {final_output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Pipeline 執行失敗: {exc}")
        sys.exit(1)

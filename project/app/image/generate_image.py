"""
generate_image.py

第一版 generate_image 只做一件事：
載入 base image template，輸出一張基礎圖。
"""

from pathlib import Path

from PIL import Image

from models.shared_data import SharedData
from renderer import resolve_path


def generate_image(
    shared_data: SharedData,
    *,
    template_config: dict,
    base_dir: Path,
    output_path: Path,
) -> Path:
    """
    根據 pipeline 指定的 base image template 產出基礎圖。

    第一版先固定只支援：
    載入 template_image -> 另存成 pipeline 的中間圖片。
    """
    if not template_config.get("template_image"):
        raise ValueError("generate_image 缺少 template_image 設定。")

    template_path = resolve_path(base_dir, template_config["template_image"])
    if not template_path.exists():
        raise FileNotFoundError(f"找不到 base image template: {template_path}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(template_path) as template_image:
        base_image = template_image.convert("RGBA")
        # 第一版先固定用 record_id 命名輸出的基礎圖，
        # shared_data 在這裡負責提供穩定的資料單位識別。
        base_image.save(output_path, format="PNG")
        base_image.close()

    return output_path

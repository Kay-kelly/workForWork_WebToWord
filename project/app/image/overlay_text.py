"""
overlay_text.py

把整理過的 SharedData 套用到已生成的基礎圖。
這一層只負責文字覆蓋，不再負責建立圖片本體。
"""

from pathlib import Path

from PIL import Image, ImageDraw

from models.shared_data import SharedData
from renderer import (
    calculate_text_position,
    draw_debug_grid,
    load_font,
    parse_color,
)


def overlay_text(
    shared_data: SharedData,
    *,
    template_config: dict,
    global_config: dict,
    base_dir: Path,
    input_image_path: Path,
    output_path: Path,
    debug_grid: bool = False,
) -> Path:
    """將文字依 mapping 覆蓋到 generate_image 的輸出圖上。"""
    input_image_path = Path(input_image_path)
    if not input_image_path.exists():
        raise FileNotFoundError(f"找不到 generate_image 產出的基礎圖: {input_image_path}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_image_path) as source_image:
        image = source_image.convert("RGBA")
        draw = ImageDraw.Draw(image)

        if debug_grid:
            draw_debug_grid(image, draw)

        for field in template_config.get("fields", []):
            source_name = str(field["source"]).strip()
            if source_name not in shared_data.payload:
                raise ValueError(
                    "SharedData 缺少 overlay_text 所需欄位: "
                    f"record_id='{shared_data.record_id}', source='{source_name}'"
                )

            value = shared_data.get_value(source_name)
            if value is None:
                value = ""

            text_template = field.get("format", "{value}")
            text = text_template.replace("{value}", str(value))

            font = load_font(field, global_config, base_dir)
            color = parse_color(
                field.get("color", global_config.get("default_color", "#000000"))
            )
            align = field.get("align", global_config.get("default_align", "left"))
            x = field["x"]
            y = field["y"]

            position = calculate_text_position(draw, text, font, x, y, align)
            draw.text(position, text, fill=color, font=font)

        image.save(output_path, format="PNG")
        image.close()

    return output_path

"""
renderer.py

負責：
- 開啟模板圖片
- 根據 mapping.json 的 fields 設定將 Excel 資料寫到圖片上
- 支援字型、顏色、格式化字串與水平對齊
- 將結果輸出為 PNG

業務語意：
- template_image = 模板底圖
- source = 對應 Excel 欄位名稱
- x, y = 文字在圖片上的定位座標
- format = 將 Excel 值套入輸出字串模板
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def render_image(template_config, row_data, global_config, base_dir, output_path, debug_grid=False):
    """
    根據模板設定與單列 Excel 資料產生一張輸出圖片。

    流程：
    1. 解析 template_image 路徑並開啟圖片
    2. 逐一處理 fields 設定
    3. 從 row_data 取出 source 對應欄位值
    4. 使用 format 中的 {value} 產生最終文字
    5. 套用字型、顏色、對齊後繪製到圖片
    6. 儲存為 PNG

    參數：
    template_config (dict)
        單一模板設定
    row_data (dict)
        單列 Excel 資料
    global_config (dict)
        全域預設設定
    base_dir (Path | str)
        專案根目錄或 exe 基底目錄
    output_path (Path | str)
        輸出 PNG 路徑
    """
    template_path = resolve_path(base_dir, template_config["template_image"])
    if not template_path.exists():
        raise FileNotFoundError(f"找不到模板底圖：{template_path}")

    image = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # 除錯模式下先畫座標格線，方便校正 mapping.json 的 x / y。
    if debug_grid:
        draw_debug_grid(image, draw)

    for field in template_config["fields"]:
        field_name = field.get("name", "<unnamed>")
        source = field["source"]

        # 若 mapping.json 指定的 source 在 Excel 中不存在，直接提供可定位的錯誤訊息。
        if source not in row_data:
            raise ValueError(
                "Excel 資料缺少對應欄位：template_id='{template_id}', "
                "field='{field_name}', source='{source}', row_number={row_number}".format(
                    template_id=template_config["template_id"],
                    field_name=field_name,
                    source=source,
                    row_number=row_data.get("row_number", "unknown"),
                )
            )

        value = row_data.get(source)
        if value is None:
            value = ""

        # MVP 僅支援最基本的字串格式化，使用 {value} 佔位符插入 Excel 值。
        text_template = field.get("format", "{value}")
        text = text_template.replace("{value}", str(value))

        # 若 field 未指定字型、大小或顏色，則回退使用 global 預設值。
        font = load_font(field, global_config, base_dir)
        color = parse_color(field.get("color", global_config.get("default_color", "#000000")))
        align = field.get("align", global_config.get("default_align", "left"))

        # x, y 被視為文字的水平定位 anchor point。
        x = field["x"]
        y = field["y"]
        position = calculate_text_position(draw, text, font, x, y, align)

        draw.text(position, text, fill=color, font=font)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    image.close()


def draw_debug_grid(image, draw):
    """
    在圖片上繪製除錯格線與座標標示，方便校正欄位位置。
    """
    width, height = image.size
    step = 50
    line_color = (255, 0, 0, 80)
    text_color = (255, 0, 0, 255)
    label_font = ImageFont.load_default()

    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=line_color, width=1)
        draw.text((x + 2, 2), str(x), fill=text_color, font=label_font)

    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=line_color, width=1)
        draw.text((2, y + 2), str(y), fill=text_color, font=label_font)


def resolve_path(base_dir, relative_path):
    """
    將相對路徑轉為基於 base_dir 的實際路徑。

    參數：
    base_dir (Path | str)
        專案根目錄或 exe 所在目錄
    relative_path (Path | str)
        相對或絕對路徑

    回傳：
    Path
        可直接使用的完整路徑
    """
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return Path(base_dir) / path


def load_font(field, global_config, base_dir):
    """
    載入欄位所需字型。

    規則：
    1. 優先使用 field.font_path
    2. 若未指定，改用 global.default_font_path
    3. 若仍未指定，退回 Pillow 內建預設字型

    參數：
    field (dict)
        欄位設定
    global_config (dict)
        全域預設設定
    base_dir (Path | str)
        專案根目錄或 exe 基底目錄

    回傳：
    ImageFont.FreeTypeFont | ImageFont.ImageFont
        Pillow 字型物件
    """
    font_size = field.get("font_size", global_config.get("default_font_size", 24))
    font_path = field.get("font_path") or global_config.get("default_font_path")

    if not font_path:
        return ImageFont.load_default()

    resolved_font_path = resolve_path(base_dir, font_path)
    if not resolved_font_path.exists():
        raise FileNotFoundError(f"找不到字型檔：{resolved_font_path}")

    return ImageFont.truetype(str(resolved_font_path), size=font_size)


def parse_color(color_value):
    """
    將 mapping.json 中的顏色格式轉為 Pillow 可使用的 RGB tuple。

    支援格式：
    - HEX 字串，例如 "#FFFFFF" 或 "#FFF"
    - RGB 陣列，例如 [255, 255, 255]

    參數：
    color_value (str | list | tuple)
        顏色設定值

    回傳：
    tuple[int, int, int]
        Pillow 可使用的 RGB 顏色
    """
    if isinstance(color_value, str):
        color_text = color_value.strip()
        if not color_text.startswith("#"):
            raise ValueError(f"不支援的顏色字串格式：{color_value}")

        hex_value = color_text[1:]
        if len(hex_value) == 3:
            hex_value = "".join(channel * 2 for channel in hex_value)

        if len(hex_value) != 6:
            raise ValueError(f"HEX 顏色必須為 3 碼或 6 碼：{color_value}")

        return tuple(int(hex_value[index:index + 2], 16) for index in (0, 2, 4))

    if isinstance(color_value, list) and len(color_value) == 3:
        return tuple(int(channel) for channel in color_value)

    if isinstance(color_value, tuple) and len(color_value) == 3:
        return color_value

    raise ValueError(f"不支援的顏色格式：{color_value}")


def calculate_text_position(draw, text, font, x, y, align):
    """
    根據 align 計算最終文字繪製位置。

    規則：
    - left: x, y 直接作為左上起點
    - center: x, y 視為水平置中的 anchor point
    - right: x, y 視為文字右邊界的 anchor point

    參數：
    draw (ImageDraw.ImageDraw)
        Pillow 繪圖物件
    text (str)
        要繪製的文字
    font (ImageFont)
        文字字型
    x (int | float)
        水平 anchor 位置
    y (int | float)
        垂直繪製起點
    align (str)
        水平對齊模式

    回傳：
    tuple[float, int | float]
        Pillow draw.text 所需的位置座標
    """
    if align not in {"left", "center", "right"}:
        raise ValueError(f"不支援的對齊方式：{align}")

    # 取得文字寬度，用於 center / right 對齊計算。
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    # 根據 align 計算實際繪製位置；y 維持不變，僅調整水平座標。
    if align == "center":
        return x - (text_width / 2), y
    if align == "right":
        return x - text_width, y

    return x, y

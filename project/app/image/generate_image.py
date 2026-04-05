"""
generate_image.py

目前穩定版的 generate_image 主要負責 cycle diagram 底圖：

- 固定尺寸畫布
- 外框與左側刻度
- path 幾何
- marker
- guides

檔案內仍保留 `legacy_generate_image()`，方便對照早期
「載入 base image template 再另存」的舊版做法。
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from models.shared_data import SharedData
from renderer import calculate_text_position, parse_color, resolve_path


def legacy_generate_image(
    shared_data: SharedData,
    *,
    template_config: dict,
    base_dir: Path,
    output_path: Path,
) -> Path:
    """
    舊版 generate_image。

    這個版本只做：
    載入 template_image -> 另存成 pipeline 的中間圖片
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


SUPPORTED_MARKER_TYPES = {"filled_circle", "hollow_circle", "triangle_up"}
SUPPORTED_SEGMENT_TYPES = {"hold", "rise", "fall"}


def generate_image(
    shared_data: SharedData,
    *,
    template_config: dict,
    base_dir: Path,
    output_path: Path,
) -> Path:
    """
    依 cycle_count 生成固定版型的 cycle diagram 底圖。

    這一層只負責：
    - 固定尺寸畫布
    - 外框
    - 左側短刻度
    - 動態 cycle path
    - 固定 marker
    """
    image_size = template_config["image_size"]
    frame_config = template_config["frame"]
    tick_config = template_config["left_ticks"]
    path_builder = template_config["path_builder"]

    cycle_count = resolve_cycle_count(shared_data, path_builder)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    background_color = parse_color(frame_config.get("background_color", "#FFFFFF"))
    image = Image.new(
        "RGBA",
        (int(image_size["width"]), int(image_size["height"])),
        background_color,
    )
    draw = ImageDraw.Draw(image)

    draw_frame(draw, frame_config)
    draw_left_ticks(draw, tick_config)

    path_result = build_cycle_path_result(
        cycle_count=cycle_count,
        frame_config=frame_config,
        path_builder=path_builder,
    )
    # 目前保留簡單 debug 輸出，方便確認實際存在的 named anchors。
    print("named_anchors.keys():")
    for anchor_name in path_result["named_anchors"].keys():
        print(f"* {anchor_name}")
    points = path_result["points"]
    line_style = path_builder["line_style"]
    draw.line(
        points,
        fill=parse_color(line_style["color"]),
        width=int(line_style["width"]),
        joint="curve",
    )

    draw_markers(
        draw,
        markers=template_config.get("markers", []),
        anchor_context={
            "start": points[0],
            "end": points[-1],
            "named_anchors": path_result["named_anchors"],
            "path_points": points,
        },
        default_color=parse_color(line_style["color"]),
    )
    # guides 屬於 generate_image 的輔助圖形層：
    # 會畫在 frame / ticks / cycle path / markers 之後，
    # 並在 overlay_text 疊字之前完成，避免和文字層責任混在一起。
    draw_guides(draw, template_config.get("guides", []), base_dir=base_dir)

    image.save(output_path, format="PNG")
    image.close()
    return output_path


def resolve_cycle_count(shared_data: SharedData, path_builder: dict) -> int:
    """從 SharedData 取得合法的 cycle_count。"""
    source_name = path_builder["cycle_count_source"]
    if source_name not in shared_data.payload:
        raise ValueError(
            f"generate_image 缺少 cycle_count 欄位: record_id='{shared_data.record_id}', source='{source_name}'"
        )

    raw_value = shared_data.get_value(source_name)
    try:
        numeric_value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"cycle_count 不是數值: source='{source_name}', value='{raw_value}'"
        ) from exc

    if not numeric_value.is_integer():
        raise ValueError(f"cycle_count 必須是整數，目前值為: {raw_value}")

    cycle_count = int(numeric_value)
    min_cycle_count = int(path_builder["min_cycle_count"])
    if cycle_count < min_cycle_count:
        raise ValueError(
            f"cycle_count 必須大於等於 {min_cycle_count}，目前值為: {cycle_count}"
        )

    return cycle_count


def draw_frame(draw: ImageDraw.ImageDraw, frame_config: dict) -> None:
    """畫出固定外框。"""
    draw.rectangle(
        [
            (int(frame_config["left"]), int(frame_config["top"])),
            (int(frame_config["right"]), int(frame_config["bottom"])),
        ],
        outline=parse_color(frame_config["border_color"]),
        width=int(frame_config["border_width"]),
    )


def draw_left_ticks(draw: ImageDraw.ImageDraw, tick_config: dict) -> None:
    """畫出左側固定短刻度。"""
    x = int(tick_config["x"])
    tick_length = int(tick_config["tick_length"])
    color = parse_color(tick_config["color"])
    width = int(tick_config["width"])

    for level_y in tick_config["levels"]:
        y = int(level_y)
        draw.line(
            [(x, y), (x + tick_length, y)],
            fill=color,
            width=width,
        )


def build_cycle_path_result(
    *,
    cycle_count: int,
    frame_config: dict,
    path_builder: dict,
) -> dict:
    """依 cycle_count 與 block 規則生成折線節點。"""
    levels = path_builder["levels"]
    cycle_zone = path_builder["cycle_zone"]
    cycle_zone_start_x = float(cycle_zone["start_x"])
    cycle_zone_end_x = float(cycle_zone["end_x"])
    usable_cycle_width = cycle_zone_end_x - cycle_zone_start_x
    block_width = usable_cycle_width / cycle_count

    current_x = float(frame_config["left"])
    current_y = float(levels["start"])
    points: list[tuple[float, float]] = [(current_x, current_y)]
    named_anchors: dict[str, tuple[float, float]] = {
        "path_start": points[0],
    }

    current_x, current_y = append_segments(
        points,
        segments=path_builder["left_lead_segments"],
        total_width=cycle_zone_start_x - float(frame_config["left"]),
        start_x=current_x,
        start_y=current_y,
        levels=levels,
    )
    # `lead_kink` 代表起始段中的轉折位置。
    # 目前 left_lead_segments 很簡單，幾何上會先與 lead_end 重合，
    # 但語意上仍保留為獨立 anchor，方便後續把 left lead 做得更細。
    named_anchors["lead_kink"] = (current_x, current_y)
    # `lead_end` 代表 left lead 區域的結束點。
    named_anchors["lead_end"] = (current_x, current_y)

    block_sequence = build_block_sequence(cycle_count, path_builder)
    for block_kind, block_index, block_segments in block_sequence:
        if block_kind == "outer":
            if block_index == 1:
                named_anchors.update(
                    compute_outer_first_special_anchors(
                        segments=block_segments,
                        total_width=block_width,
                        start_x=current_x,
                        start_y=current_y,
                        levels=levels,
                    )
                )
            elif block_index == 2:
                named_anchors.update(
                    compute_outer_last_special_anchors(
                        segments=block_segments,
                        total_width=block_width,
                        start_x=current_x,
                        start_y=current_y,
                        levels=levels,
                    )
                )
        current_x, current_y = append_segments(
            points,
            segments=block_segments,
            total_width=block_width,
            start_x=current_x,
            start_y=current_y,
            levels=levels,
            segment_callback=build_block_anchor_callback(
                named_anchors,
                block_kind=block_kind,
                block_index=block_index,
            ),
        )

    named_anchors["tail_start"] = (current_x, current_y)
    current_x, current_y = append_segments(
        points,
        segments=path_builder["right_tail_segments"],
        total_width=float(frame_config["right"]) - cycle_zone_end_x,
        start_x=current_x,
        start_y=current_y,
        levels=levels,
    )
    named_anchors["path_end"] = (current_x, current_y)

    return {
        "points": points,
        "named_anchors": named_anchors,
    }


def build_block_sequence(cycle_count: int, path_builder: dict) -> list[tuple[str, int, list[dict]]]:
    """組出 outer_first / inner / outer_last 的 block 序列。"""
    outer_first_block = path_builder["outer_first_block"]
    inner_block = path_builder["inner_block"]
    outer_last_block = path_builder["outer_last_block"]

    sequence: list[tuple[str, int, list[dict]]] = [("outer", 1, outer_first_block)]
    inner_count = max(cycle_count - 2, 0)
    for index in range(1, inner_count + 1):
        sequence.append(("inner", index, inner_block))
    sequence.append(("outer", 2, outer_last_block))
    return sequence


def compute_outer_first_special_anchors(
    *,
    segments: list[dict],
    total_width: float,
    start_x: float,
    start_y: float,
    levels: dict,
) -> dict[str, tuple[float, float]]:
    current_x = start_x
    current_y = start_y
    total_ratio = sum(float(segment["ratio"]) for segment in segments)
    if total_ratio <= 0:
        raise ValueError("segment ratio total must be greater than 0.")

    inner_high_y = float(levels["inner_high"])
    inner_low_y = float(levels["inner_low"])
    anchors: dict[str, tuple[float, float]] = {}

    for segment in segments:
        next_x = current_x + (total_width * float(segment["ratio"]) / total_ratio)
        next_y = float(levels[segment["to_level"]])

        if (
            segment["type"] == "rise"
            and segment["to_level"] == "outer_high"
            and "outer_1_rise_at_inner_high" not in anchors
        ):
            if current_y == next_y:
                raise ValueError("Cannot interpolate outer_1_rise_at_inner_high on a flat segment.")

            interpolation_ratio = (inner_high_y - current_y) / (next_y - current_y)
            if not 0.0 <= interpolation_ratio <= 1.0:
                raise ValueError("inner_high is outside the first outer rise segment.")

            anchor_x = current_x + ((next_x - current_x) * interpolation_ratio)
            anchors["outer_1_rise_at_inner_high"] = (anchor_x, inner_high_y)

        if (
            segment["type"] == "fall"
            and segment["to_level"] == "inner_high"
            and "outer_1_inner_high" not in anchors
        ):
            anchors["outer_1_inner_high"] = (next_x, inner_high_y)

        if (
            segment["type"] == "hold"
            and segment["to_level"] == "inner_high"
            and "outer_1_inner_high_end" not in anchors
        ):
            anchors["outer_1_inner_high_end"] = (next_x, inner_high_y)

        if (
            segment["type"] == "fall"
            and segment["to_level"] == "outer_low"
            and "outer_1_fall_at_inner_low" not in anchors
        ):
            anchor_x = interpolate_segment_x_at_y(
                start_x=current_x,
                start_y=current_y,
                end_x=next_x,
                end_y=next_y,
                target_y=inner_low_y,
                anchor_name="outer_1_fall_at_inner_low",
            )
            anchors["outer_1_fall_at_inner_low"] = (anchor_x, inner_low_y)

        if (
            segment["type"] == "rise"
            and segment["to_level"] == "inner_low"
            and "outer_1_inner_low" not in anchors
        ):
            anchors["outer_1_inner_low"] = (next_x, inner_low_y)

        if (
            segment["type"] == "hold"
            and segment["to_level"] == "inner_low"
            and "outer_1_inner_low_end" not in anchors
        ):
            anchors["outer_1_inner_low_end"] = (next_x, inner_low_y)

        current_x = next_x
        current_y = next_y

    if "outer_1_rise_at_inner_high" not in anchors:
        raise ValueError("Missing geometry for outer_1_rise_at_inner_high.")
    if "outer_1_inner_high" not in anchors:
        raise ValueError("Missing geometry for outer_1_inner_high.")
    if "outer_1_inner_high_end" not in anchors:
        raise ValueError("Missing geometry for outer_1_inner_high_end.")
    if "outer_1_fall_at_inner_low" not in anchors:
        raise ValueError("Missing geometry for outer_1_fall_at_inner_low.")
    if "outer_1_inner_low" not in anchors:
        raise ValueError("Missing geometry for outer_1_inner_low.")
    if "outer_1_inner_low_end" not in anchors:
        raise ValueError("Missing geometry for outer_1_inner_low_end.")

    return anchors


def compute_outer_last_special_anchors(
    *,
    segments: list[dict],
    total_width: float,
    start_x: float,
    start_y: float,
    levels: dict,
) -> dict[str, tuple[float, float]]:
    current_x = start_x
    current_y = start_y
    total_ratio = sum(float(segment["ratio"]) for segment in segments)
    if total_ratio <= 0:
        raise ValueError("segment ratio total must be greater than 0.")

    inner_high_y = float(levels["inner_high"])
    inner_low_y = float(levels["inner_low"])
    anchors: dict[str, tuple[float, float]] = {}

    for segment in segments:
        next_x = current_x + (total_width * float(segment["ratio"]) / total_ratio)
        next_y = float(levels[segment["to_level"]])

        if (
            segment["type"] == "rise"
            and segment["to_level"] == "outer_high"
            and "outer_2_rise_at_inner_high" not in anchors
        ):
            anchor_x = interpolate_segment_x_at_y(
                start_x=current_x,
                start_y=current_y,
                end_x=next_x,
                end_y=next_y,
                target_y=inner_high_y,
                anchor_name="outer_2_rise_at_inner_high",
            )
            anchors["outer_2_rise_at_inner_high"] = (anchor_x, inner_high_y)

        if (
            segment["type"] == "fall"
            and segment["to_level"] == "inner_high"
            and "outer_2_inner_high" not in anchors
        ):
            anchors["outer_2_inner_high"] = (next_x, inner_high_y)

        if (
            segment["type"] == "hold"
            and segment["to_level"] == "inner_high"
            and "outer_2_inner_high_end" not in anchors
        ):
            anchors["outer_2_inner_high_end"] = (next_x, inner_high_y)

        if (
            segment["type"] == "fall"
            and segment["to_level"] == "outer_low"
            and "outer_2_fall_at_inner_low" not in anchors
        ):
            anchor_x = interpolate_segment_x_at_y(
                start_x=current_x,
                start_y=current_y,
                end_x=next_x,
                end_y=next_y,
                target_y=inner_low_y,
                anchor_name="outer_2_fall_at_inner_low",
            )
            anchors["outer_2_fall_at_inner_low"] = (anchor_x, inner_low_y)

        if (
            segment["type"] == "rise"
            and segment["to_level"] == "inner_low"
            and "outer_2_inner_low" not in anchors
        ):
            anchors["outer_2_inner_low"] = (next_x, inner_low_y)

        if (
            segment["type"] == "hold"
            and segment["to_level"] == "inner_low"
            and "outer_2_inner_low_end" not in anchors
        ):
            anchors["outer_2_inner_low_end"] = (next_x, inner_low_y)

        current_x = next_x
        current_y = next_y

    if "outer_2_rise_at_inner_high" not in anchors:
        raise ValueError("Missing geometry for outer_2_rise_at_inner_high.")
    if "outer_2_inner_high" not in anchors:
        raise ValueError("Missing geometry for outer_2_inner_high.")
    if "outer_2_inner_high_end" not in anchors:
        raise ValueError("Missing geometry for outer_2_inner_high_end.")
    if "outer_2_fall_at_inner_low" not in anchors:
        raise ValueError("Missing geometry for outer_2_fall_at_inner_low.")
    if "outer_2_inner_low" not in anchors:
        raise ValueError("Missing geometry for outer_2_inner_low.")
    if "outer_2_inner_low_end" not in anchors:
        raise ValueError("Missing geometry for outer_2_inner_low_end.")

    return anchors


def interpolate_segment_x_at_y(
    *,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    target_y: float,
    anchor_name: str,
) -> float:
    if start_y == end_y:
        raise ValueError(f"Cannot interpolate {anchor_name} on a flat segment.")

    interpolation_ratio = (target_y - start_y) / (end_y - start_y)
    if not 0.0 <= interpolation_ratio <= 1.0:
        raise ValueError(f"{anchor_name} target y is outside the segment range.")

    return start_x + ((end_x - start_x) * interpolation_ratio)


def append_segments(
    points: list[tuple[float, float]],
    *,
    segments: list[dict],
    total_width: float,
    start_x: float,
    start_y: float,
    levels: dict,
    segment_callback=None,
) -> tuple[float, float]:
    """依 segment list 追加折線節點。"""
    current_x = start_x
    current_y = start_y
    total_ratio = sum(float(segment["ratio"]) for segment in segments)
    if total_ratio <= 0:
        raise ValueError("segment ratio 總和必須大於 0。")

    for segment in segments:
        next_x = current_x + (total_width * float(segment["ratio"]) / total_ratio)
        next_y = float(levels[segment["to_level"]])
        points.append((next_x, next_y))
        if segment_callback is not None:
            segment_callback(segment, (next_x, next_y))
        current_x = next_x
        current_y = next_y

    return current_x, current_y


def build_block_anchor_callback(
    named_anchors: dict[str, tuple[float, float]],
    *,
    block_kind: str,
    block_index: int,
):
    """
    依 block 類型與 index 註冊穩定命名 anchor。

    命名規則只使用 index，不使用 last。
    """
    high_level_name = f"{block_kind}_high"
    low_level_name = f"{block_kind}_low"

    def callback(segment: dict, point: tuple[float, float]) -> None:
        if segment["type"] != "hold":
            return

        if segment["to_level"] == high_level_name:
            named_anchors[f"{block_kind}_{block_index}_high"] = point
            return

        if segment["to_level"] == low_level_name:
            named_anchors[f"{block_kind}_{block_index}_low"] = point

    return callback


def draw_markers(
    draw: ImageDraw.ImageDraw,
    *,
    markers: list[dict],
    anchor_context: dict,
    default_color: tuple[int, int, int],
) -> None:
    """統一處理 marker 清單。"""
    for marker in markers:
        base_point = resolve_marker_anchor(marker, anchor_context)
        draw_marker(
            draw,
            marker=marker,
            base_point=base_point,
            default_color=default_color,
        )


def draw_guides(draw: ImageDraw.ImageDraw, guides: list[dict], *, base_dir: Path) -> None:
    """繪製 cycle diagram 的輔助虛線與箭頭。"""
    for guide in guides:
        guide_type = guide["type"]
        if guide_type == "dashed_line":
            draw_dashed_line(draw, guide)
            continue

        if guide_type == "arrow":
            draw_arrow(draw, guide)
            continue

        if guide_type == "dimension":
            draw_dimension(draw, guide, base_dir=base_dir)
            continue

        raise ValueError(f"不支援的 guide type: {guide_type}")


def draw_dashed_line(draw: ImageDraw.ImageDraw, guide: dict) -> None:
    """用多段短線畫出最小可用的破折線。"""
    x1 = float(guide["x1"])
    y1 = float(guide["y1"])
    x2 = float(guide["x2"])
    y2 = float(guide["y2"])
    color = parse_color(guide["color"])
    width = int(guide["width"])
    dash_on, dash_off = (float(value) for value in guide["dash"])

    dx = x2 - x1
    dy = y2 - y1
    line_length = math.hypot(dx, dy)
    if line_length == 0:
        return

    unit_x = dx / line_length
    unit_y = dy / line_length
    current_length = 0.0

    while current_length < line_length:
        start_x = x1 + unit_x * current_length
        start_y = y1 + unit_y * current_length
        end_length = min(current_length + dash_on, line_length)
        end_x = x1 + unit_x * end_length
        end_y = y1 + unit_y * end_length
        draw.line([(start_x, start_y), (end_x, end_y)], fill=color, width=width)
        current_length += dash_on + dash_off


def draw_arrow(draw: ImageDraw.ImageDraw, guide: dict) -> None:
    """繪製簡單箭頭：主幹線 + 兩條箭頭邊。"""
    x1 = float(guide["x1"])
    y1 = float(guide["y1"])
    x2 = float(guide["x2"])
    y2 = float(guide["y2"])
    color = parse_color(guide["color"])
    width = int(guide["width"])

    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    dx = x2 - x1
    dy = y2 - y1
    line_length = math.hypot(dx, dy)
    if line_length == 0:
        return

    unit_x = dx / line_length
    unit_y = dy / line_length
    head_length = max(10.0, width * 4.0)
    head_angle = math.radians(28)

    left_x = x2 - head_length * (
        unit_x * math.cos(head_angle) + unit_y * math.sin(head_angle)
    )
    left_y = y2 - head_length * (
        unit_y * math.cos(head_angle) - unit_x * math.sin(head_angle)
    )
    right_x = x2 - head_length * (
        unit_x * math.cos(head_angle) - unit_y * math.sin(head_angle)
    )
    right_y = y2 - head_length * (
        unit_y * math.cos(head_angle) + unit_x * math.sin(head_angle)
    )

    draw.line([(x2, y2), (left_x, left_y)], fill=color, width=width)
    draw.line([(x2, y2), (right_x, right_y)], fill=color, width=width)


def draw_dimension(draw: ImageDraw.ImageDraw, guide: dict, *, base_dir: Path) -> None:
    """繪製最小可用的水平雙向箭頭與中間標註文字。"""
    x1 = float(guide["x1"])
    y1 = float(guide["y1"])
    x2 = float(guide["x2"])
    y2 = float(guide["y2"])
    color = parse_color(guide["color"])
    width = int(guide["width"])
    arrow_size = float(guide["arrow_size"])
    text = str(guide["text"])
    text_offset = float(guide["text_offset"])

    if abs(y1 - y2) > 0.001:
        raise ValueError("dimension 目前只支援水平線段。")

    line_y = y1
    draw.line([(x1, line_y), (x2, line_y)], fill=color, width=width)

    # 左端箭頭向右、右端箭頭向左。
    draw.line([(x1, line_y), (x1 + arrow_size, line_y - arrow_size / 2)], fill=color, width=width)
    draw.line([(x1, line_y), (x1 + arrow_size, line_y + arrow_size / 2)], fill=color, width=width)
    draw.line([(x2, line_y), (x2 - arrow_size, line_y - arrow_size / 2)], fill=color, width=width)
    draw.line([(x2, line_y), (x2 - arrow_size, line_y + arrow_size / 2)], fill=color, width=width)

    font = load_dimension_font(base_dir, arrow_size)
    text_x = (x1 + x2) / 2
    text_y = line_y + text_offset
    text_position = calculate_text_position(draw, text, font, text_x, text_y, "center")
    draw.text(text_position, text, fill=color, font=font)


def load_dimension_font(base_dir: Path, arrow_size: float):
    """為 dimension 文字載入固定粗體字型。"""
    font_path = resolve_path(base_dir, "assets/fonts/NotoSansTC-Bold.ttf")
    font_size = max(18, int(arrow_size * 4))
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=font_size)

    return ImageFont.load_default()


def resolve_marker_anchor(marker: dict, anchor_context: dict) -> tuple[float, float]:
    """
    解析 marker 的 base anchor。

    目前先支援：
    - start
    - end

    但 anchor_context 保留未來擴充：
    - named_anchors
    - path_points
    """
    anchor_name = marker["anchor"]

    if anchor_name in {"start", "end"}:
        return anchor_context[anchor_name]

    if anchor_name == "named_anchor":
        anchor_ref = marker.get("anchor_ref")
        if not isinstance(anchor_ref, str) or not anchor_ref.strip():
            raise ValueError("marker 使用 named_anchor 時，必須提供非空的 anchor_ref。")

        named_anchors = anchor_context.get("named_anchors", {})
        if anchor_ref not in named_anchors:
            raise ValueError(f"找不到指定的 named_anchor: {anchor_ref}")

        return named_anchors[anchor_ref]

    raise ValueError(f"不支援的 marker anchor: {anchor_name}")


def draw_marker(
    draw: ImageDraw.ImageDraw,
    *,
    marker: dict,
    base_point: tuple[float, float],
    default_color: tuple[int, int, int],
) -> None:
    """依 marker type 畫單一 marker。"""
    base_x, base_y = base_point
    center_x = base_x + float(marker["dx"])
    center_y = base_y + float(marker["dy"])
    marker_type = marker["type"]
    color = parse_color(marker.get("color", default_color))

    if marker_type == "filled_circle":
        draw_filled_circle(draw, center_x, center_y, marker, color)
        return

    if marker_type == "hollow_circle":
        draw_hollow_circle(draw, center_x, center_y, marker, color)
        return

    if marker_type == "triangle_up":
        draw_up_triangle(draw, center_x, center_y, marker, color)
        return

    raise ValueError(f"不支援的 marker type: {marker_type}")


def draw_filled_circle(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    center_y: float,
    marker: dict,
    color: tuple[int, int, int],
) -> None:
    """畫實心圓。"""
    radius = float(marker["size"]) / 2
    draw.ellipse(
        [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y + radius),
        ],
        fill=color,
        outline=color,
    )


def draw_hollow_circle(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    center_y: float,
    marker: dict,
    color: tuple[int, int, int],
) -> None:
    """畫空心圓。"""
    radius = float(marker["size"]) / 2
    outline_width = int(marker.get("outline_width", 2))
    draw.ellipse(
        [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y + radius),
        ],
        outline=color,
        width=outline_width,
    )


def draw_up_triangle(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    center_y: float,
    marker: dict,
    color: tuple[int, int, int],
) -> None:
    """畫固定朝上的小三角。"""
    size = float(marker["size"])
    half_width = size / 2
    # marker 對齊語意：
    # - filled_circle / hollow_circle：anchor = 幾何中心
    # - triangle_up：anchor = 幾何中心
    points = [
        (center_x, center_y - half_width),
        (center_x - half_width, center_y + half_width),
        (center_x + half_width, center_y + half_width),
    ]
    draw.polygon(points, fill=color, outline=color)

"""
config_loader.py

最小外部 config loader。
這一版只支援 MVP pipeline：
shared data -> generate_image -> overlay_text
"""

from __future__ import annotations

import json
from pathlib import Path

from renderer import resolve_path


SUPPORTED_STEPS = ("generate_image", "overlay_text")


class LegacyPipelineConfigLoader:
    """讀取並驗證 MVP pipeline config。"""

    def __init__(self, config_path: Path | str, *, base_dir: Path | str):
        self.config_path = Path(config_path)
        self.base_dir = Path(base_dir)

    def load(self) -> dict:
        """載入 pipeline config 與 image template mapping。"""
        pipeline_config = self._load_json(self.config_path)
        self._validate_pipeline_config(pipeline_config)

        mapping_path = self._resolve_config_reference(
            self.config_path,
            pipeline_config["image_template_mapping"],
        )
        image_template_config = self._load_json(mapping_path)
        self._validate_image_template_config(image_template_config)

        merged_render_defaults = {
            "default_font_size": 24,
            "default_color": "#000000",
            "default_align": "left",
            **pipeline_config.get("render_defaults", {}),
        }

        return {
            "project_id": pipeline_config["project_id"],
            "test_id": pipeline_config["test_id"],
            "pipeline_steps": pipeline_config["pipeline"],
            "render_defaults": merged_render_defaults,
            "image_template_config": image_template_config,
            "image_template_mapping_path": mapping_path,
        }

    def _load_json(self, path: Path) -> dict:
        """讀取 JSON 檔。"""
        if not path.exists():
            raise FileNotFoundError(f"找不到 config 檔案: {path}")

        with path.open("r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON 格式錯誤: {path}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"JSON 根節點必須是物件: {path}")

        return data

    def _validate_pipeline_config(self, config_data: dict) -> None:
        """驗證 pipeline config。"""
        required_keys = [
            "project_id",
            "test_id",
            "image_template_mapping",
            "pipeline",
        ]
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"pipeline config 缺少必要欄位: {key}")

        if not isinstance(config_data["project_id"], str) or not config_data["project_id"].strip():
            raise ValueError("project_id 必須是非空字串。")

        if not isinstance(config_data["test_id"], str) or not config_data["test_id"].strip():
            raise ValueError("test_id 必須是非空字串。")

        if (
            not isinstance(config_data["image_template_mapping"], str)
            or not config_data["image_template_mapping"].strip()
        ):
            raise ValueError("image_template_mapping 必須是非空字串。")

        pipeline_steps = config_data["pipeline"]
        if not isinstance(pipeline_steps, list) or not pipeline_steps:
            raise ValueError("pipeline 必須是非空列表。")

        step_names: list[str] = []
        for step_config in pipeline_steps:
            if not isinstance(step_config, dict):
                raise ValueError("pipeline step 必須是物件。")

            step_name = step_config.get("step")
            if step_name not in SUPPORTED_STEPS:
                raise ValueError(f"不支援的 step 名稱: {step_name}")

            step_names.append(step_name)

        if step_names != ["generate_image", "overlay_text"]:
            raise ValueError(
                "目前 MVP pipeline 順序必須固定為: generate_image -> overlay_text"
            )

        generate_artifact_key = pipeline_steps[0].get("artifact_key", "base_image")
        overlay_input_key = pipeline_steps[1].get("input_artifact_key", "base_image")
        if generate_artifact_key != overlay_input_key:
            raise ValueError(
                "overlay_text 的 input_artifact_key 必須對應 generate_image 的 artifact_key。"
            )

        render_defaults = config_data.get("render_defaults", {})
        if render_defaults and not isinstance(render_defaults, dict):
            raise ValueError("render_defaults 必須是物件。")

    def _validate_image_template_config(self, config_data: dict) -> None:
        """驗證 image template mapping。"""
        required_keys = ["template_id", "template_image", "fields"]
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"image template mapping 缺少必要欄位: {key}")

        if not isinstance(config_data["template_id"], str) or not config_data["template_id"].strip():
            raise ValueError("template_id 必須是非空字串。")

        if not isinstance(config_data["template_image"], str) or not config_data["template_image"].strip():
            raise ValueError("template_image 必須是非空字串。")

        template_image_path = resolve_path(self.base_dir, config_data["template_image"])
        if not template_image_path.exists():
            raise FileNotFoundError(f"找不到 image template 檔案: {template_image_path}")

        fields = config_data["fields"]
        if not isinstance(fields, list):
            raise ValueError("fields 必須是列表。")

        for field_index, field in enumerate(fields, start=1):
            if not isinstance(field, dict):
                raise ValueError(f"fields[{field_index}] 必須是物件。")

            for key in ("source", "x", "y"):
                if key not in field:
                    raise ValueError(f"fields[{field_index}] 缺少必要欄位: {key}")

    def _resolve_config_reference(self, source_path: Path, reference: str) -> Path:
        """解析 config 對 config 的相對引用。"""
        reference_path = Path(reference)
        if reference_path.is_absolute():
            return reference_path

        return (source_path.parent / reference_path).resolve()


SUPPORTED_TEMPLATE_KIND = "cycle_diagram"
SUPPORTED_SEGMENT_TYPES = {"hold", "rise", "fall"}
SUPPORTED_MARKER_ANCHORS = {"start", "end", "named_anchor"}
SUPPORTED_MARKER_TYPES = {"filled_circle", "hollow_circle", "triangle_up"}
SUPPORTED_GUIDE_TYPES = {"dashed_line", "arrow", "dimension"}


class PipelineConfigLoader:
    """讀取並驗證 MVP pipeline config。"""

    def __init__(self, config_path: Path | str, *, base_dir: Path | str):
        self.config_path = Path(config_path)
        self.base_dir = Path(base_dir)

    def load(self) -> dict:
        """載入 pipeline config 與 image template mapping。"""
        pipeline_config = self._load_json(self.config_path)
        self._validate_pipeline_config(pipeline_config)

        mapping_path = self._resolve_config_reference(
            self.config_path,
            pipeline_config["image_template_mapping"],
        )
        image_template_config = self._load_json(mapping_path)
        self._validate_image_template_config(image_template_config)

        merged_render_defaults = {
            "default_font_size": 24,
            "default_color": "#000000",
            "default_align": "left",
            **pipeline_config.get("render_defaults", {}),
        }

        return {
            "project_id": pipeline_config["project_id"],
            "test_id": pipeline_config["test_id"],
            "pipeline_steps": pipeline_config["pipeline"],
            "render_defaults": merged_render_defaults,
            "image_template_config": image_template_config,
            "image_template_mapping_path": mapping_path,
        }

    def _load_json(self, path: Path) -> dict:
        """讀取 JSON 檔。"""
        if not path.exists():
            raise FileNotFoundError(f"找不到 config 檔案: {path}")

        with path.open("r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON 格式錯誤: {path}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"JSON 根節點必須是物件: {path}")

        return data

    def _validate_pipeline_config(self, config_data: dict) -> None:
        """驗證 pipeline config。"""
        required_keys = [
            "project_id",
            "test_id",
            "image_template_mapping",
            "pipeline",
        ]
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"pipeline config 缺少必要欄位: {key}")

        pipeline_steps = config_data["pipeline"]
        if not isinstance(pipeline_steps, list) or not pipeline_steps:
            raise ValueError("pipeline 必須是非空列表。")

        step_names = [step.get("step") for step in pipeline_steps if isinstance(step, dict)]
        if step_names != ["generate_image", "overlay_text"]:
            raise ValueError("目前 MVP pipeline 順序必須固定為: generate_image -> overlay_text")

        generate_artifact_key = pipeline_steps[0].get("artifact_key", "base_image")
        overlay_input_key = pipeline_steps[1].get("input_artifact_key", "base_image")
        if generate_artifact_key != overlay_input_key:
            raise ValueError("overlay_text 的 input_artifact_key 必須對應 generate_image 的 artifact_key。")

        render_defaults = config_data.get("render_defaults", {})
        if render_defaults and not isinstance(render_defaults, dict):
            raise ValueError("render_defaults 必須是物件。")

    def _validate_image_template_config(self, config_data: dict) -> None:
        """驗證 cycle_diagram template config。"""
        required_keys = [
            "template_id",
            "template_kind",
            "image_size",
            "frame",
            "left_ticks",
            "path_builder",
            "fields",
        ]
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"image template mapping 缺少必要欄位: {key}")

        if config_data["template_kind"] != SUPPORTED_TEMPLATE_KIND:
            raise ValueError("目前只支援 template_kind = cycle_diagram。")

        self._validate_image_size(config_data["image_size"])
        self._validate_frame(config_data["frame"])
        self._validate_left_ticks(config_data["left_ticks"])
        self._validate_path_builder(config_data["path_builder"])
        self._validate_markers(config_data.get("markers", []))
        self._validate_guides(config_data.get("guides", []))

        fields = config_data["fields"]
        if not isinstance(fields, list):
            raise ValueError("fields 必須是列表。")

    def _validate_image_size(self, image_size: dict) -> None:
        for key in ("width", "height"):
            if key not in image_size:
                raise ValueError(f"image_size 缺少必要欄位: {key}")

    def _validate_frame(self, frame: dict) -> None:
        for key in ("left", "right", "top", "bottom", "border_color", "border_width", "background_color"):
            if key not in frame:
                raise ValueError(f"frame 缺少必要欄位: {key}")

    def _validate_left_ticks(self, left_ticks: dict) -> None:
        for key in ("x", "tick_length", "levels", "color", "width"):
            if key not in left_ticks:
                raise ValueError(f"left_ticks 缺少必要欄位: {key}")

    def _validate_path_builder(self, path_builder: dict) -> None:
        required_keys = [
            "cycle_count_source",
            "min_cycle_count",
            "cycle_zone",
            "levels",
            "left_lead_segments",
            "outer_block",
            "inner_block",
            "right_tail_segments",
            "line_style",
        ]
        for key in required_keys:
            if key not in path_builder:
                raise ValueError(f"path_builder 缺少必要欄位: {key}")

        if int(path_builder["min_cycle_count"]) < 2:
            raise ValueError("min_cycle_count 必須大於等於 2。")

        cycle_zone = path_builder["cycle_zone"]
        for key in ("start_x", "end_x"):
            if key not in cycle_zone:
                raise ValueError(f"cycle_zone 缺少必要欄位: {key}")

        if not isinstance(path_builder["levels"], dict) or not path_builder["levels"]:
            raise ValueError("levels 必須是非空物件。")

        for segment_key in ("left_lead_segments", "outer_block", "inner_block", "right_tail_segments"):
            self._validate_segment_list(segment_key, path_builder[segment_key], path_builder["levels"])

        line_style = path_builder["line_style"]
        for key in ("color", "width"):
            if key not in line_style:
                raise ValueError(f"line_style 缺少必要欄位: {key}")

    def _validate_segment_list(self, segment_key: str, segments: list[dict], levels: dict) -> None:
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"{segment_key} 必須是非空列表。")

        for index, segment in enumerate(segments, start=1):
            for key in ("type", "ratio", "to_level"):
                if key not in segment:
                    raise ValueError(f"{segment_key}[{index}] 缺少必要欄位: {key}")

            if segment["type"] not in SUPPORTED_SEGMENT_TYPES:
                raise ValueError(f"{segment_key}[{index}] 的 type 不合法: {segment['type']}")

            if float(segment["ratio"]) <= 0:
                raise ValueError(f"{segment_key}[{index}] 的 ratio 必須大於 0。")

            if segment["to_level"] not in levels:
                raise ValueError(f"{segment_key}[{index}] 的 to_level 不存在於 levels: {segment['to_level']}")

    def _validate_markers(self, markers: list[dict]) -> None:
        if not isinstance(markers, list):
            raise ValueError("markers 必須是列表。")

        for index, marker in enumerate(markers, start=1):
            for key in ("marker_key", "anchor", "type", "dx", "dy", "size"):
                if key not in marker:
                    raise ValueError(f"markers[{index}] 缺少必要欄位: {key}")

            if not isinstance(marker["marker_key"], str) or not marker["marker_key"].strip():
                raise ValueError(f"markers[{index}] 的 marker_key 必須是非空字串。")

            if marker["anchor"] not in SUPPORTED_MARKER_ANCHORS:
                raise ValueError(f"markers[{index}] 的 anchor 不合法: {marker['anchor']}")

            if marker["type"] not in SUPPORTED_MARKER_TYPES:
                raise ValueError(f"markers[{index}] 的 type 不合法: {marker['type']}")

            if float(marker["size"]) <= 0:
                raise ValueError(f"markers[{index}] 的 size 必須大於 0。")

            if marker["anchor"] == "named_anchor":
                anchor_ref = marker.get("anchor_ref")
                if not isinstance(anchor_ref, str) or not anchor_ref.strip():
                    raise ValueError(
                        f"markers[{index}] 使用 named_anchor 時，必須提供非空的 anchor_ref。"
                    )

    def _validate_guides(self, guides: list[dict]) -> None:
        if not isinstance(guides, list):
            raise ValueError("guides 必須是列表。")

        for index, guide in enumerate(guides, start=1):
            for key in ("type", "x1", "y1", "x2", "y2", "color", "width"):
                if key not in guide:
                    raise ValueError(f"guides[{index}] 缺少必要欄位: {key}")

            if guide["type"] not in SUPPORTED_GUIDE_TYPES:
                raise ValueError(f"guides[{index}] 的 type 不合法: {guide['type']}")

            if float(guide["width"]) <= 0:
                raise ValueError(f"guides[{index}] 的 width 必須大於 0。")

            if guide["type"] == "dashed_line":
                dash = guide.get("dash")
                if (
                    not isinstance(dash, list)
                    or len(dash) != 2
                    or any(float(value) <= 0 for value in dash)
                ):
                    raise ValueError(
                        f"guides[{index}] 的 dashed_line 必須提供正數 dash，例如 [6, 4]。"
                    )

            if guide["type"] == "dimension":
                for key in ("arrow_size", "text", "text_offset"):
                    if key not in guide:
                        raise ValueError(f"guides[{index}] 的 dimension 缺少必要欄位: {key}")

                if float(guide["arrow_size"]) <= 0:
                    raise ValueError(f"guides[{index}] 的 arrow_size 必須大於 0。")

    def _resolve_config_reference(self, source_path: Path, reference: str) -> Path:
        """解析 config 對 config 的相對引用。"""
        reference_path = Path(reference)
        if reference_path.is_absolute():
            return reference_path

        return (source_path.parent / reference_path).resolve()

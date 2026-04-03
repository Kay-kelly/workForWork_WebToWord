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

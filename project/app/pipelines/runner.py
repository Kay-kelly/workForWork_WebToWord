"""
runner.py

第一版 pipeline runner。
只支援 shared data -> generate_image -> overlay_text。
"""

from pathlib import Path

from image.generate_image import generate_image
from image.overlay_text import overlay_text
from models.shared_data import SharedData


def run_pipeline(
    shared_data: SharedData,
    *,
    pipeline_steps: list[dict],
    template_config: dict,
    global_config: dict,
    base_dir: Path,
    output_dir: Path,
    debug_grid: bool = False,
) -> Path:
    """
    依序執行 pipeline step。

    第一版只支援：
    - generate_image
    - overlay_text
    """
    artifacts: dict[str, Path] = {}
    final_output_path: Path | None = None

    for step_config in pipeline_steps:
        step_name = step_config["step"]

        if step_name == "generate_image":
            artifact_key = step_config.get("artifact_key", "base_image")
            output_path = output_dir / "_intermediate" / f"{shared_data.record_id}_base.png"
            artifacts[artifact_key] = generate_image(
                shared_data,
                template_config=template_config,
                base_dir=base_dir,
                output_path=output_path,
            )
            continue

        if step_name == "overlay_text":
            input_artifact_key = step_config.get("input_artifact_key", "base_image")
            if input_artifact_key not in artifacts:
                raise ValueError(
                    f"overlay_text 找不到前一步產物: {input_artifact_key}"
                )

            final_output_path = build_final_output_path(shared_data, output_dir)
            overlay_text(
                shared_data,
                template_config=template_config,
                global_config=global_config,
                base_dir=base_dir,
                input_image_path=artifacts[input_artifact_key],
                output_path=final_output_path,
                debug_grid=debug_grid,
            )
            continue

        raise ValueError(f"目前不支援的 pipeline step: {step_name}")

    if final_output_path is None:
        raise ValueError("Pipeline 沒有產出最終圖片。")

    return final_output_path


def build_final_output_path(shared_data: SharedData, output_dir: Path) -> Path:
    """建立最終輸出檔名。"""
    output_name = shared_data.get_value("output_name")

    if output_name is None or str(output_name).strip() == "":
        file_name = shared_data.record_id
    else:
        file_name = str(output_name).strip()

    if not file_name.lower().endswith(".png"):
        file_name = f"{file_name}.png"

    return output_dir / file_name

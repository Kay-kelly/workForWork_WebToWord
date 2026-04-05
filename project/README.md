# project/ 目錄導引

`project/` 是目前實際執行與開發的工作區。

## 目前主要入口

目前建議優先使用：

- `app/pipeline_main.py`

執行方式：

```powershell
.\.venv\Scripts\python.exe project\app\pipeline_main.py
```

這條流程目前對應：

- `SharedData`
- `generate_image`
- `overlay_text`
- `cycle_diagram.json`

這裡的 pipeline 是目前 stabilization 階段的 MVP 固定流程，
不是完整通用 pipeline 引擎。

目前實際落地的步驟順序固定為：

- `generate_image -> overlay_text`

目前還沒有落地：

- 任意 step 組合
- 部分流程執行
- 完整通用的 step 參數化 pipeline

## 舊版入口

- `app/main.py`

這是較早期的圖片貼字流程，仍保留作為舊版相容入口，但不是目前 cycle diagram MVP 的主要入口。

## 目前最常看的檔案

- `config/image_templates/cycle_diagram.json`
- `app/image/generate_image.py`
- `app/image/overlay_text.py`
- `app/pipelines/config_loader.py`
- `docs/cycle_diagram_marker_guide.md`

## 主要目錄

- `app/`
  - 程式主體
- `config/`
  - pipeline 與 image template 設定
- `data/`
  - Excel 示例輸入
- `output/`
  - 圖片輸出
- `assets/`
  - 字型與模板資源

## 輸出位置

完整 pipeline 成功執行後，輸出會在：

```text
project/output/pipeline_mvp/
```

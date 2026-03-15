# BakeOutPic

一個以 Excel 驅動、可透過 `mapping.json` 設定的 Python 圖片產生工具。  
這個 repo 目前定位為學習 / 作品集專案，重點在展示如何把「資料輸入、模板配置、圖片輸出」整理成可維護的流程。

## 專案用途

程式會讀取 Excel 資料，依每列的 `template_id` 選擇模板，並依照 `config/mapping.json` 的設定，將文字寫入模板圖片後輸出為 PNG。

適合用在：

- Excel 批次產生圖卡或標示圖
- 依不同模板輸出測試或製程資訊
- 需要讓非工程人員調整 Excel 或 mapping 設定的情境

## 功能特色

- 使用 `openpyxl` 讀取 Excel
- 使用 `Pillow` 將文字寫入圖片模板
- 以 `mapping.json` 管理模板、欄位、座標、字型、顏色與格式
- 支援多模板與不同欄位配置
- 主程式不寫死實際商業欄位
- 內建 debug grid，方便校正 `x` / `y`
- 可用 PyInstaller 打包為 Windows `exe`

## 專案結構

```text
BakeOutPic/
├─ project/
│  ├─ app/
│  ├─ assets/
│  ├─ config/
│  ├─ data/
│  ├─ output/
│  ├─ requirements.txt
│  └─ README.md
├─ build_exe.ps1
└─ BakeOutPic.spec
```

## 快速開始

### 建立虛擬環境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 安裝依賴

```powershell
pip install -r project\requirements.txt
```

### 執行程式

請從 repo 根目錄執行：

```powershell
python project/app/main.py
```

### 輸出位置

成功執行後，圖片會輸出到：

```text
project/output/
```

## 核心概念

- `template_image`：模板底圖路徑
- `source`：對應 Excel 欄位名稱
- `x, y`：文字在圖片上的定位座標
- `format`：將 Excel 值套入輸出字串模板
- `output_name`：最終輸出檔名；若未提供則使用 `template_id + row_number`

## 公開 repo 建議

建議 repo 只保留可公開的示例資源與示例資料：

- `project/config/mapping.json`
- `project/data/input.xlsx`
- `project/assets/templates/`
- `project/assets/fonts/`

另外，`project/data/README.md` 與 `project/assets/templates/README.md` 已補上最小示例說明，方便 clone repo 後快速理解目前收錄的是示例檔還是實際素材。

若素材包含客戶資料、內部模板、商標或未授權字型，不建議直接公開。

目前 `mapping.json` 內可能含有比 repo 內更多的模板設定；若模板底圖尚未全部附上，公開前請補齊對應示例檔，或移除未提供的模板設定。

## 建議上傳 / 不建議上傳

建議上傳：

- `project/app/`
- `project/config/mapping.json`
- `project/requirements.txt`
- 可公開的 `project/assets/`
- 可公開的 `project/data/`
- `build_exe.ps1`
- `BakeOutPic.spec`
- `README.md`

不建議上傳：

- `project/output/`
- `dist/`、`build/`
- `.venv/`、`venv/`
- 真實生產資料 Excel
- 未授權字型、內部模板與敏感素材

## Windows 打包

本專案使用 PyInstaller 的 `onedir` 模式，讓使用者可以直接修改外部資源，例如：

- `config/mapping.json`
- `data/input.xlsx`
- `assets/templates/*`
- `assets/fonts/*`

打包指令：

```powershell
.\build_exe.ps1
```

打包後結構：

```text
dist/
  BakeOutPic/
    BakeOutPic.exe
    assets/
    config/
    data/
```

exe 執行後輸出位置：

```text
dist/BakeOutPic/output/
```

## 目前限制

- 目前以文字繪製為主，尚未支援自動縮字、換行與複雜排版
- 模板欄位與座標仍需手動調整
- 專案目前以 Windows 與 PyInstaller 打包情境為主

## 未來可擴充方向

- 多行文字與自動換行
- 字體自動縮放
- 條件欄位顯示
- 圖片貼圖、QR code、條碼
- 更完整的設定驗證與測試

## 補充

`project/README.md` 僅保留 `project/` 目錄內的簡短導引；對外說明請以本檔為主。

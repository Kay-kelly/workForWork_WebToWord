$ErrorActionPreference = "Stop"

$projectRoot = Join-Path $PSScriptRoot "project"
$venvPath = Join-Path $projectRoot "venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPath)) {
    Write-Host "建立虛擬環境..."
    python -m venv $venvPath
}

Write-Host "安裝或更新專案依賴..."
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $projectRoot "requirements.txt")
& $pythonExe -m pip install pyinstaller

Write-Host "開始打包 BakeOutPic.exe ..."
Push-Location $PSScriptRoot
try {
    & $pythonExe -m PyInstaller BakeOutPic.spec
}
finally {
    Pop-Location
}

Write-Host "打包完成。輸出目錄位於 dist\BakeOutPic\"

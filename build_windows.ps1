param()

$ErrorActionPreference = "Stop"

Write-Host "Installing packaging dependencies..."
python -m pip install -e .[pack]

Write-Host "Running tests..."
python -m pytest -q

Write-Host "Cleaning previous build output..."
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

Write-Host "Building Windows app with PyInstaller..."
python -m PyInstaller --noconfirm BatchVideoConcatTool.spec

Write-Host ""
Write-Host "Build complete."
Write-Host "App folder: dist\\BatchVideoConcatTool"
Write-Host "Executable: dist\\BatchVideoConcatTool\\BatchVideoConcatTool.exe"

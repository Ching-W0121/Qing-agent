# 求职 Agent 后端启动脚本 (Windows)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "求职 Agent 后端服务" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# 检查 Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "错误: 未找到 Python" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host "安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "启动服务..." -ForegroundColor Green
Write-Host "API 地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

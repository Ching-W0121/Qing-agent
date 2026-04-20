#!/bin/bash

# 求职 Agent 后端启动脚本

set -e

echo "======================================"
echo "求职 Agent 后端服务"
echo "======================================"

# 检查 Python
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 Python"
    exit 1
fi

# 安装依赖（如果需要）
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate  # Linux/Mac
# source venv/Scripts/activate  # Windows

echo "安装依赖..."
pip install -r requirements.txt

echo ""
echo "启动服务..."
echo "API 地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "======================================"

uvicorn app.main:app --host 127.0.0.1 --port 8000

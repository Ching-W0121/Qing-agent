#!/bin/bash

# 求职 Agent 前端启动脚本

echo "======================================"
echo "求职 Agent 前端服务"
echo "======================================"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
npm install

echo ""
echo "启动开发服务器..."
echo "前端地址: http://localhost:5173"
echo "======================================"

npm run dev

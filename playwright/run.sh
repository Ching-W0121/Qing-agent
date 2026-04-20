#!/bin/bash

# Playwright 浏览器自动化测试脚本

echo "======================================"
echo "Playwright 浏览器自动化"
echo "======================================"

# 检查 Python
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 Python"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 安装浏览器
echo "安装 Chromium..."
playwright install chromium

echo ""
echo "测试搜索功能..."
echo "======================================"

# 示例命令
python -m playwright.src.main --platform zhilian --keyword "品牌策划" --city 深圳

echo ""
echo "完成!"

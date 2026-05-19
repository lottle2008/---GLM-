#!/bin/bash

echo "=============================================="
echo "🎤 智谱AI 语音克隆 Web 服务"
echo "=============================================="

if [ -f "requirements.txt" ]; then
    echo "📦 检查并安装依赖..."
    pip install -q -r requirements.txt
fi

echo "🚀 启动服务..."
echo "🌐 访问地址: http://localhost:7860"
echo "=============================================="

python app.py

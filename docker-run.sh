#!/bin/bash

echo "=============================================="
echo "🎤 智谱AI语音克隆 - Docker一键部署脚本"
echo "=============================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误：未找到Docker，请先安装Docker"
    echo "下载地址：https://www.docker.com/get-started"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误：未找到Docker Compose，请先安装"
    exit 1
fi

# 停止并删除旧容器
echo "⚡ 停止并清理旧容器..."
docker-compose down

# 构建并启动新容器
echo "🚀 构建并启动服务..."
docker-compose up -d --build

if [ $? -eq 0 ]; then
    echo "✅ Docker部署完成！"
    echo "=============================================="
    echo "🌐 访问地址: http://localhost:7860"
    echo "📂 数据目录: ./outputs (音频文件)"
    echo "🗄️ 数据库: ./voices.db (音色数据)"
    echo "📋 查看日志: docker-compose logs -f"
    echo "⏹️ 停止服务: docker-compose down"
    echo "=============================================="
    
    # 等待服务启动
    echo "⏳ 等待服务启动..."
    sleep 3
    
    # 尝试打开浏览器
    if command -v open &> /dev/null; then
        open http://localhost:7860
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:7860
    fi
else
    echo "❌ Docker部署失败，请检查错误信息"
    exit 1
fi

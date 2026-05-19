#!/bin/bash

echo "=============================================="
echo "🎤 智谱AI语音克隆 - Mac打包脚本"
echo "=============================================="

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3，请先安装Python 3.7+"
    echo "下载地址：https://www.python.org/downloads/macos/"
    exit 1
fi

# 检查PyInstaller是否安装
if ! pip3 show pyinstaller &> /dev/null; then
    echo "📦 安装PyInstaller..."
    pip3 install pyinstaller
    if [ $? -ne 0 ]; then
        echo "❌ 安装PyInstaller失败"
        exit 1
    fi
fi

# 停止可能正在运行的服务
echo "⚡ 停止端口7860占用..."
lsof -ti:7860 | xargs kill -9 2>/dev/null

# 创建输出目录
mkdir -p dist build

echo "🚀 开始打包..."
# 使用--noconfirm禁用确认提示
python3 -m PyInstaller zhipu_audio.spec --clean --noconfirm

if [ $? -eq 0 ]; then
    echo "✅ 打包完成！"
    echo "📂 输出目录: dist/ZhipuAudio.app"
else
    echo "❌ 打包失败，请检查错误信息"
    exit 1
fi

# 复制必要文件到输出目录
echo "📋 复制资源文件..."
cp voices.db dist/ZhipuAudio.app/Contents/MacOS/voices.db 2>/dev/null || true

echo "=============================================="
echo "📦 打包完成！"
echo "=============================================="
echo "输出位置: dist/ZhipuAudio.app"
echo "运行方式: 双击 ZhipuAudio.app"

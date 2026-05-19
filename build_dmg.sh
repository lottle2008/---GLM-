#!/bin/bash

echo "=============================================="
echo "🎤 智谱AI语音克隆 - Mac DMG打包脚本"
echo "=============================================="

# 检查是否已构建app
if [ ! -d "dist/ZhipuAudio.app" ]; then
    echo "❌ 错误：未找到ZhipuAudio.app，请先运行build_mac.sh"
    exit 1
fi

# 检查hdiutil是否可用
if ! command -v hdiutil &> /dev/null; then
    echo "❌ 错误：hdiutil不可用，此脚本仅适用于macOS"
    exit 1
fi

# 创建DMG临时目录
DMG_TMP_DIR="dmg_temp"
rm -rf "$DMG_TMP_DIR"
mkdir -p "$DMG_TMP_DIR"

# 复制app到临时目录
cp -r "dist/ZhipuAudio.app" "$DMG_TMP_DIR/"

# 创建Applications快捷方式
ln -s /Applications "$DMG_TMP_DIR/Applications"

# 计算所需大小（当前目录大小 + 200MB）
SIZE=$(du -sm "$DMG_TMP_DIR" | awk '{print $1}')
SIZE=$((SIZE + 200))

echo "📦 创建DMG镜像..."
TEMP_DMG="dist/ZhipuAudio.dmg.tmp"
hdiutil create -srcfolder "$DMG_TMP_DIR" -volname "ZhipuAudio" -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" -format UDRW -size "${SIZE}m" "$TEMP_DMG"

# 检查临时DMG是否创建成功（hdiutil会自动添加.dmg扩展名）
ACTUAL_TEMP_DMG="$TEMP_DMG.dmg"
if [ ! -f "$ACTUAL_TEMP_DMG" ]; then
    # 也检查不带扩展名的情况
    if [ ! -f "$TEMP_DMG" ]; then
        echo "❌ 错误：创建临时DMG失败"
        rm -rf "$DMG_TMP_DIR"
        exit 1
    fi
    ACTUAL_TEMP_DMG="$TEMP_DMG"
fi

# 挂载临时DMG
MOUNT_POINT="/Volumes/ZhipuAudio"
hdiutil attach "$ACTUAL_TEMP_DMG" -mountpoint "$MOUNT_POINT"

# 设置DMG背景（可选）
# echo "🎨 设置DMG背景..."

# 卸载DMG
hdiutil detach "$MOUNT_POINT"

# 转换为压缩格式
echo "🔄 压缩DMG镜像..."
hdiutil convert "$ACTUAL_TEMP_DMG" -format UDZO -o "dist/ZhipuAudio.dmg"

# 删除临时文件
rm -f "$ACTUAL_TEMP_DMG"
rm -rf "$DMG_TMP_DIR"

# 检查DMG是否创建成功
if [ -f "dist/ZhipuAudio.dmg" ]; then
    echo "✅ DMG打包完成！"
    echo "=============================================="
    echo "📂 输出文件: dist/ZhipuAudio.dmg"
    echo "💾 文件大小: $(du -sh dist/ZhipuAudio.dmg | awk '{print $1}')"
    echo "=============================================="
else
    echo "❌ DMG打包失败"
    exit 1
fi

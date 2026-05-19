@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==============================================
echo 🎤 智谱AI语音克隆 - Windows打包脚本
echo ==============================================

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未找到Python，请先安装Python 3.7+
    echo 下载地址：https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

:: 检查PyInstaller是否安装
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 安装PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ❌ 安装PyInstaller失败
        pause
        exit /b 1
    )
)

:: 停止可能正在运行的服务
echo ⚡ 停止端口7860占用...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7860"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 创建输出目录
mkdir dist 2>nul
mkdir build 2>nul

echo 🚀 开始打包...
pyinstaller zhipu_audio.spec --clean

if %errorlevel% equ 0 (
    echo ✅ 打包完成！
    echo 📂 输出目录: dist\ZhipuAudio
    echo 📄 可执行文件: dist\ZhipuAudio\ZhipuAudio.exe
    echo.
    echo 🎉 双击 ZhipuAudio.exe 即可运行
) else (
    echo ❌ 打包失败，请检查错误信息
    pause
    exit /b 1
)

:: 复制必要文件到输出目录
echo 📋 复制资源文件...
copy voices.db dist\ZhipuAudio\voices.db /Y >nul

echo ==============================================
echo 📦 打包完成！
echo ==============================================
echo 输出位置: dist\ZhipuAudio
echo 运行方式: 双击 ZhipuAudio.exe
pause

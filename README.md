# AI 语音克隆与生成教育智能体 - 本地服务

基于智谱AI开放平台API的本地语音克隆与生成Web应用，支持文生文、语音克隆、语音合成三大功能。

## 📋 功能特性

- **文生文**: AI智能生成配音文本（需API Key）或手动输入
- **语音克隆**: 上传音频创建专属音色（需API Key）
- **语音合成**: 使用智谱TTS或系统语音合成音频
- **双模式**: 有API Key启用高级功能，无API Key提供本地替代方案
- **音色管理**: SQLite数据库存储音色，支持搜索、备注、排序、分页
- **异步处理**: 后台任务处理，不阻塞用户界面
- **跨平台**: 支持Windows、Mac、Linux及Docker部署

## 🚀 快速开始

### 1. 环境要求

- Python 3.7+
- pip包管理器

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
# Windows
run.bat

# Mac/Linux
chmod +x run.sh
./run.sh

# 或直接运行
python3 app.py
```

### 4. 访问应用

打开浏览器访问: http://localhost:7860

## 📦 项目结构

```
├── app.py                 # 主应用程序
├── requirements.txt       # Python依赖
├── voices.db             # SQLite音色数据库
├── zhipu_audio.spec      # PyInstaller打包配置
├── Dockerfile           # Docker镜像配置
├── docker-compose.yml    # Docker Compose配置
├── run.sh               # Mac/Linux启动脚本
├── run.bat              # Windows启动脚本
├── build_mac.sh         # Mac打包脚本
├── build_dmg.sh         # DMG打包脚本
├── build_windows.bat    # Windows打包脚本
├── docker-run.sh        # Docker一键部署脚本
└── README.md           # 项目说明文档
```

## ⚙️ 配置说明

### API Key配置（可选）

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/) 注册账号
2. 获取API Key
3. 在应用界面右上角点击"API Key: 未配置"按钮
4. 输入您的API Key并确认

> **注意**: 不配置API Key也可以使用基础功能（手动输入文本+系统语音合成）

### 端口配置

默认端口为 **7860**，如需修改请编辑 `app.py` 中的 `port` 变量。

## 📖 使用流程

### 步骤1：文生文

- **AI生成模式**: 输入生成指令，让AI自动生成文本内容
- **手动输入模式**: 直接输入或粘贴要合成的文本

### 步骤2：语音克隆

- 上传10-60秒的参考音频（支持wav、mp3、m4a、ogg、flac格式）
- 输入音频对应的文本内容
- 点击"开始克隆"创建自定义音色

> 此功能需要配置智谱API Key

### 步骤3：语音合成

- 选择音色（预设音色或自定义音色）
- 点击"生成音频"合成语音
- 播放预览或下载音频文件

## 🎵 预设音色

项目内置了3个示例音色：

| ID | 名称 | 说明 |
|----|------|------|
| klm | 康老师 | 预设音色1 |
| mld | 马老师 | 预设音色2 |
| zhaoxue | 赵雪 | 预设音色3 |

> 注意: 预设音色需要通过语音克隆功能实际创建后才能使用

## 🔧 打包部署

### Windows打包

1. 安装Python 3.7+
2. 运行 `build_windows.bat`
3. 打包完成后在 `dist/` 目录找到 `ZhipuAudio.exe`

### Mac打包

1. 运行 `./build_mac.sh`
2. 运行 `./build_dmg.sh` 生成DMG安装包
3. 打包完成后在 `dist/` 目录找到相关文件

### Docker部署

```bash
# 一键部署
./docker-run.sh

# 或手动部署
docker-compose up -d
```

## 📝 技术栈

- **Python 3.7+** - 核心开发语言
- **Flask** - Web框架
- **SQLite** - 音色数据管理
- **PyInstaller** - 跨平台打包
- **Docker** - 容器化部署

## ⚠️ 注意事项

1. 音频文件大小限制: 50MB
2. 语音克隆建议音频时长: 10-60秒
3. 端口7860占用时会自动尝试清理
4. 打包后的程序首次运行可能需要额外权限

## 📄 许可证

MIT License

## 🤝 技术支持

如遇问题请提交Issue或联系技术支持。

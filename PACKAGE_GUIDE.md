# 🎤 智谱AI语音克隆 - 打包与部署指南

## 项目概述

本项目是一个基于智谱AI开放平台的语音克隆与生成教育智能体，支持文生文、语音克隆和语音合成三大核心功能。

### 技术栈
- **Python 3.7+** - 核心开发语言
- **Flask** - Web框架
- **智谱AI API** - 文生文、语音克隆、TTS服务
- **SQLite** - 音色数据库
- **PyInstaller** - 打包工具

### 功能特性
- ✅ 文生文 → 语音克隆 → 语音合成 三步工作流
- ✅ 中英双语支持
- ✅ 双模式运行（有API Key/无Key本地免费）
- ✅ SQLite音色管理（搜索、备注、排序、分页）
- ✅ 异步任务处理（避免页面阻塞）
- ✅ Docker容器化部署

---

## 一、打包前准备

### 1.1 环境要求
| 平台 | 要求 |
|------|------|
| Windows | Windows 10/11 + Python 3.7+ |
| Mac | macOS 10.15+ + Python 3.7+ |

### 1.2 安装依赖

```bash
# 安装基础依赖
pip install flask requests

# 安装打包工具
pip install pyinstaller
```

### 1.3 项目文件清单

确保以下文件存在于项目根目录：

```
zhipu-tts-clone/
├── app.py              # 主应用程序
├── voices.db           # SQLite数据库（首次运行自动创建）
├── zhipu_audio.spec    # PyInstaller配置文件
├── build_windows.bat   # Windows打包脚本
├── build_mac.sh        # Mac打包脚本
├── build_dmg.sh        # Mac DMG打包脚本
├── docker-run.sh       # Docker一键部署脚本
├── Dockerfile          # Docker镜像配置
├── docker-compose.yml  # Docker Compose配置
└── requirements.txt    # 依赖清单
```

---

## 二、Windows打包（生成EXE）

### 2.1 自动打包（推荐）

**方法一：双击运行脚本**
1. 双击 `build_windows.bat`
2. 等待打包完成
3. 输出文件位于 `dist/ZhipuAudio/` 目录

**方法二：手动执行命令**

```batch
@echo off
chcp 65001

:: 停止端口占用
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7860"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 执行打包
pyinstaller zhipu_audio.spec --clean

:: 复制数据库文件
copy voices.db dist\ZhipuAudio\voices.db /Y
```

### 2.2 打包输出

```
dist/ZhipuAudio/
├── ZhipuAudio.exe      # 主程序（双击运行）
├── voices.db          # 音色数据库
└── outputs/           # 音频输出目录（自动创建）
```

### 2.3 运行方式

1. **双击运行**：直接双击 `ZhipuAudio.exe`
2. **命令行运行**：
   ```batch
   ZhipuAudio.exe
   ```

运行后会：
- 自动清理端口7860
- 启动Flask服务
- 自动打开浏览器访问 http://localhost:7860

---

## 三、Mac打包（生成.app和.dmg）

### 3.1 生成.app文件

**方法一：使用脚本**
```bash
./build_mac.sh
```

**方法二：手动执行**
```bash
# 停止端口占用
lsof -ti:7860 | xargs kill -9 2>/dev/null

# 执行打包
python3 -m PyInstaller zhipu_audio.spec --clean

# 复制数据库文件
cp voices.db dist/ZhipuAudio.app/Contents/MacOS/voices.db
```

### 3.2 生成DMG安装包

```bash
./build_dmg.sh
```

### 3.3 打包输出

```
dist/
├── ZhipuAudio.app      # 应用程序包
└── ZhipuAudio.dmg      # DMG安装镜像（可选）
```

### 3.4 运行方式

1. **双击运行**：直接双击 `ZhipuAudio.app`
2. **命令行运行**：
   ```bash
   open dist/ZhipuAudio.app
   ```

> **注意**：首次运行可能需要在"系统设置" → "隐私与安全性"中允许运行。

---

## 四、Docker部署

### 4.1 一键部署

```bash
./docker-run.sh
```

### 4.2 手动部署

```bash
# 构建镜像
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4.3 访问地址

- **Web界面**：http://localhost:7860
- **数据持久化**：
  - `./outputs` - 音频输出目录
  - `./voices.db` - 音色数据库

---

## 五、配置说明

### 5.1 API Key配置

运行后在Web界面右上角点击"API Key: 未配置"按钮，输入智谱API Key即可启用高级功能。

### 5.2 端口配置

默认端口为 **7860**，如需修改请编辑 `app.py`：

```python
if __name__ == '__main__':
    port = 7860  # 修改此值
    app.run(host='0.0.0.0', port=port, debug=False)
```

### 5.3 预设音色

系统预置了3个示例音色ID：
- `klm` - 康老师（示例音色）
- `mld` - 马老师（示例音色）
- `zhaoxue` - 赵雪（示例音色）

> **注意**：这些是示例ID，实际使用时需要通过语音克隆功能创建自己的音色。

---

## 六、常见问题

### Q1: 打包失败，提示缺少模块？

**解决方案**：
```bash
pip install pyinstaller flask requests
```

### Q2: Windows提示"Windows保护你的电脑"？

**解决方案**：
1. 点击"更多信息"
2. 点击"仍然运行"
3. 或在Windows Defender中添加信任

### Q3: Mac提示"无法打开，因为Apple无法检查其是否包含恶意软件"？

**解决方案**：
1. 打开"系统设置" → "隐私与安全性"
2. 在"安全性"部分找到提示信息
3. 点击"允许打开"

### Q4: 端口7860被占用？

**解决方案**：

**Windows**：
```batch
netstat -ano | findstr ":7860"
taskkill /F /PID <进程ID>
```

**Mac/Linux**：
```bash
lsof -ti:7860 | xargs kill -9
```

### Q5: 运行后浏览器无法访问？

**解决方案**：
1. 检查控制台是否有错误信息
2. 确保端口7860未被占用
3. 尝试手动打开 http://localhost:7860

---

## 七、目录结构

```
ZhipuAudio/                              # Windows/Mac运行目录
├── ZhipuAudio.exe / ZhipuAudio.app     # 主程序
├── voices.db                           # SQLite数据库
├── outputs/                            # 音频输出目录
│   ├── tts_*.wav                       # TTS生成的音频
│   └── clone_*.wav                     # 克隆生成的音频
└── logs/                               # 日志目录（自动创建）
```

---

## 八、技术细节

### 8.1 PyInstaller配置

`zhipu_audio.spec` 配置要点：

| 参数 | 说明 |
|------|------|
| `console=True` | 保留控制台输出，方便排查问题 |
| `upx=True` | 使用UPX压缩可执行文件 |
| `datas` | 包含voices.db数据库文件 |
| `hiddenimports` | 显式声明依赖模块 |

### 8.2 动态路径适配

```python
def resource_path(relative_path):
    try:
        # PyInstaller打包后使用sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # 开发模式使用当前目录
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
```

### 8.3 自动启动浏览器

```python
import webbrowser
import threading

def open_browser():
    time.sleep(2)  # 等待服务启动
    webbrowser.open(f'http://localhost:{port}')

threading.Thread(target=open_browser, daemon=True).start()
```

---

## 九、部署交付物清单

| 交付物 | 说明 | 位置 |
|--------|------|------|
| ZhipuAudio.exe | Windows可执行文件 | `dist/ZhipuAudio/` |
| ZhipuAudio.app | Mac应用程序 | `dist/` |
| ZhipuAudio.dmg | Mac安装镜像 | `dist/` |
| docker-run.sh | Docker一键部署脚本 | 项目根目录 |
| PACKAGE_GUIDE.md | 打包部署说明书 | 项目根目录 |

---

## 十、许可证

本项目仅供学习和教育使用。使用前请确保已获得智谱AI API的使用授权。

---

**最后更新**：2026年5月  
**版本**：v1.0.0

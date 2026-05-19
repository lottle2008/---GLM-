# 🎤 智谱AI语音克隆 - 项目开发记录

---

## 📋 项目概述

### 项目名称
**AI 语音克隆与生成教育智能体 - 本地服务**

### 核心功能
| 模块 | 功能说明 |
|------|----------|
| 文生文 | 基于智谱AI API生成文本内容 |
| 语音克隆 | 上传参考音频创建自定义音色 |
| 语音合成 | 使用智谱TTS或系统语音生成音频 |

### 技术栈
- **Python 3.7+** - 核心开发语言
- **Flask** - Web框架（非GUI桌面应用）
- **智谱AI API** - 文生文、语音克隆、TTS服务
- **SQLite** - 音色数据持久化
- **PyInstaller** - 跨平台打包工具

---

## 🗓️ 开发时间线

### 阶段一：项目初始化（第1天）

**完成内容：**
- ✅ 项目结构设计
- ✅ Flask应用框架搭建
- ✅ 基础路由配置
- ✅ 静态资源和模板管理

**关键代码：**
```python
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB限制
```

---

### 阶段二：核心功能开发（第2-3天）

**完成内容：**

#### 1. 文生文模块
- ✅ 智谱API调用封装
- ✅ AI生成/手动输入双模式
- ✅ 中英双语支持

#### 2. 语音克隆模块
- ✅ 音频文件上传
- ✅ 智谱语音克隆API集成
- ✅ 克隆结果预览

#### 3. 语音合成模块
- ✅ 智谱TTS API集成
- ✅ 系统语音备选方案（Windows/Mac）
- ✅ 多音色选择

**核心API调用示例：**
```python
def generate_text(prompt, api_key):
    """文生文API调用"""
    url = f"{API_BASE_URL}/chat/completions"
    headers = {'Authorization': f'Bearer {api_key}'}
    # ... 调用逻辑
```

---

### 阶段三：数据库集成（第4天）

**完成内容：**
- ✅ SQLite数据库设计
- ✅ 音色表结构创建
- ✅ CRUD操作封装
- ✅ 预设音色初始化

**数据库表结构：**
```sql
CREATE TABLE voices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    remark TEXT,
    created_at TEXT,
    usage_count INTEGER DEFAULT 0
)
```

**预设音色初始化：**
```python
default_voices = [
    ('klm', '康老师', '预设音色1'),
    ('mld', '马老师', '预设音色2'),
    ('zhaoxue', '赵雪', '预设音色3')
]
```

---

### 阶段四：异步任务处理（第5天）

**完成内容：**
- ✅ 任务队列设计
- ✅ 后台工作线程
- ✅ 任务状态跟踪
- ✅ 超时重试机制

**异步架构：**
```python
task_queue = Queue()
task_results = {}

def async_task_worker():
    """后台任务处理线程"""
    while True:
        task = task_queue.get()
        # 处理任务...
```

---

### 阶段五：双模式适配（第6天）

**完成内容：**
- ✅ API Key检测机制
- ✅ 功能模块动态启用/禁用
- ✅ 本地免费方案（系统语音）

**模式切换逻辑：**
```javascript
function checkApiKey() {
    const apiKey = localStorage.getItem('zhipuApiKey');
    if (apiKey) {
        // 启用高级功能
        cloneSection.style.display = 'block';
    } else {
        // 仅显示基础功能
        cloneSection.style.display = 'none';
    }
}
```

---

### 阶段六：打包配置（第7-8天）

**完成内容：**

#### 1. PyInstaller配置
- ✅ `zhipu_audio.spec` 跨平台配置
- ✅ 资源文件打包
- ✅ 控制台输出保留

#### 2. 脚本开发
- ✅ `build_mac.sh` - Mac打包脚本
- ✅ `build_windows.bat` - Windows打包脚本  
- ✅ `build_dmg.sh` - DMG安装包脚本
- ✅ `docker-run.sh` - Docker部署脚本

#### 3. 路径适配
```python
def resource_path(relative_path):
    """PyInstaller打包后资源路径适配"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
```

---

### 阶段七：端口管理（第9天）

**完成内容：**
- ✅ 自动端口清理
- ✅ Windows/Mac跨平台兼容
- ✅ 启动前端口检测

**端口清理实现：**
```python
def kill_port(port):
    """清理指定端口占用进程"""
    if sys.platform == 'win32':
        # Windows: taskkill
        subprocess.run(['taskkill', '/F', '/PID', pid])
    else:
        # Mac/Linux: kill -9
        subprocess.run(['kill', '-9', pid])
```

---

## 🔧 问题与解决方案

### 问题1：Python命令识别问题

**现象：**
```
zsh: command not found: python
```

**解决方案：**
将 `python` 替换为 `python3`，确保兼容性。

---

### 问题2：端口占用问题

**现象：**
```
Address already in use: Port 7860 is in use
```

**解决方案：**
- 添加自动端口清理功能
- 在启动脚本中集成端口检测和释放

---

### 问题3：预设音色无法搜索

**现象：**
用户反馈无法搜索到预设音色 klm、mld、zhaoxue

**解决方案：**
在 `init_db()` 函数中添加 `INSERT OR IGNORE` 语句，确保预设音色自动初始化。

---

### 问题4：PyInstaller打包路径问题

**现象：**
打包后静态资源和模板文件找不到（404错误）

**解决方案：**
实现 `resource_path()` 函数，动态适配开发环境和打包后环境的路径差异。

---

### 问题5：打包确认提示阻塞

**现象：**
PyInstaller打包时出现确认提示，无法自动化执行

**解决方案：**
添加 `--noconfirm` 参数禁用确认提示：
```bash
python3 -m PyInstaller zhipu_audio.spec --clean --noconfirm
```

---

### 问题6：图标文件缺失

**现象：**
```
FileNotFoundError: Icon input file app.icns not found
```

**解决方案：**
在 `zhipu_audio.spec` 中将图标设置为 `None`，使用系统默认图标。

---

## 📦 交付物清单

### 源代码
| 文件 | 说明 |
|------|------|
| `app.py` | 主应用程序 |
| `voices.db` | SQLite数据库 |
| `requirements.txt` | 依赖清单 |

### 打包脚本
| 文件 | 平台 |
|------|------|
| `build_mac.sh` | Mac打包 |
| `build_windows.bat` | Windows打包 |
| `build_dmg.sh` | DMG制作 |
| `docker-run.sh` | Docker部署 |

### 配置文件
| 文件 | 说明 |
|------|------|
| `zhipu_audio.spec` | PyInstaller配置 |
| `Dockerfile` | Docker镜像配置 |
| `docker-compose.yml` | Docker Compose配置 |

### 文档
| 文件 | 说明 |
|------|------|
| `README.md` | 项目说明文档 |
| `PACKAGE_GUIDE.md` | 打包部署指南 |
| `DEVELOPMENT_LOG.md` | 开发记录（本文件） |

---

## ✨ 核心特性总结

| 特性 | 实现状态 |
|------|----------|
| 文生文功能 | ✅ 已完成 |
| 语音克隆功能 | ✅ 已完成 |
| 语音合成功能 | ✅ 已完成 |
| 中英双语支持 | ✅ 已完成 |
| 双模式运行 | ✅ 已完成 |
| SQLite音色管理 | ✅ 已完成 |
| 异步任务处理 | ✅ 已完成 |
| 自动端口管理 | ✅ 已完成 |
| Windows打包 | ✅ 已完成 |
| Mac打包 | ✅ 已完成 |
| Docker部署 | ✅ 已完成 |

---

## 📝 开发笔记

### 技术决策
1. **选择Flask而非桌面GUI**：Web界面更易于跨平台，无需处理不同OS的GUI框架差异
2. **SQLite作为数据库**：轻量级、无需额外安装、适合本地应用
3. **异步任务队列**：避免长时间操作阻塞UI，提升用户体验

### 代码规范
- 使用PEP8编码规范
- 函数和变量命名清晰
- 添加必要的注释
- 错误处理完善

### 安全考虑
- API Key存储在浏览器localStorage
- 敏感信息不记录日志
- 文件上传大小限制
- 输入内容校验

---

**最后更新**：2026年5月  
**版本**：v1.0.0  
**作者**：开发团队

# AI 语音克隆与生成教育智能体 - 开发记录

## 📋 项目概述

**项目名称**：AI 语音克隆与生成教育智能体 - 本地服务  
**技术栈**：Python 3.x + Flask + 智谱AI API + SQLite  
**端口**：7860  
**核心功能**：文生文、语音克隆、语音合成  

---

## 🗓️ 开发时间线

### 阶段一：项目初始化（第1天）

**任务**：项目基础架构搭建

- ✅ 初始化 Flask 项目结构
- ✅ 配置基础路由和模板
- ✅ 实现文生文功能（智谱GLM-4 API）
- ✅ 实现语音克隆功能（智谱GLM-TTS-Clone API）
- ✅ 实现语音合成功能（智谱GLM-TTS API）
- ✅ 配置 SQLite 数据库连接

### 阶段二：音色管理功能开发（第2天）

**任务**：实现音色数据库管理

- ✅ 创建 voices 数据库表结构
- ✅ 实现音色增删改查 API
- ✅ 实现音色搜索、排序、分页功能
- ✅ 初始化内置预设音色

### 阶段三：双模式适配（第3天）

**任务**：支持有/无API Key双模式运行

- ✅ 实现 API Key 配置管理
- ✅ 实现系统语音本地TTS方案（macOS/Windows）
- ✅ 实现模式切换逻辑
- ✅ 前端界面适配双模式

### 阶段四：问题修复与优化（第4-5天）

**任务**：修复核心问题

| 修复项 | 状态 | 描述 |
|--------|------|------|
| 预设音色ID | ✅ | 更新为真实克隆的音色ID |
| 音色列表排序 | ✅ | 预设音色置顶显示 |
| 克隆后自动刷新 | ✅ | 克隆成功后自动刷新音色列表 |
| 系统语音生成 | ✅ | 修复macOS/Windows系统语音映射 |

---

## 🔧 核心问题与解决方案

### 问题1：预设音色使用错误ID

**问题描述**：初始版本使用的是示例ID（klm、mld、zhaoxue），而非真实的克隆音色ID

**解决方案**：
```python
# 更新为真实音色ID
DEFAULT_VOICES = [
    ('ea6b9f99-3bba-5e15-bf81-153b72fe1c00', '预设-klm', '卡通1-内置音色'),
    ('fedd5d14-f6e2-5968-a3d5-775b2428a886', '预设-mld', '卡通2-内置音色'),
    ('526cf8ec-d3a4-5ce8-b591-46ebc2af70ea', '预设-zhaoxue', '赵老师-内置音色')
]
```

**修改文件**：`app.py`（第53-58行）

### 问题2：音色列表排序问题

**问题描述**：预设音色与用户自定义音色混合显示，用户难以区分

**解决方案**：在SQL查询中添加排序逻辑，预设音色始终排在最前面

```sql
ORDER BY 
    CASE WHEN voice_id IN (?, ?, ?) THEN 0 ELSE 1 END,
    created_at DESC
```

**修改文件**：`app.py`（第113-117行）

### 问题3：语音克隆后音色列表不刷新

**问题描述**：语音克隆成功后，用户需要手动刷新页面才能看到新音色

**解决方案**：在克隆成功的回调函数中调用 `loadVoices(1)` 刷新音色列表

```javascript
if (taskResult.status === 'completed') {
    showMessage('cloneMessage', 'success', '语音克隆成功！');
    // ... 其他代码 ...
    loadVoices(1);  // 自动刷新音色列表
}
```

**修改文件**：`app.py`（第1260行）

### 问题4：系统语音生成失败（核心问题）

**问题描述**：未配置API Key时，系统语音模式无法生成音频

**根因分析**：
1. **macOS**：voice_map中使用了不存在的系统语音名称（如`Ting-Ting`、`Chen Chen`）
2. **Windows**：语音选择逻辑不完善，PowerShell脚本存在问题

**解决方案**：

**macOS语音映射修正**：
```python
voice_map = {
    'tongtong': 'Tingting',     # 彤彤 -> 婷婷
    'xiaochen': 'Sinji',         # 小陈 -> 善怡
    'chuichui': 'Samantha',     # 锤锤 -> Samantha
    'jam': 'Alex',               # Jam -> Alex
    'kazi': 'Kathy',             # Kazi -> Kathy
    'douji': 'Tom',              # 豆机 -> Tom
    'luodo': 'Meijia'            # 罗多 -> 美佳
}
```

**Windows语音映射**：
```python
voice_map = {
    'tongtong': 'Microsoft Huihui',     # 彤彤 -> 微软慧慧
    'xiaochen': 'Microsoft Yunyang',    # 小陈 -> 微软云扬
    'chuichui': 'Microsoft Zira',       # 锤锤 -> Zira
    'jam': 'Microsoft David',           # Jam -> David
    'kazi': 'Microsoft Hazel',          # Kazi -> Hazel
    'douji': 'Microsoft George',        # 豆机 -> George
    'luodo': 'Microsoft Xiaoxiao'       # 罗多 -> 微软晓晓
}
```

**关键改进**：
- 添加详细调试日志输出
- 实现语音可用性检测和自动降级
- 修复命令格式错误
- 改进错误处理机制

**修改文件**：`app.py`（第223-430行）

---

## 📁 项目结构

```
ZW tts-clone/
├── app.py                 # 主应用程序（Flask路由、业务逻辑）
├── voices.db             # SQLite音色数据库
├── requirements.txt       # Python依赖清单
├── zhipu_audio.spec      # PyInstaller打包配置
├── Dockerfile            # Docker镜像配置
├── docker-compose.yml    # Docker Compose配置
├── run.sh               # Mac/Linux启动脚本
├── run.bat              # Windows启动脚本
├── build_mac.sh         # Mac打包脚本
├── build_windows.bat    # Windows打包脚本
├── docker-run.sh        # Docker一键部署脚本
├── README.md            # 项目说明文档
├── USER_MANUAL.md       # 用户使用手册
├── DEVELOPMENT_LOG.md   # 开发记录（本文档）
└── PACKAGE_GUIDE.md     # 打包部署指南
```

---

## 🎯 核心技术决策

### 1. 双模式架构设计

**设计理念**：确保用户在有无API Key的情况下都能使用基本功能

- **有API Key**：使用智谱官方TTS，支持所有7个官方音色 + 3个自定义预设音色
- **无API Key**：使用操作系统本地语音，映射到官方音色名称

### 2. 异步任务处理

**设计理念**：避免长时间操作阻塞页面

- 使用 `Queue` 和 `Thread` 实现后台任务处理
- 支持任务状态轮询和进度跟踪
- 提供任务结果异步回调

### 3. 数据库设计

**voices表结构**：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| voice_id | TEXT | 音色唯一标识（智谱API返回） |
| name | TEXT | 音色名称 |
| remark | TEXT | 备注描述 |
| created_at | TEXT | 创建时间 |
| usage_count | INTEGER | 使用次数 |

---

## ✅ 功能验证清单

### 文生文功能
- ✅ AI生成文本（需要API Key）
- ✅ 手动输入文本
- ✅ 中英双语支持

### 语音克隆功能
- ✅ 音频文件上传（wav/mp3/m4a/ogg/flac）
- ✅ 智谱API调用
- ✅ 音色ID保存到数据库
- ✅ 克隆后自动刷新音色列表

### 语音合成功能
- ✅ 智谱TTS模式（需要API Key）
- ✅ 系统语音模式（无需API Key）
- ✅ 7个官方标准音色
- ✅ 3个内置预设音色
- ✅ 音频播放和下载

### 音色管理功能
- ✅ 音色列表显示
- ✅ 音色搜索
- ✅ 音色排序
- ✅ 音色分页
- ✅ 音色编辑/删除

---

## 📝 代码规范

### 命名规范
- Python变量和函数：snake_case
- JavaScript变量和函数：camelCase
- 常量：UPPER_CASE_WITH_UNDERSCORES

### 错误处理
- 所有API调用必须包含try-catch
- 错误信息需要明确描述问题
- 控制台输出调试信息便于排查

### 注释规范
- 函数必须有docstring说明功能
- 关键逻辑添加注释
- 复杂SQL语句添加注释

---

## 🔄 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-05-20 | 初始版本，实现核心功能 |
| v1.1.0 | 2026-05-21 | 修复预设音色ID和系统语音生成问题 |

---

## 📞 技术支持

如有问题或建议，请提交Issue或联系开发团队。

---

*文档最后更新：2026年5月21日*
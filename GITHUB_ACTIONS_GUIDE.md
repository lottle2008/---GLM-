# GitHub Actions 自动打包使用指南

## 📋 概述

本项目已配置 GitHub Actions 自动打包，支持：
- ✅ 自动测试（多平台、多Python版本）
- ✅ 自动构建（macOS、Windows、Linux）
- ✅ 自动发布（创建GitHub Release）

---

## 🚀 快速开始

### 1. 推送代码触发构建

```bash
# 提交代码
git add .
git commit -m "更新代码"
git push origin main
```

推送后，GitHub Actions 会自动：
1. 运行测试（Ubuntu、macOS、Windows × Python 3.9/3.10）
2. 构建三个平台的可执行文件
3. 上传构建产物（保留7天）

### 2. 发布新版本

```bash
# 创建版本标签
git tag v1.1.0

# 推送标签触发发布
git push origin v1.1.0
```

推送标签后，GitHub Actions 会自动：
1. 构建三个平台的可执行文件
2. 打包成压缩文件
3. 创建 GitHub Release
4. 上传发布文件

---

## 📁 配置文件说明

### `.github/workflows/build.yml`

**触发条件**：
- 推送到 `main` 或 `master` 分支
- Pull Request 到 `main` 或 `master` 分支

**执行任务**：
| 任务 | 平台 | 说明 |
|------|------|------|
| test | Ubuntu/macOS/Windows | 运行测试（Python 3.9/3.10） |
| build-mac | macOS | 构建 macOS 应用 |
| build-windows | Windows | 构建 Windows 可执行文件 |
| build-linux | Ubuntu | 构建 Linux 可执行文件 |

**产物下载**：
- 构建完成后，在 GitHub Actions 页面下载产物
- 产物保留 7 天

### `.github/workflows/release.yml`

**触发条件**：
- 推送 `v*` 格式的标签（如 v1.0.0、v1.1.0）

**执行任务**：
| 任务 | 平台 | 说明 |
|------|------|------|
| build-mac | macOS | 构建 macOS 应用并打包 |
| build-windows | Windows | 构建 Windows 可执行文件并打包 |
| build-linux | Ubuntu | 构建 Linux 可执行文件并打包 |
| create-release | Ubuntu | 创建 GitHub Release |

**发布文件**：
- `ZhipuAudio-macOS.zip` - macOS 应用
- `ZhipuAudio-Windows.zip` - Windows 可执行文件
- `ZhipuAudio-Linux.tar.gz` - Linux 可执行文件

---

## 🔧 使用步骤

### 步骤一：查看构建状态

1. 访问 GitHub 仓库
2. 点击 **Actions** 标签
3. 查看正在运行的构建任务

### 步骤二：下载构建产物

#### 方法一：从 Actions 页面下载

1. 在 Actions 页面点击具体的运行记录
2. 滚动到 **Artifacts** 部分
3. 下载对应的产物：
   - `macos-app` - macOS 应用
   - `windows-exe` - Windows 可执行文件
   - `linux-binary` - Linux 可执行文件

#### 方法二：从 Releases 页面下载

1. 点击 **Releases** 标签
2. 找到对应版本
3. 下载对应平台的压缩包

### 步骤三：本地测试

#### macOS

```bash
# 解压
unzip ZhipuAudio-macOS.zip

# 运行
./ZhipuAudio.app/Contents/MacOS/ZhipuAudio

# 或双击 ZhipuAudio.app
```

#### Windows

```batch
:: 解压
解压 ZhipuAudio-Windows.zip

:: 运行
ZhipuAudio.exe
```

#### Linux

```bash
# 解压
tar -xzf ZhipuAudio-Linux.tar.gz

# 赋予执行权限
chmod +x ZhipuAudio

# 运行
./ZhipuAudio
```

---

## 📝 版本发布流程

### 1. 更新版本号

更新以下文件中的版本号：
- `CHANGELOG.md`
- `USER_MANUAL.md`
- `README.md`（如有）

### 2. 提交更改

```bash
git add .
git commit -m "准备发布 v1.1.0"
git push origin main
```

### 3. 创建标签

```bash
# 创建带注释的标签
git tag -a v1.1.0 -m "Release v1.1.0"

# 推送标签
git push origin v1.1.0
```

### 4. 等待自动发布

GitHub Actions 会自动：
1. 构建所有平台版本
2. 创建 GitHub Release
3. 上传发布文件

### 5. 编辑 Release 说明

1. 访问 Releases 页面
2. 点击编辑按钮
3. 补充详细的更新说明
4. 保存

---

## ⚙️ 高级配置

### 自定义构建参数

编辑 `.github/workflows/build.yml`：

```yaml
# 修改 Python 版本
python-version: ['3.8', '3.9', '3.10', '3.11']

# 修改构建平台
os: [macos-latest, windows-latest, ubuntu-latest]

# 修改产物保留时间
retention-days: 30
```

### 添加构建前脚本

在 `build-mac` 任务中添加：

```yaml
- name: Pre-build script
  run: |
    # 执行自定义脚本
    python scripts/pre_build.py
```

### 添加构建后测试

在 `build-windows` 任务中添加：

```yaml
- name: Test built executable
  run: |
    ./dist/ZhipuAudio.exe --test
```

---

## 🔍 监控和调试

### 查看构建日志

1. 在 Actions 页面点击具体运行记录
2. 展开各个步骤查看详细日志
3. 如有错误，查看错误信息

### 重新运行失败的任务

1. 点击失败的任务
2. 点击 **Re-run all jobs** 按钮

### 调试构建问题

1. 添加调试步骤：

```yaml
- name: Debug
  run: |
    echo "Current directory: $(pwd)"
    echo "Files: $(ls -la)"
    python --version
    pip list
```

2. 查看输出定位问题

---

## 📊 性能优化

### 减少构建时间

1. **使用缓存**：

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

2. **并行构建**：
   - 默认配置已启用并行构建
   - 三个平台同时构建

3. **减少测试矩阵**：
   - 只测试关键平台和Python版本

---

## 🛡️ 安全注意事项

### 保护敏感信息

- ❌ 不要在代码中硬编码 API Key
- ✅ 使用 GitHub Secrets 存储敏感信息
- ✅ 在 workflow 中使用 `${{ secrets.SECRET_NAME }}`

### 添加 Secrets

1. 进入仓库 Settings
2. 点击 Secrets and variables → Actions
3. 点击 New repository secret
4. 添加名称和值

---

## 📞 常见问题

### Q: 构建失败怎么办？

1. 查看 Actions 日志定位错误
2. 检查 requirements.txt 是否完整
3. 确认 spec 文件配置正确
4. 本地测试打包命令是否成功

### Q: 如何跳过构建？

在提交信息中添加 `[skip ci]`：

```bash
git commit -m "更新文档 [skip ci]"
```

### Q: 如何只构建特定平台？

修改 workflow 文件，注释掉不需要的任务。

### Q: 构建产物在哪里？

- **构建产物**：Actions 页面 → 具体运行 → Artifacts
- **发布文件**：Releases 页面 → 对应版本

---

## 🎯 最佳实践

1. **频繁推送**：小步快跑，及时发现问题
2. **版本管理**：使用语义化版本号
3. **更新日志**：每次发布都更新 CHANGELOG.md
4. **测试先行**：确保本地测试通过后再推送
5. **文档同步**：及时更新用户手册和文档

---

## 📚 相关文档

- [GitHub Actions 官方文档](https://docs.github.com/zh/actions)
- [PyInstaller 文档](https://pyinstaller.org/en/stable/)
- [语义化版本](https://semver.org/lang/zh-CN/)
- [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)

---

*最后更新：2026年5月21日*

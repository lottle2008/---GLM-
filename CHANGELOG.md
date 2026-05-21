# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.1.0] - 2026-05-21

### 新增
- ✨ 添加 GitHub Actions 自动打包配置
- ✨ 支持跨平台自动构建（macOS、Windows、Linux）
- ✨ 添加版本发布自动化流程

### 修复
- 🐛 修复系统语音生成问题（macOS/Windows）
- 🐛 修正语音映射关系，对齐智谱官方7个标准音色
- 🐛 修复预设音色ID错误
- 🐛 修复音色列表排序问题
- 🐛 修复语音克隆后音色列表不刷新问题

### 优化
- 💄 添加详细错误日志和调试信息
- 💄 实现语音可用性检测和自动降级
- 💄 改进错误处理机制

### 文档
- 📝 添加开发记录文档（DEVELOPMENT_LOG.md）
- 📝 添加完整项目代码文档（PROJECT_CODE.md）
- 📝 添加用户手册（USER_MANUAL.md）
- 📝 添加打包部署指南（PACKAGE_GUIDE.md）

## [1.0.0] - 2026-05-20

### 新增
- ✨ 实现文生文功能（智谱GLM-4 API）
- ✨ 实现语音克隆功能（智谱GLM-TTS-Clone API）
- ✨ 实现语音合成功能（智谱GLM-TTS API）
- ✨ 支持双模式运行（有/无API Key）
- ✨ 实现系统语音本地TTS方案（macOS/Windows）
- ✨ 创建音色数据库管理功能
- ✅ 初始化内置预设音色（3个）
- ✅ 支持7个官方标准音色
- ✅ 实现音色搜索、排序、分页功能
- ✅ 添加 Docker 部署支持
- ✅ 添加启动脚本（Mac/Windows）

---

## 版本说明

- **主版本号（Major）**：不兼容的API更改
- **次版本号（Minor）**：向下兼容的功能性新增
- **修订号（Patch）**：向下兼容的问题修正

[1.1.0]: https://github.com/lottle2008/---GLM-/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/lottle2008/---GLM-/releases/tag/v1.0.0

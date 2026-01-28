# 🌊 Ripple - API Impact Analyzer

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 一个轻量级的 CLI 工具，用于分析 OpenAPI (Swagger) 变更对代码库的影响。
> 
> 帮助开发者在修改 API 前了解 **"谁在使用这个接口"** 🔍

---

## ✨ 功能特性

- 📄 **OpenAPI 解析** - 自动解析 OpenAPI 3.0 YAML 规范文件
- 🗂️ **多语言扫描** - 支持 `.js`, `.ts`, `.py`, `.go`, `.java`, `.php` 等常见语言
- 🔢 **引用计数** - 精确统计每个 API 在代码库中的引用次数
- 🚫 **智能过滤** - 自动跳过 `node_modules`, `.git`, `venv` 等干扰目录
- 🎨 **友好输出** - 清晰的终端报告，一目了然

---

## 📦 安装

### 环境要求
- Python 3.7 或更高版本

### 安装依赖
```bash
pip install pyyaml
```

---

## 🚀 快速开始

### 1. 准备你的 OpenAPI 规范文件

```yaml
# api.yaml
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
paths:
  /users/login:
    post:
      summary: User Login
  /products/{id}:
    get:
      summary: Get Product Details
```

### 2. 运行分析

```bash
python main.py --spec fixtures/api.yaml --dir ./src
```

### 3. 查看结果

```
🔍 Ripple API 影响分析工具
==================================================

📄 加载 API 规范: /path/to/api.yaml
   发现 3 个 API 端点

📁 扫描代码目录: /path/to/src
   支持的文件类型: .go, .java, .js, .php, .py, .ts
   跳过的目录: .git, .idea, .vscode, __pycache__, bin, build, dist, env, node_modules, obj, target, third_party, venv, vendor
   找到 42 个代码文件

🔎 正在分析 API 引用情况...

📊 分析结果:
--------------------------------------------------
✅ [引用中] /users/login (引用次数: 5)
✅ [引用中] /products/{id} (引用次数: 3)
⚠️ [未引用] /old/legacy-endpoint
--------------------------------------------------

📈 汇总统计:
   - 已引用：2 个
   - 未引用：1 个
   - 总计：3 个 API
   - 扫描文件：42 个
```

---

## 📖 使用说明

### 命令行参数

```
python main.py --spec <openapi.yaml> --dir <code_directory>
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--spec` | ✅ | OpenAPI YAML 文件路径 |
| `--dir` | ✅ | 要扫描的代码根目录 |

### 示例

```bash
# 分析当前项目的 API 影响
python main.py --spec ./openapi.yaml --dir ./src

# 分析其他项目的代码
python main.py --spec ./api.yaml --dir ../another-project
```

---

## 🛠️ 工作原理

1. **解析 API 规范** - 从 OpenAPI YAML 中提取所有 `paths` 定义
2. **递归扫描代码** - 遍历指定目录下的所有支持的代码文件
3. **智能匹配** - 
   - 静态路径（如 `/users/login`）直接匹配
   - 动态路径（如 `/products/{id}`）智能转换为 `/products/` 进行前缀匹配
4. **统计报告** - 汇总每个 API 的引用次数并生成报告

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License © 2026 Ripple Contributors

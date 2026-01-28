# 🌊 Ripple - API Impact Analyzer

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.0-orange.svg)]()

[English](#-english) | [中文文档](#-中文文档)

---

<a name="-english"></a>
## 🌏 English

**Ripple** is a lightweight, high-performance CLI tool designed to analyze the impact of OpenAPI (Swagger) changes on your codebase.

Before modifying or deleting an API endpoint, Ripple helps you answer: **"Who is using this API, and where?"** 🔍

### ✨ Features

*   **🚀 High Performance**: Multi-threaded concurrent scanning, lightning fast for large codebases.
*   **📊 Visualization**: Generates interactive **HTML reports** with dependency graphs (powered by ECharts).
*   **🎯 Precise Tracking**: Pinpoints exact **file paths and line numbers**, with code previews.
*   **🧠 Smart Analysis**: Intelligent matching that filters out comments (`//`, `#`, `/*... */`).
*   **⚙️ Configurable**: Support `ripple.json` for custom rules and extensions.
*   **🤖 CI/CD Ready**: Supports JSON output and `--fail-on-unused` mode for automated pipelines.
*   **🌍 Multi-Language**: Supports `.js`, `.ts`, `.py`, `.go`, `.java`, `.php` and more.
*   **🌐 I18n Support**: HTML reports support one-click switching between **Chinese and English** interfaces.

### 📦 Installation

Requires Python 3.7+.

```bash
pip install pyyaml
```

### 🚀 Quick Start

#### 1. Prepare OpenAPI Spec
Ensure you have an [api.yaml](fixtures/api.yaml) file (OpenAPI 3.0+).

#### 2. Run Analysis

```bash
python main.py --spec fixtures/api.yaml --dir ./src
```

#### 3. Check Report
Open the generated `report.html` in your browser to see the visualization.

### ⚙️ Configuration (ripple.json)

You can create a `ripple.json` in your project root to avoid typing arguments every time:

```json
{
  "extensions": [".js", ".ts", ".py", ".go", ".java"],
  "skip_dirs": ["node_modules", "dist", ".git", "venv"],
  "max_workers": 8
}
```

### 🛠 Advanced Usage

#### Generate JSON for Tools

```bash
python main.py --spec api.yaml --dir ./src --output-json result.json
```

#### CI/CD Pipeline Mode

Block the build if unused APIs are found:

```bash
python main.py --spec api.yaml --dir ./src --fail-on-unused
# Returns Exit Code 1 if unused APIs exist
```

---

<a name="-中文文档"></a>
## 🇨🇳 中文文档

**Ripple** 是一个轻量级、高性能的 API 影响分析工具。它可以根据 OpenAPI (Swagger) 规范，自动扫描代码库，分析 API 的引用情况。

它能帮助开发者在修改 API 之前了解 "哪些代码在使用这个接口"，从而避免线上故障。🔍

### ✨ 核心特性

*   **🚀 极速扫描**: 内置多线程并发处理，支持毫秒级分析大型项目。
*   **📊 可视化报告**: 自动生成交互式 HTML 依赖图谱 (基于 ECharts)，直观展示 API 与文件的关系。
*   **🎯 精准定位**: 不仅统计次数，还能定位到具体的 **文件路径、行号** 并提供 **代码预览**。
*   **🧠 智能过滤**: 自动识别并忽略代码中的注释行 (`//`, `#`, `/*... */`)，避免误报。
*   **⚙️ 灵活配置**: 支持 `ripple.json` 配置文件，自定义扫描规则和忽略目录。
*   **🤖 CI/CD 集成**: 支持输出 JSON 格式供机器读取，提供 `--fail-on-unused` 参数用于流水线阻断。
*   **🌍 多语言支持**: 原生支持 `.js`, `.ts`, `.py`, `.go`, `.java`, `.php` 等常见语言。
*   **🌐 双语界面**: HTML 报告支持一键切换 **中英文** 界面，方便国际化团队使用。

### 📦 安装与使用

需要 Python 3.7 或更高版本。

```bash
# 1. 安装依赖
pip install pyyaml

# 2. 运行分析
python main.py --spec fixtures/api.yaml --dir ./src
```

### 🚀 进阶功能

#### 1. 可视化报告
运行命令后，默认会在当前目录生成 `report.html`。双击打开即可查看依赖关系图。

#### 2. 使用配置文件
在项目根目录新建 `ripple.json`，即可省去繁琐的命令行参数：

```json
{
  "extensions": [".js", ".ts", ".py", ".vue"],
  "skip_dirs": ["node_modules", "dist", "vendor"],
  "max_workers": 4
}
```

#### 3. 集成到 CI/CD 流水线
在 Jenkins 或 GitHub Actions 中使用。如果发现有"僵尸 API"（未被引用），脚本将返回错误码，阻止代码合并。

```bash
python main.py --spec api.yaml --dir ./src --fail-on-unused
```

#### 4. 机器可读输出 (JSON)
将分析结果导出为 JSON，方便对接其他系统（如钉钉通知、自定义看板）。

```bash
python main.py --spec api.yaml --dir ./src --output-json output.json
```

### 📝 许可证

MIT License © 2026 Ripple Contributors
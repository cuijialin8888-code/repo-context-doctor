# Repo Context Doctor

[![CI](https://github.com/cuijialin8888-code/repo-context-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/cuijialin8888-code/repo-context-doctor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/cuijialin8888-code/repo-context-doctor)](https://github.com/cuijialin8888-code/repo-context-doctor/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**一个只读、本地运行的编码代理上下文与仓库验证路径证据清单工具。**

Repo Context Doctor 帮你回答：编码代理进入仓库后，实际上能看到哪些指令，能发现哪些测试、lint、格式化、类型检查和构建命令，这些结论又来自哪里、可信度如何。

它具有以下边界：

- 确定性静态检测，不使用 LLM；
- 运行时零第三方依赖；
- 不调用 API、不联网、不上传报告、无遥测；
- 不执行目标仓库里的任何命令；
- 默认只读，仅在显式使用 `--output` 时写入指定报告文件；
- 输出 Console、JSON 或 Markdown。

[English README](README.md)

## 快速开始

需要 Python 3.11 或更高版本。可从带标签的 GitHub 版本安装：

```bash
python -m pip install "repo-context-doctor @ git+https://github.com/cuijialin8888-code/repo-context-doctor.git@v0.1.0"
repo-context-doctor .
```

也可以从源码安装：

```bash
git clone https://github.com/cuijialin8888-code/repo-context-doctor.git
cd repo-context-doctor
python -m venv .venv
python -m pip install ".[dev]"
repo-context-doctor .
```

安装过程可能需要网络；实际扫描是本地、离线的。

## 用法

```text
repo-context-doctor [PATH] [--json | --markdown] [--output FILE] [--no-score]
```

```bash
# 终端摘要
repo-context-doctor .

# JSON
repo-context-doctor . --json

# 明确写出 Markdown 报告
repo-context-doctor . --markdown --output context-report.md

# 不显示启发式分数
repo-context-doctor . --no-score
```

扫描完成返回 `0`，即使报告中存在缺口；参数错误返回 `2`；意外的致命扫描错误返回 `3`。发现项和分数都不是 CI 质量门。

## 检查什么

工具会清点常见代理指令表面及其作用域，包括：

- 根目录和嵌套目录中的 `AGENTS.md`、`AGENTS.override.md`；
- `CLAUDE.md`、`.claude/CLAUDE.md`、`CLAUDE.local.md`、`.claude/rules/*.md`；
- `GEMINI.md`；
- `.github/copilot-instructions.md` 和 `.github/instructions/*.instructions.md`；
- `.cursor/rules/*.mdc` 和旧版 `.cursorrules`。

Python、Node.js、Rust、Go、PowerShell 提供较深的验证路径检测；混合仓库还会获得通用 manifest、锁文件、CI 和目录结构信号。每条命令都会标出 `MANIFEST`、`INSTRUCTION`、`DOCUMENTATION`、`CI`、`MAKEFILE` 或 `INFERRED` 来源以及可信度，但绝不会被执行。

准确范围请查看[支持的信号](docs/supported-signals.md)与[报告格式](docs/report-format.md)。

## 安全与隐私

- 不跟随符号链接；
- 排除 VCS、依赖、构建、缓存和常见敏感目录；
- 跳过常见密钥文件，并对疑似凭证值进行纵深脱敏；
- 报告仅使用仓库相对路径；
- 超大、无法解码或无法访问的元数据会标为 `UNKNOWN`，不会假装不存在；
- 默认限制深度 10、条目 20,000、单个文本文件 256 KiB。

这些措施不是完整的密钥扫描器或沙箱。若目标仓库敏感，在公开报告前仍应人工复核。

## 启发式分数

可选分数由五类有上限的证据组成：代理上下文 30%、验证可发现性 30%、自动化 15%、依赖可复现性 15%、仓库导向 10%。显式命令得分高于推断命令，重复指令文件不会无限叠加。

该分数**不是**代码质量、代理成功率、安全性或可维护性基准。完整公式见[评分说明](docs/scoring.md)，不需要分数时使用 `--no-score`。

## 不做什么

本工具不会生成、修复或重写代理指令，不会初始化配置，不会运行测试、构建、包管理器、容器或钩子，不会克隆远程仓库，不会上传数据，也不会用 AI 评价指令质量。

## 已知限制

- 检测有意保持保守，自定义包装器可能无法识别；
- 各厂商指令规则可能随时间变化；
- 为保持运行时零依赖，YAML、Markdown 和部分 manifest 仅做浅层解析；
- 扫描完成不代表所有文件都可读，请检查 `UNKNOWN` 和扫描限制元数据。

## 贡献与支持

开发命令和检测器契约见 [CONTRIBUTING.md](CONTRIBUTING.md) 与[添加检测器](docs/adding-a-detector.md)。问题请提交至 [GitHub Issues](https://github.com/cuijialin8888-code/repo-context-doctor/issues)，安全问题按 [SECURITY.md](SECURITY.md) 私下报告。

Repo Context Doctor 是独立开源项目，与 OpenAI、Anthropic、Google、GitHub、Cursor 或其他编码代理厂商不存在隶属或背书关系。

## 许可证

[MIT](LICENSE)

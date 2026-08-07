# 🚀 Bomiot — 面向仓储行业的节点化全栈开发平台

[English](README_EN.md) | [中文](README.md)

![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9%20%E2%80%94%203.13-yellowgreen)

简要：Bomiot 是专注仓储与供应链的节点化全栈开发平台，支持把应用打包为单文件可执行程序（零依赖）、对所有 Python 代码进行编译/加密处理、并兼容三大主流前端框架以便快速构建行业插件与解决方案。

---

## 核心优势（突出卖点）

- 单文件节点，零依赖部署：Nuitka 将运行时、依赖、代码与资源打包为单个可执行文件，双击即可运行。
- 全语言栈自由：后端自由选择 Django / FastAPI / Flask；前端完全兼容 Vue（Quasar）、React 与 Angular 三大主流框架，现成模板与抽象层支持无缝接入。
- 所有 Python 代码可编译与加密：支持将项目整体或指定模块通过 Nuitka 编译为二进制（.exe/.so/.pyd），关键安全路径可使用 PyO3（Rust）实现以进一步提高逆向难度，从而实现源码保护与商业化分发。
- 插件化与变现：内置插件市场与热插拔机制，支持开发者上架与收益分成（最高可达 70%）。
- 数据主权与本地优先：节点本地存储，适合对数据合规与隐私有严格要求的企业。
- 轻量多场景：既可做单机/局域网离线节点，也可通过授权网关实现多节点云/跨站协同。

---

## 快速上手（最短路径）

1. 安装
```bash
pip install bomiot
# 或
poetry add bomiot
```

2. 初始化与创建
```bash
bomiot init
bomiot project my-warehouse
bomiot new inbound --framework django   # 或 fastapi / flask
```

3. 数据库与管理员
```bash
bomiot migrate
bomiot initadmin
```

4. 运行开发节点
```bash
bomiot run --host 0.0.0.0 --port 8000
# 访问 http://127.0.0.1:8000/
```

5. 打包为单文件（可加密）
```bash
bomiot package my-project
# 输出在 dist/，核心模块可被编译为二进制以保护源码
```

---

## 前端兼容性（明确说明）

- 推荐：Quasar + Vue 3（内置模板、快速集成）
- 兼容：React（Create React App / Vite）与 Angular（CLI / Vite），平台提供前端抽象层与适配说明，插件与 UI 模块可用任一框架开发并热插入节点。

---

## Python 代码保护与加密策略（关键说明）

- 项目级编译：使用 Nuitka 将 Python 应用编译为本地二进制，生成单文件可执行程序，从而避免裸露源码与依赖树。
- 关键路径加固：对认证、授权、支付、许可证验证等敏感模块，推荐使用 PyO3（Rust）实现并编译为扩展模块，进一步提高逆向成本。
- 可选流程（CI/发布）：在 CI 中执行编译、二进制签名与版本化；将加密二进制与插件打包后上架市场进行分发与销售。

注意：术语“加密”在此指通过本地化编译/打包提高源码保护与逆向难度。实际安全性与不可逆性取决于构建策略、混淆强度与补充的安全措施（如授权验证、反篡改等）。

---

## 主要特性（简要）

- 节点化部署：单文件、零依赖、跨平台（Windows / macOS / Linux）
- 多后端支持：Django / FastAPI / Flask
- 三大前端兼容：Vue / React / Angular
- 全局/模块级 Python 编译与加固支持（Nuitka + PyO3）
- 插件市场与收益分成（支持加密分发）
- 本地优先的数据策略与 LAN 协同
- 内置任务调度（APScheduler）与系统监控选项

---

## 常用命令（速览）

- bomiot init
- bomiot project <name>
- bomiot new <app> --framework {django|fastapi|flask}
- bomiot migrate / makemigrations
- bomiot initadmin / initpwd
- bomiot run [--host --port --workers --log-level ...]
- bomiot package <project>

---

## 打包与发布建议

- 将编译/打包步骤放入 CI：构建、签名、版本化与上传 Artifacts。
- 对关键模块使用 Rust(PyO3)进行二次实现（若安全要求极高）。
- 为插件提供加密发布流程与在线授权验证，防止未经授权分发。

---

## 插件生态

- 为开发者提供脚手架、上架流程、收益统计与加密发布能力。
- 企业可按需购买插件并在线/离线部署，支持自动化安装与权限校验。

---

## 贡献与支持

欢迎贡献与反馈：
- Bug 报告 / 功能请求 / 讨论请到仓库 Issues / Discussions 页面。

---

## 许可证

Apache License 2.0 — 详见 LICENSE 文件。

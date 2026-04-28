# AGENTS.md

> 你是这个项目的开发者。在标记任务完成之前，先问自己：这个实现值得为它骄傲吗？

## 项目概述

基于 Playwright 的 Google 搜索负面新闻取证工具。工具默认启动有头 Chrome，并复用独立 profile 中的登录状态，按模板搜索目标实体的负面信息，保存 PDF、HTML、截图和 JSON 元数据。

**技术栈**：Python 3.10+ / Playwright / Click CLI / PyYAML

## 常用命令

```bash
# 开发环境
python3 --version                # 必须 >= 3.10
pip install -e ".[dev]"          # 安装依赖
playwright install chromium      # 仅 browser.channel=chromium 时需要

# Lint & Test
ruff check .
ruff check --fix .
pytest
pytest tests/test_searcher.py

# 首次登录与执行搜索
google-search login
google-search profile-status
google-search search "三鹿集团" company
python -m google_search "张三" person --template '"{name}" AND (诈骗 OR 起诉)'
```

## 关键路径

```text
src/google_search/
├── __main__.py     # python -m google_search 入口
├── cli.py          # Click CLI 接口
├── config.py       # YAML 配置加载
├── browser.py      # 持久化 Chrome profile 生命周期
├── searcher.py     # 搜索流程编排
├── pdf.py          # CDP PDF、HTML、截图保存
├── parser.py       # Google 结果 best-effort 解析
├── models.py       # dataclass 模型
└── templates.py    # 搜索 URL 构造

config.yaml          # 运行时配置与搜索模板
output/              # PDF + HTML + PNG + JSON 输出（不提交 git）
docs/                # 详细文档
tests/               # pytest 测试
```

## 必知约定

- **PDF 生成**：使用 CDP `Page.printToPDF`，因为 headed Chrome 不支持 Playwright `page.pdf()`
- **动态加载**：`networkidle` 使用毫秒超时值，配置单位是秒，传给 Playwright 前必须乘以 1000
- **搜索策略**：多模板分次执行，不用 `OR` 拼接成单条超长查询
- **反爬边界**：不内置代理池、UA 池、stealth 或验证码绕过；遇到验证码时 headed 模式等待用户手动处理
- **配置文件**：`config.yaml` 管理 profile、browser、search、templates、output

## 常见坑

- **IMPORTANT**: 安装前必须检查 Python 版本 >= 3.10，运行 `python3 --version` 确认
- 如果系统 `python3` 是 3.9，请使用 `.venv/bin/python` 或创建 3.10+ 虚拟环境
- PDF 文件命名格式：`实体名_template_id_YYYYMMDDTHHMMSSZ.pdf`
- output/ 目录不提交到 git，已在 .gitignore 中
- `python -m google_search "名称" company` 是兼容短格式，真实 CLI 子命令是 `search`

## 错误自省规则

每次会话中遇到任何错误（代码错误、依赖问题、调试异常），必须：

1. **分析错误根因**：找出直接原因和深层原因
2. **更新 `docs/errors.md`**：
   ```markdown
   ## [错误摘要] — YYYY-MM-DD

   **错误信息**：`Error: ...`

   **根因**：
   - 原因1

   **解决方案**：
   - 方案1

   **预防规则**（写入 AGENTS.md）：
   - 规则描述
   ```
3. **更新本文件 `错误预防规则` 章节**：追加新规则防止重蹈覆辙

## 错误预防规则

> 此章节由每次错误后自动追加，禁止手动删除

- **安装前必须检查 Python 版本**，必须 >= 3.10
- **运行 Git 命令前必须先确认当前目录是 Git 工作区**，避免在源码快照目录误判状态
- **跑测试或 lint 前必须确认使用 Python 3.10+ 且已执行 editable 开发安装**，否则 pytest/ruff/Playwright 依赖可能不可用
- **src 布局项目若未安装，临时测试必须显式设置 `PYTHONPATH=src`**，避免 `ModuleNotFoundError: google_search`
- **新初始化仓库后必须验证 `.git/` 可写**，再继续执行 `remote/add/commit/push`
- **本机默认 `python3` 低于 3.10 时，测试和开发命令必须显式使用 `.venv/bin/python` 或等价 3.10+ 解释器**
- **修改 CLI 用法、README 示例或集成测试时，必须同步验证三者一致**
- **Playwright timeout 参数使用毫秒，配置秒数传入前必须乘以 1000，禁止再除以 1000**
- **清理缓存/生成物时只针对项目文件路径，禁止递归触碰 `.git/` 内部文件**
- **测试中启动当前项目的子进程必须使用 `sys.executable`，不要硬编码 `python` 或 `python3`**
- **真实访问 Google/Chrome 的集成测试必须默认跳过，用显式环境变量开启**
- **写入 JSON 的元数据必须先规范化为可序列化基础类型，尤其是来自 mock 或第三方对象的字段**

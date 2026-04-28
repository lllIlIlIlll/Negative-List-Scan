# 错误日志

> 本文件记录所有遇到的问题、根因分析、解决方案和预防规则。
> 由 Claude Code 会话在每次遇到错误后自动追加。

---

<!-- 错误记录追加格式：
## [错误摘要] — YYYY-MM-DD

**错误信息**：`Error: ...`

**根因**：
- 原因1
- 原因2

**解决方案**：
- 方案1
- 方案2

**预防规则**（已写入 CLAUDE.md）：
- 规则描述
---
-->

---

## [Python 版本不满足 — 2026-04-09

**错误信息**：`ERROR: Package 'google-search' requires a different Python: 3.9.6 not in '>=3.10'`

**根因**：
- 系统默认 Python 为 3.9.6，不满足项目 `requires-python = ">=3.10"` 要求
- macOS CommandLineTools 自带 Python 版本较旧

**解决方案**：
- 使用 Python 3.10+ 的虚拟环境（`python3.10 -m venv .venv`）
- 或使用 [pyenv](https://github.com/pyenv/pyenv) 管理多版本 Python：`pyenv install 3.10 && pyenv local 3.10`
- 或使用 [uv](https://github.com/astral-sh/uv)：`uv venv --python 3.10 && source .venv/bin/activate`

---

## [Playwright Sync API 与 asyncio loop 冲突 — 2026-04-09

**错误信息**：`It looks like you are using Playwright Sync API inside the asyncio loop.`

**根因**：
- macOS 上存在全局活跃的 asyncio 事件循环（由 pytest 或其他库创建）
- Playwright Sync API 内部创建自己的 loop，与已有 loop 冲突

**解决方案**：
- 在 `browser.py` 的 `_ensure_browser()` 中用 `asyncio.new_event_loop()` 创建隔离 loop
- 修复已应用到 `src/google_search/browser.py`

**预防规则**（已写入 CLAUDE.md）：
- Playwright Sync API 在 macOS 上必须使用隔离事件循环

**预防规则**（已写入 CLAUDE.md）：
- 安装前先检查 Python 版本：`python3 --version`，必须 >= 3.10
- README.md 中已说明 `requires-python = ">=3.10"`

---

---

## [Playwright async API 迁移 — 2026-04-09

**错误信息**：`RuntimeWarning: coroutine 'Page.goto' was never awaited` + `'coroutine' object has no attribute 'lower'`

**根因**：
- `browser.py` 改用 async Playwright API 后，返回的 Page/Context 是 async 对象
- `searcher.py` 中调用 `page.goto()`、`page.content()`、`page.title()`、`page.context.close()` 时未包装 `_run_async`
- `_is_blocked_page()` 中 `page.content().lower()` 的 `.lower()` 报错是因为 `content()` 返回 coroutine

**解决方案**：
- `searcher.py` 中所有 Playwright async 方法调用必须用 `mgr._run_async()` 包装
- 修复已应用到 `src/google_search/searcher.py`

**预防规则**（已写入 CLAUDE.md）：
- browser.py 返回的 Page/Context 对象只允许通过 `_run_async` 调用其方法



每次会话中遇到错误时：
1. 分析错误根因
2. 以上方格式追加到本文件
3. 将"预防规则"追加到 `CLAUDE.md` 的 `错误预防规则` 章节
4. 后续会话开始时读取本文件，避免重复犯错

---

*本文件由 Claude Code 自动维护，请勿手动删除任何记录。*

---

## [本地工作区不是 Git 仓库 — 2026-04-28]

**错误信息**：`fatal: not a git repository (or any of the parent directories): .git`

**根因**：
- 当前目录 `/Users/x403/google-search` 没有 `.git` 元数据，不能执行依赖 Git 仓库上下文的命令。
- 项目分析阶段默认尝试 `git status`，但未先确认当前目录是否已初始化或是否只是源码快照。

**解决方案**：
- 在运行 Git 命令前先检查 `.git` 是否存在，或使用 `git rev-parse --is-inside-work-tree` 做探测。
- 如果需要版本管理能力，应先确认项目来源，必要时重新 clone 或执行 `git init`。

**预防规则**（写入 AGENTS.md）：
- 运行 Git 命令前必须先确认当前目录是 Git 工作区。

---

## [Python 3.10 开发环境未完整初始化 — 2026-04-28]

**错误信息**：`Python 3.9.6` / `No module named ruff` / `ModuleNotFoundError: No module named 'google_search'` / `ModuleNotFoundError: No module named 'playwright'`

**根因**：
- 系统默认 `python3` 是 3.9.6，不满足项目 `requires-python = ">=3.10"`。
- 可用的 `/opt/homebrew/bin/python3.10` 未安装项目 editable 包和完整开发依赖。
- 未安装项目时，pytest 不知道 `src/` 布局下的 `google_search` 包；即使用 `PYTHONPATH=src`，仍缺少 Playwright 和 ruff。

**解决方案**：
- 使用 Python 3.10+ 创建并激活虚拟环境。
- 执行 `pip install -e ".[dev]"` 安装项目和开发依赖。
- 执行 `playwright install chromium` 安装浏览器运行时。

**预防规则**（写入 AGENTS.md）：
- 跑测试或 lint 前必须确认使用 Python 3.10+ 且已执行 editable 开发安装。
- `src/` 布局项目若未安装，临时测试必须显式设置 `PYTHONPATH=src`。

---

## [Sandbox 阻止写入 Git 元数据 — 2026-04-28]

**错误信息**：`error: could not lock config file .git/config: Operation not permitted` / `touch: .git/codex_write_probe: Operation not permitted`

**根因**：
- 当前执行环境允许创建 `.git/`，但阻止后续写入 `.git/config`、`.git/index` 等 Git 元数据文件。
- `git remote add`、`git add`、`git commit` 都依赖写入 `.git/`，因此无法在未获额外授权的 sandbox 内完成本地提交和推送。

**解决方案**：
- 对需要写入 `.git/` 的 Git 命令申请提升权限。
- 如果提升权限不可用，改用 GitHub 连接器提交少量变更，或请用户在本机终端执行 Git/gh 登录和推送命令。

**预防规则**（写入 AGENTS.md）：
- 新初始化仓库后必须验证 `.git/` 可写，再继续执行 `remote/add/commit/push`。

# AGENTS.md

> 你是这个项目的开发者。在标记任务完成之前，先问自己：这个实现值得为它骄傲吗？

## 项目概述

基于 Playwright 无头浏览器的 Google 搜索负面新闻排查工具。通过 Chromium 自动访问 Google，搜索目标实体的负面新闻并保存 PDF。

**技术栈**：Python 3.10+ / Playwright / Click CLI / PyYAML

## 常用命令

```bash
# 开发环境
pip install -e .[dev]          # 安装依赖
playwright install chromium       # 安装浏览器
/build                           # 自定义命令

# Lint & Test
ruff check .                     # 检查
ruff check --fix .               # 自动修复
pytest                           # 所有测试
/test tests/test_searcher.py     # 单文件测试

# 执行搜索
python -m google_search "三鹿集团" company
python -m google_search "张三" person --template '"{name}" AND (诈骗 OR 起诉)'
/run "三鹿集团" company
```

## 关键路径

```
src/google_search/
├── __main__.py     # python -m google_search 入口
├── cli.py          # Click CLI 接口
├── config.py       # YAML 配置加载
├── browser.py      # Playwright 浏览器生命周期
├── searcher.py     # 搜索流程编排
├── pdf.py          # PDF 生成
├── ua_pool.py      # User-Agent 池
├── proxy.py        # 代理池
└── templates.py    # 搜索模板

config.yaml          # 运行时配置
templates/default.yaml  # 预定义模板
output/              # PDF + JSON 输出（不提交 git）
docs/                # 详细文档
tests/               # pytest 测试
```

## 必知约定

- **PDF 生成**：使用 `page.pdf()` 全页面截图，保持 Google 页面原始布局
- **动态加载**：使用 `networkidle` 等待页面完全渲染后再生成 PDF
- **重试策略**：失败时自动切换代理 IP + 随机 UA，最多重试 2 次
- **配置文件**：`config.yaml` 管理代理池、UA 池、搜索模板

## 常见坑

- **IMPORTANT**: 安装前必须检查 Python 版本 >= 3.10，运行 `python3 --version` 确认
- PDF 文件命名格式：`实体名_YYYYMMDD_HHMMSS.pdf`
- output/ 目录不提交到 git，已在 .gitignore 中

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

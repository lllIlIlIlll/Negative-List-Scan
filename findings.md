# Findings & Decisions

## Requirements

From the project's CLAUDE.md and documentation:
- Google 负面新闻排查工具
- Based on Playwright headless browser
- PDF + JSON output
- Retry logic with proxy/UA rotation
- Config via config.yaml

## Research Findings

### Google 反爬问题
- Google 对自动化浏览器（Playwright）有严格检测
- 无代理模式下直接请求返回 403/sorry 页面
- 选择器 `div.g` 在 403 页面上不存在
- 所有现有运行都返回 `total_results: 0`

### PDF 生成验证
- PDF 生成本身是正常工作的（`/tmp/test_pdf.pdf` 34049 bytes）
- 问题是页面内容是 403 拦截页，不是 Google 搜索结果

### 代码质量
- 26/26 测试通过
- ruff lint 无错误
- `browser.py` async cleanup 问题已修复（`stop()` 现已 await）

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 使用 async Playwright API | sync API 在 macOS 上与 asyncio loop 冲突 |
| `networkidle` 等待策略 | 三段式等待：networkidle → 2s延迟 → domcontentloaded兜底 |
| 重试最多2次 | 配置通过 `MAX_RETRIES = 2` |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Python 3.9 不满足 `>=3.10` | 使用 .venv 中的 Python 3.10.17 |
| Playwright Sync API 与 asyncio loop 冲突 | 改用 async API + 隔离事件循环 |
| `stop()` 未 await 导致 RuntimeWarning | 修复：用 `_run_async(self._playwright.stop())` |
| ruff import block unsorted | `ruff check --fix .` 自动修复 |

## Resources

- 项目根目录：`/Users/x403/workspace/google-search`
- 源码：`src/google_search/`
- 测试：`tests/`
- 输出：`output/` (PDF + JSON)
- 文档：`docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_PLAN.md`

## Visual/Browser Findings

- Google 403/sorry 页面 URL 包含 `/sorry/index`
- 403 页面标题很短（少于5字符），可作为拦截检测特征
- `div.g` 选择器在正常 Google 搜索结果中存在，但在拦截页不存在

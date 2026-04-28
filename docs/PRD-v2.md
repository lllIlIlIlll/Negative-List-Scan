# 产品需求文档（PRD v2）

**文档版本**：v2.0
**日期**：2026-04-28
**状态**：定位修正 / 重新设计
**关联文档**：`PRD.md`（v1，已废弃）/ `ARCHITECTURE.md`（待按本文档同步）

---

## 0. v2 修订说明

v1 把产品定位为"基于无头浏览器的 Google 搜索爬虫"，导致 PRD 中堆砌了代理池、UA 池、反爬规避等大量与实际需求无关的复杂度。

**v2 重新定位**：本产品是**面向单用户的浏览器自动化取证工具**，而非数据采集系统。它的目标是把"打开 Chrome → 输入查询 → 另存为 PDF"这套人工流程自动化，输出可作为合规/尽调证据的 PDF 文件。

v2 与 v1 的核心差异：

| 维度 | v1（爬虫） | v2（浏览器自动化） |
|------|-----------|------------------|
| 浏览器模式 | headless | **headed 默认 + headless 可选** |
| 浏览器身份 | 全新匿名 context | **持久化 profile，复用用户 Chrome 状态** |
| 网络出口 | 内置代理池轮换 | **复用用户系统级网络配置（用户的 VPN/代理）** |
| 反爬措施 | UA/IP 轮换、webdriver 隐藏 | **无（用真实浏览器即可）** |
| 失败重试 | 切换代理 + 切换 UA | **简单重试 + 必要时用户手动介入** |
| 核心交付 | 结构化 JSON 数据 | **PDF 文件 + 取证元数据** |
| 调用频率假设 | 高频批量 | 低频、人工节奏 |

---

## 1. 产品概述

### 1.1 产品名称

Google 负面新闻取证工具

### 1.2 产品定位

基于 Playwright 的 Google 搜索取证工具。系统自动启动一个绑定独立 profile 的 Chrome 浏览器，按预设模板执行负面关键词搜索，将搜索结果页完整保存为 PDF 作为排查证据。

**关键属性**：

- **取证工具**而非数据采集工具：核心产物是可验证的 PDF，结构化 JSON 是附属物
- **单用户单机**：不为高并发批量采集设计，按人工节奏运行
- **使用真实浏览器**：复用用户已登录的 Google 账号、cookies、网络配置（含 VPN）
- **可视化默认**：默认有头模式，用户可观察执行过程，必要时手动介入

### 1.3 不做的事

为了保持定位清晰，本产品**明确不做**以下事情：

- 不绕过 Google 反爬机制（不内置代理池、不做指纹伪装、不做 stealth）
- 不为中国大陆免梯子用户提供网络通路（这是用户自身的网络环境问题）
- 不做高频批量爬取（v0.1 单实体；v0.2 批量也仍按人工节奏顺序执行）
- 不替代 SerpAPI / Bright Data SERP 等专业 SERP 服务

---

## 2. 用户故事

### 2.1 目标用户

- 企业风控/合规岗：合作方背景排查
- 尽调/投资人员：投资/并购前负面信息核查
- 律师/调查员：案件背景取证
- 个人尽调：对潜在合作伙伴/雇员的核查

### 2.2 典型场景

**故事 1：单次取证**

> 作为风控人员，我需要对潜在合作伙伴"XX 集团"做一次负面排查。
> 我运行 `google-search search "XX 集团" company`，工具自动打开 Chrome 执行搜索，
> 我可以在屏幕上看到搜索过程，工具自动保存 PDF 到 `output/` 目录。
> 整个过程约 60 秒（含两个默认模板 + 模板间随机停顿），比手动操作快约 5 倍。

**故事 2：首次配置 + 跨会话复用**

> 我第一次使用工具时，它弹出 Chrome 提示我登录 Google。
> 登录一次后，工具关闭浏览器但保留了 profile。
> 此后所有运行都自动复用这个登录状态，不需要重复处理 cookie banner / reCAPTCHA。

**故事 3：触发验证码后的人工介入**

> 工具运行中 Google 弹出 reCAPTCHA。
> 因为是有头模式，我直接在浏览器里手动通过验证码。
> 工具检测到验证完成，继续后续流程并正常输出 PDF。

**故事 4：批量排查（v0.2）**

> 我有一份 50 家供应商的清单（CSV）。
> 运行 `google-search batch suppliers.csv`，工具按 10–30 秒间隔依次搜索，
> 每个公司生成一份 PDF + JSON。下班启动，第二天上午得到完整排查包。

---

## 3. 功能需求

### 3.1 功能范围

| 功能 | v0.1 | v0.2 | v0.3+ |
|------|------|------|-------|
| 单实体搜索 + PDF 输出 | ✅ | - | - |
| 持久化 Chrome profile | ✅ | - | - |
| 有头 / 无头模式切换 | ✅ | - | - |
| 多模板分次执行（非 OR 拼接） | ✅ | - | - |
| 自定义模板参数 | ✅ | - | - |
| HTML 快照 + 全页面截图（兜底证据） | ✅ | - | - |
| PDF SHA-256 + UTC 时间戳 | ✅ | - | - |
| 结构化结果 JSON（best-effort） | ✅ | - | - |
| 用户登录引导 + 状态检查 | ✅ | - | - |
| CSV 批量输入 | - | ✅ | - |
| 失败补搜（断点续做） | - | ✅ | - |
| SQLite 持久化 + 跨次去重 | - | - | ✅ |
| 详情页抓取（点击进入原文） | - | - | ✅ |
| LLM 负面性判断与摘要 | - | - | ✅ |
| SerpAPI 作为兜底数据源 | - | - | ✅ |

### 3.2 FR-1：搜索执行

**输入**：

- `entity`：实体名称（必填）
- `entity_type`：`company` \| `person`（必填）
- `--template`：自定义模板（可选，覆盖默认）
- `--headless` / `--no-headless`：是否无头（默认有头）
- `--profile`：profile 路径（可选）

**处理流程**：

1. 加载模板（自定义优先于配置文件中的默认模板）
2. **多模板分次执行**：每个模板独立构造 Google URL，分别访问保存
   - 同一实体的多次搜索之间随机间隔 5–15 秒（模拟人工节奏）
3. 启动持久化 Chrome（`launch_persistent_context` + `channel="chrome"`）
4. 逐个搜索 URL：访问 → 等待加载 → 保存 PDF + HTML + 截图 + 解析 JSON
5. 全部完成后关闭浏览器（保留 profile）

**重要修正**：v1 中 `templates.py` 把多模板用 ` OR ` 拼接成一条查询，这是错的——既会让查询超长，也会因为 `A AND B OR C AND D` 的运算优先级产生意外结果。v2 改为**每个模板单独发一次请求，单独保存一份 PDF**。

**输出**（每个模板一组）：

- `{entity}_{template_id}_{YYYYMMDDTHHMMSS}Z.pdf`
- `{entity}_{template_id}_{YYYYMMDDTHHMMSS}Z.html`（页面 DOM 快照）
- `{entity}_{template_id}_{YYYYMMDDTHHMMSS}Z.png`（全页面截图，兜底）
- `{entity}_{template_id}_{YYYYMMDDTHHMMSS}Z.json`（元数据 + best-effort 解析）

文件名时间戳使用 **UTC + ISO8601 紧凑格式**，避免跨时区/夏令时混淆。

### 3.3 FR-2：PDF 取证质量

PDF 是核心交付物。质量要求：

- 完整保留 Google 搜索结果第一页的全部内容（标题、摘要、链接、图片）
- 保留背景色与图片（`printBackground=True`）
- A4 尺寸，无白边
- 文件名包含实体名 + 模板编号 + UTC 时间戳，可从文件名识别归属

**取证元数据**（写入同名 JSON）：

```json
{
  "entity": "三鹿集团",
  "entity_type": "company",
  "template_id": "company_default_1",
  "search_template": "\"三鹿集团\" AND (欺诈 OR 投诉 OR ...)",
  "search_url": "https://www.google.com/search?q=...",
  "searched_at_utc": "2026-04-28T07:30:00Z",
  "searched_at_local": "2026-04-28T15:30:00+08:00",
  "browser": {
    "channel": "chrome",
    "version": "Chrome/124.0.6367.62",
    "headless": false,
    "user_agent": "Mozilla/5.0 ...",
    "viewport": {"width": 1280, "height": 900}
  },
  "evidence": {
    "pdf_path": "output/三鹿集团_company_default_1_20260428T073000Z.pdf",
    "pdf_sha256": "a1b2c3...",
    "pdf_bytes": 245678,
    "html_path": "output/三鹿集团_company_default_1_20260428T073000Z.html",
    "html_sha256": "d4e5f6...",
    "screenshot_path": "output/三鹿集团_company_default_1_20260428T073000Z.png"
  },
  "results": [
    {"rank": 1, "title": "...", "url": "...", "snippet": "...", "source": "...", "date": ""}
  ],
  "results_parse_status": "success",
  "metadata": {
    "total_results": 10,
    "page_load_ms": 4231,
    "attempt_count": 1,
    "had_user_interaction": false
  }
}
```

**关键设计点**：

- `pdf_sha256` 用于事后证明 PDF 未被篡改（合规审计或诉讼场景下重要）
- `searched_at_utc` 是权威时间，本地时间仅作展示
- `results_parse_status` 显式声明结构化解析的成败（`success` \| `partial` \| `failed`）；**解析失败不影响 PDF 交付**
- `had_user_interaction` 记录是否触发过用户手动操作（reCAPTCHA、登录刷新等），便于审计

### 3.4 FR-3：浏览器 Profile 管理

**Profile 默认路径**：

| 操作系统 | 路径 |
|---------|------|
| macOS | `~/Library/Application Support/google_search/profile` |
| Linux | `~/.local/share/google_search/profile` |
| Windows | `%APPDATA%/google_search/profile` |

**首次运行行为**：

- profile 目录不存在 → 创建空 profile，启动有头 Chrome
- CLI 输出明确引导："请在弹出的浏览器中登录 Google 并完成首次设置（关闭无关弹窗、cookie banner 等），完成后回到终端按 Enter"
- 用户操作完成后，工具继续执行后续流程
- 关闭浏览器后，所有 cookies/local storage 持久化到 profile 目录

**后续运行**：

- 自动复用 profile，无需用户介入
- 如检测到登录失效（特征：搜索结果页出现"sign in"提示），CLI 提示运行 `google-search login`

**注意事项**：

- profile 与系统 Chrome 默认 profile **完全隔离**，不会污染用户日常浏览
- 单一 profile 同时只能被一个工具实例使用（Chrome 自身的锁机制）；并发运行时第二个实例直接失败并提示
- profile 不可跨机器迁移（cookies 与设备指纹绑定，迁移后会被 Google 视为可疑登录）

### 3.5 FR-4：失败处理

**失败分类与策略**：

| 错误类型 | 处理方式 |
|---------|---------|
| 网络超时（默认 30s）| 重试 1 次；仍失败则保存错误 JSON，继续下一个模板 |
| 页面加载失败 | 同上 |
| 触发 reCAPTCHA / 异常流量页 | **headed 模式：暂停最多 120 秒等用户手动通过；headless 模式：直接失败** |
| 登录失效 | CLI 输出明确提示；本次任务结束，不再继续 |
| profile 被锁定（其他实例运行中） | 立即失败，提示用户 |
| Chrome 未安装 | 启动前预检，给出安装指引 |

**重要原则**：

- **任何失败都生成一份带 error 标记的 JSON 文件**，方便事后审计
- 多模板执行中，单个模板失败不阻断其他模板
- CLI 退出码：全部成功=0，部分成功=1，全部失败=2

### 3.6 FR-5：配置管理

**`config.yaml`（v2 简化版）**：

```yaml
profile:
  path: ~/.local/share/google_search/profile

browser:
  channel: chrome           # chrome | chromium | msedge
  headless: false
  viewport:
    width: 1280
    height: 900

search:
  hl: zh-CN
  gl: cn
  inter_query_delay_seconds: [5, 15]   # 多查询间随机间隔（秒）
  page_load_timeout_seconds: 30
  network_idle_timeout_seconds: 30
  captcha_wait_seconds: 120             # headed 模式下等用户手动操作的最长时间

search_templates:
  company:
    - id: company_default_1
      template: '"{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约)'
    - id: company_default_2
      template: '"{name}" AND (调查 OR 处罚 OR 监管 OR 违规 OR 黑名单)'
  person:
    - id: person_default_1
      template: '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕)'
    - id: person_default_2
      template: '"{name}" AND (受贿 OR 挪用 OR 潜逃)'

output:
  directory: ./output
  save_html: true
  save_screenshot: true
```

**v1 中被移除的配置项**：

- `proxy.*` 整段
- `user_agents`（直接使用真实浏览器自带 UA）

**环境变量**（保留）：

| 环境变量 | 作用 |
|---------|------|
| `GOOGLE_SEARCH_PROFILE` | 覆盖 profile 路径 |
| `GOOGLE_SEARCH_OUTPUT_DIR` | 覆盖输出目录 |

环境变量优先级高于 `config.yaml`；`config.yaml` 本身可由 `--config` 指定路径。

---

## 4. 非功能需求

### 4.1 性能

- 单实体单模板：< 30 秒（浏览器启动 ~3s + 页面加载 ~5–10s + PDF 生成 ~2s）
- 单实体两模板（默认配置含间隔）：< 90 秒
- 并发：v0.1 顺序执行，不支持并发（profile 锁定限制）

### 4.2 可靠性

- 首次运行需用户介入登录的概率高，必须明确引导，不能让用户面对一个无声卡住的程序
- 多模板搜索互相独立：单个失败不影响其他
- 任何失败都有可审计的产物（PDF + JSON 至少有 JSON）

### 4.3 兼容性

- Python：>= 3.10
- 操作系统：macOS、Linux、**Windows**（v1 限制为 macOS/Linux 没必要，Playwright 支持所有平台）
- 浏览器：用户系统已安装的 Chrome（推荐）或 Chromium / Edge

### 4.4 安全与隐私

- profile 目录权限设为 `0700`（仅当前用户可读写），避免本机其他用户读取登录态
- 工具本身不上报任何遥测数据
- 输出文件不含访问 cookie 等敏感信息（仅含 SERP 内容）

### 4.5 v0.1 限制

- 不支持批量（单次单实体）
- 不访问搜索结果链接的目标页（只保存 SERP）
- 不做情感分析、去重、关键词抽取
- 不支持 Google 以外的搜索引擎

---

## 5. CLI 接口

### 5.1 命令结构

```bash
# 单实体搜索
google-search search <entity> <type> [OPTIONS]

# 重新登录（启动有头 Chrome 让用户登录）
google-search login

# 检查 profile 状态（是否存在、上次更新时间、登录态是否有效）
google-search profile-status

# 批量（v0.2）
google-search batch <csv_file> [OPTIONS]
```

### 5.2 search 子命令参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `entity` | str | ✅ | - | 实体名称 |
| `entity_type` | choice | ✅ | - | `company` \| `person` |
| `-t, --template` | str | - | - | 自定义模板，含 `{name}` 占位符 |
| `--headless` | flag | - | False | 无头模式 |
| `--profile` | path | - | 见 FR-3 | 自定义 profile 路径 |
| `-c, --config` | path | - | `config.yaml` | 配置文件路径 |
| `-o, --output-dir` | path | - | 见 config | 输出目录 |
| `--no-html` | flag | - | False | 跳过 HTML 快照 |
| `--no-screenshot` | flag | - | False | 跳过截图 |

### 5.3 输出示例

```
$ google-search search "三鹿集团" company

✓ 检测到 profile：~/.local/share/google_search/profile
✓ 启动 Chrome（chrome 124.0.6367.62, headed）
✓ 登录态有效

[1/2] 模板 company_default_1
  搜索: "三鹿集团" AND (欺诈 OR 投诉 OR ...)
  ✓ 页面加载完成（4.2s）
  ✓ PDF: output/三鹿集团_company_default_1_20260428T073000Z.pdf (240 KB)
  ✓ SHA-256: a1b2c3d4e5f6...
  ✓ 解析到 10 条结果
  ⏱ 等待 8.3 秒...

[2/2] 模板 company_default_2
  搜索: "三鹿集团" AND (调查 OR 处罚 OR ...)
  ✓ 页面加载完成（3.8s）
  ✓ PDF: output/三鹿集团_company_default_2_20260428T073012Z.pdf (220 KB)
  ⚠ DOM 解析失败（选择器可能已失效），PDF 已正常保存

完成: 2/2 PDF 成功生成，1/2 解析成功
输出目录: output/
总耗时: 22.5 秒
```

### 5.4 错误输出示例

```
$ google-search search "三鹿集团" company

✗ profile 不存在：~/.local/share/google_search/profile
提示: 请先运行 `google-search login` 完成首次登录配置
```

```
$ google-search search "三鹿集团" company --headless

[1/2] 模板 company_default_1
  ⚠ 检测到 reCAPTCHA 页面
  ✗ 当前为 headless 模式，无法人工介入
  提示: 移除 --headless 参数后重试，或运行 `google-search login` 重新登录
```

---

## 6. 项目结构

```
google-search/
├── src/google_search/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Click CLI（含 search / login / profile-status / batch 子命令）
│   ├── config.py           # YAML 加载（依赖注入，不再用模块级单例）
│   ├── exceptions.py       # 简化为 3 类：UserActionRequired / Recoverable / Fatal
│   ├── models.py           # SearchResult / SearchTaskResult / EvidenceMetadata
│   ├── templates.py        # 模板加载 + URL 构造（多模板返回 list[Query]）
│   ├── browser.py          # launch_persistent_context + CDP PDF
│   ├── searcher.py         # 简化的搜索编排（无代理/UA 轮换）
│   ├── pdf.py              # CDP Page.printToPDF + SHA-256 计算
│   └── parser.py           # DOM 解析（best-effort，失败不阻塞）
│
├── tests/
│   ├── test_templates.py
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_searcher.py    # Mock browser
│   └── test_parser.py      # 用本地 fixture HTML
│
├── templates/default.yaml
├── config.yaml
├── docs/
│   ├── PRD.md              # v1（保留备查）
│   ├── PRD-v2.md           # 本文档
│   ├── ARCHITECTURE.md     # v1（保留备查）
│   └── ARCHITECTURE-v2.md  # 待按本 PRD 同步
└── output/                 # 不入 git
```

**与 v1 对比**：

- 删除：`proxy.py`、`ua_pool.py`、相关测试
- 拆分：原 `searcher._parse_search_results` 独立成 `parser.py` 模块（明确 best-effort 语义）
- 修改：`browser.py` 改为持久化 context；`pdf.py` 改用 CDP；`cli.py` 增加子命令

---

## 7. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 用户首次运行不知道要登录 Google | 高 | 中 | CLI 输出明确引导；profile 不存在时直接进入登录子命令 |
| 偶发 reCAPTCHA | 中 | 低 | headed 模式下用户可直接手动通过，工具最长等 120s |
| Google DOM 改版导致 JSON 解析失败 | 高 | 低 | best-effort 设计，PDF 不受影响；`parser.py` 维护多套选择器 fallback |
| 中国大陆访问 Google | 视用户而定 | 高 | **明确声明：本工具假设用户已具备访问 Google 的网络条件**（用户自己的 VPN/代理），工具不内置代理 |
| profile 占用磁盘 | 低 | 低 | 文档说明清理方式（`google-search profile-status --reset`） |
| profile 跨机器不可移植 | 中 | 中 | 文档说明每台机器需独立首次登录 |
| `page.pdf()` 在 headed Chrome 下不可用 | 中 | 高 | 通过 CDP `Page.printToPDF` 调用（详见 ARCHITECTURE-v2） |
| 用户对"负面新闻"取证的法律边界不清 | 中 | 中 | 文档加合规说明章节，CLI 首次运行展示一次性提示 |

---

## 8. v0.1 成功标准

1. ✅ `google-search search "测试公司" company` 一键执行，无需配置代理
2. ✅ 首次运行弹出 Chrome 让用户登录，登录后 profile 持久化
3. ✅ 默认两个公司模板各生成一份 PDF，文件名规范，含 UTC 时间戳
4. ✅ 每份 PDF 对应一份 JSON，含 `pdf_sha256` 字段
5. ✅ DOM 解析失败时，PDF 仍能正常输出，JSON 中 `results_parse_status: failed`
6. ✅ `--template` 参数可覆盖默认模板
7. ✅ `--headless` 参数可切换无头模式（headed 仍为默认）
8. ✅ 触发 reCAPTCHA 时（headed），用户手动通过后流程继续
9. ✅ `google-search profile-status` 正确显示 profile 状态
10. ✅ 通过 `ruff check .`，核心模块（templates、searcher、parser、pdf）有单元测试

---

## 9. 后续迭代

| 版本 | 主要功能 |
|------|---------|
| v0.2 | CSV 批量输入；任务级断点续做；登录态自检 |
| v0.3 | SQLite 持久化 + 跨次去重；按时间轴比对结果差异 |
| v0.4 | 详情页抓取（点击进入并保存原文 PDF） |
| v0.5 | LLM 辅助负面性判断 + 摘要生成 |
| v1.0 | SerpAPI / Bright Data SERP 作为兜底数据源（CI 模式 / 高峰备用） |

---

## 10. 从 v1 迁移指南

| v1 文件/模块 | v2 处理方式 |
|------------|------------|
| `proxy.py` | **删除** |
| `ua_pool.py` | **删除** |
| `tests/test_proxy.py`、`tests/test_ua_pool.py` | **删除** |
| `browser.py` | **重写**：`launch_persistent_context` + `channel="chrome"`，移除 stealth 注入脚本 |
| `searcher.py` | **大幅简化**：移除代理/UA 轮换分支；多模板循环改为分次执行；增加 reCAPTCHA 等待逻辑 |
| `cli.py` | **修复**：原代码 `config = Config(config_path)` 局部变量遮蔽模块级单例的 bug；增加 `login` / `profile-status` 子命令 |
| `config.py` | **改为依赖注入**：去掉模块级 `config = Config()` 单例；`Searcher`、`UAPool` 等通过构造参数接收配置 |
| `templates.py` | **改写 `build_search_query`**：返回 `list[Query]` 而非 OR 拼接的单条字符串；新增 `template_id` 字段 |
| `pdf.py` | **改用 CDP**：`page.context.new_cdp_session(page).send("Page.printToPDF", ...)`；新增 SHA-256 计算 |
| `models.py` | **新增** `EvidenceMetadata` 字段；时间字段拆为 UTC + local |
| `searcher._parse_search_results` | **拆出**为独立 `parser.py`，明确"best-effort、失败不抛"语义 |
| `exceptions.py` | **简化**：保留 `UserActionRequired`、`RecoverableError`、`FatalError`；删除 `CaptchaError`、`ForbiddenError`、`ProxyAuthError` 等不再使用的细分类型 |
| `config.yaml` | **删除** `proxy`、`user_agents` 段；**新增** `profile`、`browser`、`search.inter_query_delay_seconds` 等段 |

---

## 11. 合规说明（新增）

本工具用于辅助合法的尽调与风控工作。使用本工具时，用户应自行确认：

- 搜索目标符合所在司法辖区的法律和所属机构的合规要求
- 处理涉及自然人的搜索结果时，遵守适用的个人信息保护法律（如中国《个人信息保护法》、欧盟 GDPR）
- 不将搜索结果用于未经授权的用途（如向第三方公开、用于不当竞争）
- 遵守 Google Terms of Service

CLI 首次运行将展示一次性合规提示，用户确认后将该确认状态写入 profile 元数据。

---

**文档结束**

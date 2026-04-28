# 产品需求文档（PRD）

**文档版本**：v1.0
**日期**：2026-04-09
**状态**：第一期开发中

---

## 1. 产品概述

### 1.1 产品名称

Google 负面新闻排查系统

### 1.2 产品定位

基于 Playwright 无头浏览器的 Google 搜索负面新闻自动化排查工具。通过 Chromium 浏览器自动访问 Google，搜索目标实体（公司或个人）的负面新闻信息，并保存搜索结果快照。

### 1.3 背景

本产品源于《Google 搜索负面新闻排查操作指南》中的手动排查流程。该流程要求人工打开 Google、输入查询、保存截图并记录结果，效率低下且无法规模化。本产品旨在将此流程自动化，使排查人员从重复性操作中解放。

### 1.4 核心价值

- **零 API 依赖**：不依赖 Google 官方 API，使用无头浏览器直连
- **操作一致**：每次排查流程标准化，结果可对比
- **可扩展**：预留批量查询、SERP API 切换等扩展能力

---

## 2. 用户故事

### 2.1 目标用户

- 企业风控/合规部门：排查合作方背景
- 尽职调查人员：投资/并购前的负面信息核查
- 记者/自媒体：新闻线索挖掘
- 个人：了解特定人物/公司的公开评价

### 2.2 典型用户故事

**故事 1：企业风控排查**
> 作为风控人员，我需要对潜在合作伙伴进行负面新闻排查。
> 当我输入公司名称后，系统自动搜索并保存 PDF，我无需手动打开浏览器、输入关键词、截图。
> 这样可以将单次排查时间从 15 分钟缩短到 3 分钟。

**故事 2：使用自定义关键词**
> 作为调查记者，我需要对同一公司使用特定的搜索组合（如包含"举报"、"诈骗"等词）。
> 当我传入自定义模板时，系统使用我的模板而非预定义模板执行搜索。
> 这样我可以灵活调整搜索策略，不被固定模板限制。

---

## 3. 功能需求

### 3.1 功能范围总览

| 功能模块 | 第一期 | 后续迭代 |
|----------|--------|----------|
| 单实体搜索 | ✅ | - |
| 批量搜索 | - | ✅ |
| 搜索模板配置 | ✅ | - |
| 自定义模板 | ✅ | - |
| PDF 结果保存 | ✅ | - |
| JSON 结果保存 | ✅ | - |
| 代理池轮换 | ✅ | - |
| UA 轮换 | ✅ | - |
| 失败重试 | ✅ | - |
| 原始新闻详情页抓取 | - | ✅ |
| 情感分析 | - | ✅ |
| SQLite 数据库持久化 | - | ✅ |
| SERP API 备份 | - | ✅ |

### 3.2 FR-1：搜索执行

**描述**：通过无头 Chromium 浏览器访问 Google 搜索，执行负面新闻查询。

**输入**：
- `entity`：实体名称（必填，字符串）
- `entity_type`：实体类型（必填，枚举值 `company` 或 `person`）
- `template`：搜索模板（可选，字符串，默认使用配置文件中的预定义模板）

**搜索模板（默认）**：

- **公司模板**：
  ```
  "{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约 OR 调查 OR 处罚 OR 监管 OR 违规 OR 黑名单)
  ```

- **个人模板**：
  ```
  "{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕 OR 受贿 OR 挪用)
  ```

**处理逻辑**：
1. 如果传入 `template`，使用传入的自定义模板，将 `{name}` 替换为实体名称
2. 如果未传入 `template`，根据 `entity_type` 从配置文件加载对应预定义模板
3. 构造 Google 搜索 URL：`https://www.google.com/search?q={URL编码的查询}&hl=zh-CN&gl=cn`
4. 启动 headless Chromium，访问搜索 URL
5. 等待页面完全加载（networkidle + 超时兜底）
6. 执行后续 PDF 保存和 JSON 记录

**输出**：
- 搜索结果 PDF 文件
- 搜索结果 JSON 文件

**验收标准**：
- [ ] 公司名称"三鹿集团"，使用公司模板搜索，PDF 和 JSON 均正确生成
- [ ] 使用 `--template '"{name}" AND (欺诈 OR 投诉)'` 自定义模板，搜索使用该模板而非预定义模板
- [ ] 个人名称"李四"，使用个人模板搜索

---

### 3.3 FR-2：结果保存

**描述**：将 Google 搜索结果保存为 PDF 和 JSON 文件。

#### 3.3.1 PDF 保存

**要求**：
- 捕获完整的第一页 Google 搜索结果（全页面，非视口截图）
- 保持 Google 页面原始布局和样式（背景色、字体、图片）
- 文件命名格式：`{实体名}_{YYYYMMDD}_{HHMMSS}.pdf`
- 保存路径：`config.output.directory`（默认 `./output/`）

**技术实现**：
- 使用 Playwright `page.pdf()` 方法，`print_background=True`
- 等待策略：`networkidle` 事件触发后，等待额外 2 秒确保动态内容渲染完成
- 如果 `networkidle` 30 秒内未触发，使用 `domcontentloaded` + 5 秒固定等待兜底

**PDF 质量要求**：
- [ ] PDF 中包含 Google 页面完整内容，不截断
- [ ] 搜索结果的背景色、图片、链接样式与浏览器中一致
- [ ] 文件名包含实体名、日期、时间，可从文件名识别内容

#### 3.3.2 JSON 保存

**要求**：
- 文件命名格式：`{实体名}_{YYYYMMDD}_{HHMMSS}.json`
- 与 PDF 同目录

**JSON 结构**：
```json
{
  "entity": "实体名称",
  "entity_type": "company | person",
  "search_template": "实际使用的搜索模板",
  "search_url": "https://www.google.com/search?q=...",
  "searched_at": "2026-04-09T15:30:00",
  "proxy_used": "http://proxy.example.com:8080 | null",
  "results": [
    {
      "rank": 1,
      "title": "新闻标题",
      "url": "https://example.com/article",
      "snippet": "新闻摘要文本",
      "source": "新闻来源名称",
      "date": "发布日期（如有）"
    }
  ],
  "metadata": {
    "pdf_path": "./output/实体名_20260409_153000.pdf",
    "total_results": 10,
    "attempt_count": 1
  }
}
```

**验收标准**：
- [ ] JSON 文件包含所有搜索结果条目
- [ ] 每条结果包含 title、url、snippet 字段
- [ ] JSON 文件名与 PDF 文件名对应（仅扩展名不同）

---

### 3.4 FR-3：反爬规避

**描述**：通过代理池和 UA 轮换降低被 Google 反爬机制封禁的概率。

#### 3.4.1 代理池

**配置**：
```yaml
proxy:
  enabled: true
  pool:
    - http://user:pass@proxy1.example.com:8080
    - http://user:pass@proxy2.example.com:8080
```

**行为**：
- 每次搜索从池中按顺序选取一个代理
- 失败重试时轮换到下一个代理（用过的代理不再使用同一任务）
- `enabled: false` 时不使用代理（开发/测试阶段）

#### 3.4.2 UA 池

**配置**：
```yaml
user_agents:
  - Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - ...
```

**行为**：
- 每次搜索从池中随机选取一个 UA
- 失败重试时从池中随机选取一个新 UA（与之前使用的不同）

#### 3.4.3 重试策略

**触发条件**：遇到以下错误时触发重试
- HTTP 403 Forbidden
- CAPTCHA 页面检测
- 网络超时（> 30 秒）
- 页面加载失败（JavaScript 错误）

**重试逻辑**：
```
attempt = 1
while attempt <= 3:
    proxy = proxy_pool.get()      # 当前代理（attempt 1 用池中第1个，attempt 2 用第2个）
    ua = ua_pool.get_random()     # 随机 UA（attempt 间可重复）
    try:
        result = execute_search(proxy, ua)
        break
    except RecoverableError:
        if attempt == 3:
            raise SearchFailedError("3次重试均失败")
        attempt += 1
        proxy_pool.rotate()
```

**验收标准**：
- [ ] 首次搜索失败后自动重试，最多 3 次
- [ ] 每次重试使用不同的代理 IP
- [ ] 每次重试使用不同的 UA
- [ ] 3 次全部失败后抛出明确错误，记录到日志

---

### 3.5 FR-4：配置管理

**描述**：所有运行时配置通过 YAML 文件管理，敏感信息通过环境变量注入。

#### 3.5.1 配置文件结构（config.yaml）

```yaml
proxy:
  enabled: false
  pool: []

user_agents:
  - Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36

search_templates:
  company:
    - '"{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约 OR 调查 OR 处罚 OR 监管 OR 违规 OR 黑名单)'
  person:
    - '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕 OR 受贿 OR 挪用)'

output:
  directory: ./output
```

#### 3.5.2 环境变量覆盖

以下配置项可通过环境变量覆盖（优先级高于 config.yaml）：

| 环境变量 | 对应配置项 | 说明 |
|----------|------------|------|
| `PROXY_URL` | `proxy.pool[0]` | 单个代理的快捷配置 |

#### 3.5.3 模板配置（templates/default.yaml）

```yaml
company:
  - '"{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约)'
  - '"{name}" AND (调查 OR 处罚 OR 监管 OR 违规 OR 黑名单)'
person:
  - '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕)'
  - '"{name}" AND (受贿 OR 挪用 OR 潜逃)'
```

**验收标准**：
- [ ] 所有配置从 config.yaml 读取，无硬编码值
- [ ] `PROXY_URL` 环境变量存在时，覆盖 config.yaml 中的代理配置
- [ ] 自定义模板 `--template` 参数优先级高于预定义模板

---

## 4. 非功能需求

### 4.1 性能

- 单次搜索完成时间（不含重试）：目标 < 30 秒
- PDF 生成时间：目标 < 10 秒
- 最大并发搜索数（第一期）：1（顺序执行）

### 4.2 可靠性

- 无代理模式下，框架可正常运行（用于开发/测试）
- 重试 3 次后仍失败，明确报错，不静默跳过
- 网络不稳定时，使用超时保护（单个操作超时上限 60 秒）

### 4.3 兼容性

- Python 版本：>= 3.10
- Playwright 支持的操作系统：macOS、Linux
- 浏览器：headless Chromium（通过 Playwright 安装）

### 4.4 第一期限制

- **不登录 Google 账号**：使用匿名搜索
- **不访问原始新闻链接**：只保存 Google 搜索结果页
- **不支持批量查询**：一次只查一个实体
- **不保存到数据库**：仅使用 JSON 文件持久化
- **不使用付费代理**：第一期使用免费代理或无代理

---

## 5. CLI 接口设计

### 5.1 命令行语法

```bash
python -m google_search <entity> <type> [OPTIONS]

# 示例
python -m google_search "三鹿集团" company
python -m google_search "李四" person --template '"{name}" AND (诈骗 OR 起诉)'
```

### 5.2 参数定义

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `entity` | 字符串 | 是 | 要搜索的实体名称 |
| `type` | 枚举（company/person） | 是 | 实体类型，决定使用哪个搜索模板 |
| `--template` | 字符串 | 否 | 自定义搜索模板，优先级高于预定义模板 |

### 5.3 输出信息

```
正在初始化浏览器...
正在加载配置: config.yaml
正在使用代理: http://proxy.example.com:8080 (1/3)
正在搜索: "三鹿集团" AND (欺诈 OR 投诉 OR ...)
正在等待页面加载...
正在生成 PDF: output/三鹿集团_20260409_153000.pdf
正在保存 JSON: output/三鹿集团_20260409_153000.json
搜索完成。结果数: 10，PDF: 三鹿集团_20260409_153000.pdf
```

### 5.4 错误输出

```
错误: 代理连接失败 (proxy.example.com:8080)
错误: 3次重试均失败，请检查网络和代理配置
提示: 设置 proxy.enabled: false 可禁用代理（开发模式）
```

---

## 6. 项目结构

```
google-search/
├── CLAUDE.md                    # Claude Code 工作指南
├── README.md                    # 项目说明
├── pyproject.toml               # Python 项目配置
├── requirements.txt             # pip 依赖
├── config.yaml                  # 运行时配置
├── .env.example                 # 环境变量模板
├── .gitignore
│
├── src/google_search/           # 主包
│   ├── __init__.py
│   ├── __main__.py              # python -m google_search 入口
│   ├── cli.py                   # Click CLI
│   ├── config.py                # 配置加载
│   ├── browser.py               # Playwright 浏览器管理
│   ├── searcher.py              # 搜索流程编排
│   ├── pdf.py                   # PDF 生成
│   ├── ua_pool.py               # UA 池管理
│   ├── proxy.py                 # 代理池管理
│   └── templates.py             # 搜索模板加载
│
├── templates/
│   └── default.yaml             # 预定义搜索模板
│
├── docs/
│   ├── raw/                     # 原始资料
│   │   └── Google search负面新闻排查操作指南.pdf
│   ├── REQUIREMENTS.md           # 需求文档
│   ├── DESIGN.md                 # 技术设计文档
│   └── PRD.md                    # 本文档
│
├── output/                      # PDF + JSON 输出（不提交 git）
│
└── tests/
    ├── test_searcher.py
    ├── test_browser.py
    └── test_templates.py
```

---

## 7. 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| Google 封禁 IP（无代理） | 高 | 高 | 第一期即接入代理池 |
| Google 触发 CAPTCHA | 中 | 中 | 切换代理 + UA 重试 |
| 代理池质量差（免费代理） | 高 | 中 | 失败重试，设计期预留可手动终止的选项 |
| Playwright 页面渲染不一致 | 低 | 低 | 固定等待时间兜底 |
| 动态加载导致结果截断 | 中 | 中 | networkidle + 5秒固定等待 |

---

## 8. 第一期成功标准

1. `python -m google_search "测试公司" company` 能完整执行并生成 PDF + JSON
2. PDF 内容完整包含第一页所有搜索结果
3. JSON 包含所有搜索结果的标题、URL、摘要
4. 失败时自动重试（不同代理 + 不同 UA），重试 3 次后报错
5. 所有配置（代理、UA、模板）均可通过 config.yaml 调整
6. `python -m google_search "测试" company --template '"{name}" AND (欺诈)'` 使用自定义模板
7. 代码通过 `ruff check .` 无 lint 错误
8. 测试覆盖核心模块（searcher、browser、templates）

---

## 9. 后续迭代规划

| 版本 | 功能 |
|------|------|
| v0.2 | 批量 CSV 输入（一次查多个实体） |
| v0.3 | SQLite 数据库持久化 + 去重 |
| v0.4 | 原始新闻详情页抓取（抽取正文） |
| v0.5 | 情感分析（负面/中性/正面） |
| v1.0 | SERP API 作为备份数据源 |

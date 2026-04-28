## Why

v1 把产品定位为"基于无头浏览器的 Google 搜索爬虫"，导致架构堆砌了代理池、UA 池、反爬规避等大量与实际需求无关的复杂度。v2 重新定位为"面向单用户的浏览器自动化取证工具"——核心是把"打开 Chrome → 输入查询 → 另存为 PDF"这套人工流程自动化，输出可作为合规/尽调证据的 PDF 文件。

## What Changes

### 删除的模块
- `src/google_search/proxy.py` — 不再需要内置代理池
- `src/google_search/ua_pool.py` — 不再需要 UA 池，直接使用真实浏览器身份
- `tests/test_proxy.py`、`tests/test_ua_pool.py` — 相关测试删除

### 重写的模块
- **`browser.py`**：从"启动新匿名 Chromium context"改为"启动绑定持久化 profile 的 Chrome，复用用户已登录的 Google 状态"
- **`pdf.py`**：从 `page.pdf()`（仅 headless Chromium 支持）改为 CDP `Page.printToPDF`（支持 headed Chrome）
- **`searcher.py`**：移除代理/UA 轮换逻辑；多模板从 OR 拼接改为分次独立执行；增加 reCAPTCHA 等待逻辑
- **`cli.py`**：修复 v1 中 `config = Config(config_path)` 局部变量遮蔽模块级单例的 bug；新增 `login` / `profile-status` 子命令
- **`config.py`**：从模块级单例 `config = Config()` 改为显式依赖注入
- **`exceptions.py`**：从 7 个细分异常类型简化为 3 类（`UserActionRequired` / `RecoverableError` / `FatalError`）

### 新增的模块
- **`parser.py`**：从 `searcher` 拆出的 best-effort DOM 解析器，明确"失败不抛异常、PDF 优先"语义
- **`models.py` 扩展**：新增 `EvidenceMetadata`（SHA-256、UTC 时间戳、HTML/截图路径）、`TemplateRunResult`

### 配置变更
- `config.yaml` 删除 `proxy.*`、`user_agents` 整段
- `config.yaml` 新增 `profile`、`browser`、`search.inter_query_delay_seconds` 等段

### CLI 行为变更
- 默认有头模式（`--headless` 可选）
- 多模板分次执行（不再 OR 拼接成单条查询）
- 触发 reCAPTCHA 时 headed 模式暂停等待用户手动通过，headless 模式直接失败
- 首次运行引导用户登录 Google 并持久化 profile

### 取证能力新增
- PDF SHA-256 计算
- UTC ISO8601 时间戳（文件名 + JSON）
- HTML 快照 + PNG 全页面截图（多重证据冗余）
- `had_user_interaction` 标记（记录是否触发用户手动操作）

## Capabilities

### New Capabilities

- **`browser-automation-forensics`**: 主产品定位——基于 Playwright 的 Google 搜索取证工具，自动启动绑定独立 profile 的 Chrome，按预设模板执行搜索，将搜索结果页完整保存为 PDF 作为排查证据
- **`persistent-browser-profile`**: 浏览器 profile 持久化机制，首次登录后复用 Google cookies 和登录态，无需重复处理 reCAPTCHA
- **`headed-browser-default`**: 有头模式为默认（可见执行过程），支持 `--headless` 切换
- **`cdp-pdf-generation`**: 通过 Chrome DevTools Protocol 的 `Page.printToPDF` 生成 PDF（`page.pdf()` 仅支持 headless Chromium，不支持 headed 或 channel="chrome"）
- **`forensics-metadata`**: PDF 生成后计算 SHA-256，输出 JSON 包含 UTC 时间戳、浏览器信息、取证元数据，支持事后验证文件未被篡改
- **`user-intervention-captcha`**: headed 模式下检测到 reCAPTCHA/sorry 页面时暂停等待用户手动通过（最多 120 秒），headless 模式直接失败
- **`multi-template-sequential`**: 每个模板独立构造 Google URL，分别访问保存 PDF（不再用 OR 拼接），模板间随机停顿 5-15 秒模拟人工节奏

### Modified Capabilities

- **`search-templates`**: v1 的 `build_search_query` 用 OR 拼接所有模板为单条查询（错误），v2 改为返回 `list[Query]`，每个模板独立执行

## Impact

### 影响的代码
- `src/google_search/` 下多个核心模块（browser、pdf、searcher、cli、config、exceptions、templates）
- `tests/` 下相关测试文件

### 依赖变更
- 不再需要 `playwright install chromium`（改用系统 Chrome）
- 新增对用户机器已安装 Chrome 的依赖（可通过 `channel: chromium` 降级使用 Playwright bundled Chromium）

### 用户可见变更
- CLI 参数新增 `--headless`、`--no-html`、`--no-screenshot`
- 新增 `login` / `profile-status` 子命令
- 输出文件命名格式变化：`{entity}_{template_id}_{YYYYMMDDTHHMMSS}Z.pdf`
- 默认有头模式，首次运行会弹出 Chrome 窗口

### 安全与隐私
- profile 目录权限设为 `0700`（仅当前用户可读写）
- 工具本身不上报任何遥测数据

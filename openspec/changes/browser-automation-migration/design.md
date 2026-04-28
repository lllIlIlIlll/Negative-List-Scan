## Context

v1 产品定位为"基于无头浏览器的 Google 搜索爬虫"，架构围绕反爬（代理池、UA 池、stealth 注入、CAPTCHA 检测）设计，约 60% 的代码量服务于这些基础设施。实际用户反馈表明：

1. **定位偏差**：目标用户（风控/合规/尽调人员）需要的是"浏览器自动化取证工具"而非"爬虫"
2. **复杂度冗余**：代理池、UA 轮换对单用户本地场景毫无意义
3. **核心痛点**：用户真正需要的是把"打开 Chrome → 搜索 → 另存 PDF"流程自动化，输出可审计的取证文件

v2 重新定位后，需要从架构层面重构，删除无效模块，重写核心流程。

## Goals / Non-Goals

**Goals:**
- 实现"浏览器自动化取证工具"的产品定位
- 默认有头模式，用户可见执行过程，必要时手动介入
- 持久化 Chrome profile，复用用户已登录的 Google 状态
- PDF 作为核心交付物，支持 SHA-256 验证不可篡改性
- 简化错误处理，移除无关的代理/UA 基础设施

**Non-Goals:**
- 不做高频批量爬取（按人工节奏顺序执行）
- 不绕过 Google 反爬机制
- 不为中国大陆用户提供网络通路（假设用户已有 VPN）
- 不替代 SerpAPI 等专业 SERP 服务

## Decisions

### D1: 持久化 Browser Context 而非每次新建

**选择**：使用 `playwright.chromium.launch_persistent_context(user_data_dir=profile_path, channel="chrome")`

**替代方案对比**：
- `launch()` + `new_context()`: 每次新建匿名 context，无法复用登录态
- `launch_persistent_context()` + `channel="chrome"`: 绑定用户真实 Chrome profile，cookies 和登录态持久化

**理由**：用户已登录 Google 是核心诉求，否则每次都要处理 cookie banner 和 reCAPTCHA，开箱体验极差。

---

### D2: CDP `Page.printToPDF` 而非 `page.pdf()`

**选择**：通过 `page.context.new_cdp_session(page).send("Page.printToPDF", ...)` 生成 PDF

**替代方案对比**：
- `page.pdf()`: Playwright 官方 API，但文档明确说明"currently only supported in Chromium headless mode"
- CDP `Page.printToPDF`: Chrome DevTools Protocol 原生接口，支持 headed 模式

**理由**：v2 默认 headed（用户可见），而 `page.pdf()` 在 headed 或 `channel="chrome"` 下不可用。CDP 是唯一可靠方案。

---

### D3: 多模板分次执行而非 OR 拼接

**选择**：每个模板独立构造 URL，分别访问，分别保存 PDF

**替代方案对比**：
- `"A OR B OR C"`: 查询字符串过长，Google 运算优先级导致意外结果
- 分次执行：每次独立查询，结果纯净，可并行

**理由**：PRD-v2 明确指出 v1 的 OR 拼接是错误设计。

---

### D4: 简化为 3 类异常

**选择**：`UserActionRequired` / `RecoverableError` / `FatalError`

**替代方案对比**：
- v1 的 7 类细分异常：CaptchaError、ForbiddenError、ProxyAuthError、TimeoutError、SearchError、NonRecoverableError、...
- 3 类：足够覆盖所有场景，减少认知负担

**理由**：v2 移除了代理池和 UA 轮换，相关细分错误类型不再存在。简化后代码更易维护。

---

### D5: 配置改为依赖注入而非模块级单例

**选择**：`Config.load(path)` 作为 classmethod，返回实例注入到 `Searcher(cfg)`

**替代方案对比**：
- v1 模块级单例 `config = Config()`: CLI 的 `config = Config(config_path)` 创建局部变量遮蔽单例，导致 `--config` 参数失效
- 依赖注入：显式传递，消除全局状态

**理由**：修复 v1 bug，配置覆盖参数能正常生效。

---

## Risks / Trade-offs

- **[风险] CDP PDF 在 headed Chrome 下可能有渲染差异** → [缓解] 使用 `printBackground=True` 保留背景色；保留 HTML 快照和 PNG 截图作为兜底
- **[风险] profile 跨机器不可迁移** → [缓解] 文档明确说明每台机器需独立首次登录
- **[风险] 中国大陆用户访问 Google 依赖用户自身网络** → [缓解] 工具不内置代理，明确声明网络是用户自身问题
- **[风险] reCAPTCHA 频繁触发** → [缓解] headed 模式用户可直接手动通过；headless 模式明确失败并提示切换
- **[风险] Google DOM 改版导致解析失败** → [缓解] best-effort 设计，PDF 仍正常输出；维护多套选择器 fallback

## Migration Plan

按以下顺序执行（详见 ARCHITECTURE-v2.md 第 13 节）：

1. 删除文件：`proxy.py`、`ua_pool.py` 及相关测试
2. 更新 `config.py`：移除模块级单例，改为 `Config.load()` classmethod
3. 更新 `templates.py`：`build_search_query` → `build_queries`，返回 `list[Query]`
4. 更新 `models.py`：新增 `EvidenceMetadata`、`TemplateRunResult`
5. 重写 `browser.py`：`PersistentBrowser` + `launch_persistent_context` + `channel="chrome"`
6. 重写 `pdf.py`：CDP `Page.printToPDF` + SHA-256 + HTML/截图
7. 新增 `parser.py`：从 `searcher` 拆出 DOM 解析
8. 重写 `searcher.py`：移除代理/UA 轮换；多模板顺序执行
9. 重写 `cli.py`：Click Group + 子命令；修复 config bug
10. 简化 `exceptions.py`：保留 3 类
11. 更新 `config.yaml`：删除 proxy/user_agents，新增 profile/browser/search 段
12. 更新 `pyproject.toml`：版本 → 0.2.0
13. 运行 `pip install -e ".[dev]"`
14. 运行 `google-search login` 完成首次登录
15. 运行 `pytest` 验证

## Open Questions

1. **profile 清理机制**：用户长期使用后 profile 占用磁盘空间是否需要自动清理？（v0.1 不做，在 docs 说明清理方式即可）
2. **批量模式（v0.2）**：当前 scope 为单实体，批量模式的失败补搜、断点续做是否需要在 v0.1 预留接口？（不需要，先完成 v0.1）

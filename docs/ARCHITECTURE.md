# 技术架构设计及开发文档

**文档版本**：v1.0
**关联文档**：PRD.md、DESIGN.md
**日期**：2026-04-09

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [模块设计](#2-模块设计)
3. [数据模型](#3-数据模型)
4. [CLI 接口规范](#4-cli-接口规范)
5. [配置文件规范](#5-配置文件规范)
6. [搜索流程时序](#6-搜索流程时序)
7. [错误处理体系](#7-错误处理体系)
8. [PDF 生成机制](#8-pdf-生成机制)
9. [反爬规避策略实现](#9-反爬规避策略实现)
10. [测试策略](#10-测试策略)
11. [依赖与安装](#11-依赖与安装)
12. [目录结构规范](#12-目录结构规范)
13. [开发工作流](#13-开发工作流)

---

## 1. 系统架构概览

### 1.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                     1. 接入层（CLI）                        │
│                        cli.py                                │
│                   Click 命令行解析                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    2. 配置层                                 │
│               config.py / templates.py                       │
│         YAML 配置加载 + 环境变量注入 + 模板管理               │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   3. 资源池层                                 │
│              ua_pool.py / proxy.py                           │
│           User-Agent 池 + 代理 IP 池                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   4. 浏览器层                                 │
│                    browser.py                                │
│      Playwright BrowserContext + Page 生命周期管理            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  5. 搜索流程层                                 │
│                   searcher.py                                │
│     搜索编排 + 重试逻辑 + 结果解析 + PDF/JSON 输出             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   6. 输出层                                   │
│                      pdf.py                                  │
│              PDF 全页面渲染 + 文件输出                        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 模块依赖关系

```
cli.py
  └── config.py (加载配置)
  └── searcher.py
        ├── config.py
        ├── templates.py (加载模板)
        ├── proxy.py (代理池)
        ├── ua_pool.py (UA池)
        ├── browser.py (Playwright)
        └── pdf.py (PDF生成)
```

**依赖规则**：
- 上层模块可导入下层模块，下层模块不可导入上层模块
- 同层模块之间可相互导入
- `browser.py` 是底层基础设施，不依赖任何其他业务模块
- `cli.py` 是入口，仅做参数解析和流程触发，不含业务逻辑

---

## 2. 模块设计

### 2.1 config.py — 配置加载

**文件**：`src/google_search/config.py`

**职责**：
- 加载 `config.yaml` 文件
- 支持环境变量覆盖配置
- 提供类型安全的配置访问接口

**核心类**：

```python
class Config:
    """配置单例，全局唯一访问点"""

    def __init__(self, config_path: str = "config.yaml"):
        self._data: dict = yaml.safe_load(Path(config_path).read_text())
        self._apply_env_overrides()

    @property
    def proxy(self) -> ProxyConfig:
        return ProxyConfig(self._data.get("proxy", {}))

    @property
    def user_agents(self) -> list[str]:
        return self._data.get("user_agents", [])

    @property
    def output_directory(self) -> Path:
        return Path(self._data.get("output", {}).get("directory", "./output"))

    def get_proxy_pool(self) -> list[str]:
        # 支持 PROXY_URL 环境变量覆盖
        env_proxy = os.environ.get("PROXY_URL")
        if env_proxy:
            return [env_proxy]
        return self._data.get("proxy", {}).get("pool", [])


class ProxyConfig:
    """代理配置"""

    def __init__(self, data: dict):
        self.enabled: bool = data.get("enabled", False)
        self.pool: list[str] = data.get("pool", [])

    @property
    def is_enabled(self) -> bool:
        return self.enabled and len(self.pool) > 0
```

**关键行为**：
- `Config` 类在模块级别实例化为单例 `config = Config()`
- 所有模块导入 `from google_search.config import config` 获取同一实例
- 环境变量 `PROXY_URL` 存在时，覆盖 YAML 中的 `proxy.pool`，使 `config.get_proxy_pool()` 只返回这一个代理

---

### 2.2 templates.py — 搜索模板管理

**文件**：`src/google_search/templates.py`

**职责**：
- 加载 `templates/default.yaml`
- 根据实体类型返回预定义模板列表
- 将 `{name}` 占位符替换为实际实体名称
- 支持多个模板，返回时拼接为 Google 搜索 URL

**核心函数**：

```python
def load_templates(template_path: str = "templates/default.yaml") -> dict[str, list[str]]:
    """加载模板文件，返回 {type: [templates]}"""
    return yaml.safe_load(Path(template_path).read_text())

def build_search_query(entity: str, entity_type: str, template: str | None = None) -> str:
    """
    构造搜索查询字符串。

    Args:
        entity: 实体名称
        entity_type: "company" 或 "person"
        template: 自定义模板，不为 None 时优先使用

    Returns:
        URL 编码后的 Google 搜索查询字符串
    """
    if template:
        query = template.replace("{name}", entity)
    else:
        templates = load_templates()
        # 多个模板用 OR 拼接
        template_list = templates.get(entity_type, [])
        query = " OR ".join(t.replace("{name}", entity) for t in template_list)

    return query

def build_google_url(query: str, hl: str = "zh-CN", gl: str = "cn") -> str:
    """构造 Google 搜索 URL"""
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/search?q={encoded}&hl={hl}&gl={gl}"
```

---

### 2.3 ua_pool.py — UA 池管理

**文件**：`src/google_search/ua_pool.py`

**职责**：
- 从配置加载 UA 列表
- 提供随机选取接口
- 提供不重复选取接口（用于重试场景）

**核心类**：

```python
import random
from google_search.config import config

class UAPool:
    """UA 池，支持随机选取和不重复选取"""

    def __init__(self, uas: list[str] | None = None):
        self._pool: list[str] = uas or config.user_agents
        if not self._pool:
            # 默认 UA（当配置为空时使用）
            self._pool = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]

    def get_random(self) -> str:
        """随机返回一个 UA"""
        return random.choice(self._pool)

    def get_random_not_in(self, excluded: set[str]) -> str:
        """返回不在 excluded 集合中的随机 UA"""
        available = [ua for ua in self._pool if ua not in excluded]
        if not available:
            return random.choice(self._pool)  # 用尽则随机
        return random.choice(available)
```

**使用方式**：

```python
ua_pool = UAPool()
ua = ua_pool.get_random()           # 随机选取
ua = ua_pool.get_random_not_in({"ua1", "ua2"})  # 重试场景，排除已用过的
```

---

### 2.4 proxy.py — 代理池管理

**文件**：`src/google_search/proxy.py`

**职责**：
- 从配置加载代理列表
- 按顺序轮换选取代理
- 支持代理切换（重试时调用）

**核心类**：

```python
from google_search.config import config

class ProxyPool:
    """代理池，支持顺序轮换"""

    def __init__(self, proxies: list[str] | None = None):
        self._pool: list[str] = proxies or config.get_proxy_pool()
        self._index: int = 0
        self._used: set[str] = set()  # 记录本轮任务中已用过的代理

    def get(self) -> str | None:
        """返回当前代理，不切换"""
        if not self._pool:
            return None
        return self._pool[self._index % len(self._pool)]

    def rotate(self) -> str | None:
        """
        切换到下一个代理。
        返回下一个代理，如果池已用尽返回 None。
        """
        if not self._pool:
            return None

        # 标记当前代理为已用
        current = self._pool[self._index % len(self._pool)]
        self._used.add(current)

        # 找到下一个未用过的代理
        original_index = self._index
        while True:
            self._index += 1
            next_proxy = self._pool[self._index % len(self._pool)]
            if next_proxy not in self._used:
                return next_proxy
            if self._index - original_index >= len(self._pool):
                # 所有代理都用过了，重置
                self._used.clear()
                return None

    def mark_failed(self, proxy: str) -> None:
        """标记一个代理为失败（可用于后续实现代理质量评分）"""
        pass  # 第一期暂不实现

    @property
    def exhausted(self) -> bool:
        """池中所有代理均已用尽"""
        return len(self._used) >= len(self._pool) and len(self._pool) > 0
```

**关键行为**：
- `get()` 不移动指针，重试时用 `rotate()` 切换
- `rotate()` 保证同一任务内不重复使用同一代理
- 当所有代理都用尽时，返回 `None`，触发任务失败

---

### 2.5 browser.py — 浏览器生命周期管理

**文件**：`src/google_search/browser.py`

**职责**：
- Playwright 全局浏览器实例管理（单例）
- 创建带有代理 + UA 的 BrowserContext
- 提供页面导航和等待策略
- 处理浏览器关闭（with 上下文管理器）

**核心类**：

```python
import asyncio
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional

class BrowserManager:
    """
    Playwright 浏览器管理器。

    使用方式（上下文管理器）：
        with BrowserManager() as browser_mgr:
            page = browser_mgr.new_page(proxy="http://...", ua="...")
            page.goto("https://...")
    """

    _instance: Optional["BrowserManager"] = None

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None

    def __enter__(self) -> "BrowserManager":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    @classmethod
    def get_instance(cls) -> "BrowserManager":
        """获取单例（延迟初始化）"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def new_context(
        self,
        proxy: str | None = None,
        user_agent: str | None = None,
    ) -> BrowserContext:
        """
        创建一个新的 BrowserContext（隔离环境）。

        Args:
            proxy: 代理 URL，格式 http://host:port 或 http://user:pass@host:port
            user_agent: User-Agent 字符串

        Returns:
            BrowserContext 实例
        """
        ctx_options: dict = {
            "ignore_https_errors": True,
        }

        if proxy:
            ctx_options["proxy"] = {"server": proxy}

        if user_agent:
            ctx_options["user_agent"] = user_agent

        return self._browser.new_context(**ctx_options)

    def new_page(
        self,
        proxy: str | None = None,
        user_agent: str | None = None,
    ) -> Page:
        """
        创建一个新的 Page（自动创建 Context）。

        便捷方法，等价于：
            ctx = new_context(proxy, ua)
            return ctx.new_page()
        """
        ctx = self.new_context(proxy=proxy, user_agent=user_agent)
        page = ctx.new_page()

        # 拦截 navigator.webdriver 标志
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        return page
```

**关键设计决策**：
- `BrowserManager` 是单例，保证整个进程只启动一个 Chromium 实例
- 每个搜索任务创建独立的 `BrowserContext`（隔离 cookie、代理、UA）
- `add_init_script` 注入脚本隐藏 webdriver 自动化特征
- 使用 `sync_api`（同步 API），避免 asyncio 复杂度

---

### 2.6 pdf.py — PDF 生成

**文件**：`src/google_search/pdf.py`

**职责**：
- 等待页面完全渲染
- 调用 Playwright `page.pdf()` 生成全页面 PDF
- 处理动态加载等待

**核心函数**：

```python
from pathlib import Path
from playwright.sync_api import Page

class PDFGenerator:
    """PDF 生成器"""

    def __init__(
        self,
        network_idle_timeout: int = 30_000,
        fallback_wait: int = 5_000,
    ):
        self._network_idle_timeout = network_idle_timeout
        self._fallback_wait = fallback_wait

    def wait_for_page_ready(self, page: Page) -> None:
        """
        等待页面完全加载。

        策略：
        1. 优先等待 networkidle（最多 30 秒）
        2. 如果超时，使用 domcontentloaded + 固定等待
        3. 固定等待后再次尝试渲染
        """
        try:
            page.wait_for_load_state(
                "networkidle",
                timeout=self._network_idle_timeout
            )
            # networkidle 后额外等待 2 秒确保 JS 渲染完成
            page.wait_for_timeout(2_000)
        except Exception:
            # 超时兜底：使用 domcontentloaded + 固定等待
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(self._fallback_wait)

    def generate(
        self,
        page: Page,
        output_path: Path,
        title: str = "",
    ) -> None:
        """
        生成 PDF 文件。

        Args:
            page: Playwright Page 对象
            output_path: PDF 输出路径
            title: PDF 内部标题（可选）
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pdf_options = {
            "path": output_path,
            "format": "A4",
            "print_background": True,
            "margin": {
                "top": "0",
                "bottom": "0",
                "left": "0",
                "right": "0",
            },
            "scale": 1.0,
        }

        if title:
            pdf_options["display_header_footer"] = True
            pdf_options["header_template"] = f"<div style='font-size:10px;text-align:center;'>{title}</div>"
            pdf_options["footer_template"] = "<div style='font-size:10px;text-align:center;'>Page <span class='pageNumber'></span> of <span class='totalPages'></span></div>"

        page.pdf(**pdf_options)
```

**PDF 生成参数详解**：

| 参数 | 值 | 说明 |
|------|------|------|
| `format` | `A4` | Google 搜索结果页面宽度适配 A4 |
| `print_background` | `True` | 必须为 True 才能保留背景色、图片 |
| `margin` | 0 | 消除页面白边，Google 结果是窄页面 |
| `scale` | 1.0 | 缩放比例，默认即可 |
| `display_header_footer` | `False` | 第一期不显示 header/footer |

---

### 2.7 searcher.py — 搜索流程编排

**文件**：`src/google_search/searcher.py`

**职责**：
- 编排完整的搜索流程
- 实现重试逻辑
- 调用 browser、pdf、templates 模块
- 解析页面 DOM 提取搜索结果
- 生成 JSON 输出文件

**核心类**：

```python
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from google_search.browser import BrowserManager
from google_search.config import config
from google_search.proxy import ProxyPool
from google_search.templates import build_search_query, build_google_url
from google_search.ua_pool import UAPool
from google_search.pdf import PDFGenerator

@dataclass
class SearchResult:
    """单条搜索结果"""
    rank: int
    title: str
    url: str
    snippet: str
    source: str = ""
    date: str = ""

@dataclass
class SearchTaskResult:
    """一次搜索任务的完整结果"""
    entity: str
    entity_type: str
    search_template: str
    search_url: str
    searched_at: str
    proxy_used: Optional[str]
    results: list[SearchResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

class Searcher:
    """
    搜索流程编排器。

    使用方式：
        searcher = Searcher()
        result = searcher.search("三鹿集团", "company")
    """

    MAX_RETRIES = 2  # 最多重试 2 次（加上首次共 3 次）

    def __init__(self):
        self._ua_pool = UAPool()
        self._proxy_pool = ProxyPool()
        self._pdf_gen = PDFGenerator()

    def search(
        self,
        entity: str,
        entity_type: str,
        custom_template: str | None = None,
    ) -> SearchTaskResult:
        """
        执行一次搜索。

        Args:
            entity: 实体名称
            entity_type: "company" 或 "person"
            custom_template: 自定义模板，不为 None 时优先使用

        Returns:
            SearchTaskResult 对象

        Raises:
            SearchError: 所有重试均失败时抛出
        """
        # 1. 构造查询
        query = build_search_query(entity, entity_type, custom_template)
        google_url = build_google_url(query)
        template_used = custom_template or f"{entity_type}_template"

        # 2. 重试循环
        last_error: Exception | None = None
        attempt = 0
        page = None
        proxy_used: str | None = None
        ua_used: str | None = None
        used_uas: set[str] = set()

        while attempt <= self.MAX_RETRIES:
            try:
                # 获取代理和 UA
                if attempt == 0:
                    proxy_used = self._proxy_pool.get()
                else:
                    proxy_used = self._proxy_pool.rotate()

                ua_used = self._ua_pool.get_random_not_in(used_uas)
                used_uas.add(ua_used)

                # 执行搜索
                page = self._execute_search(google_url, proxy_used, ua_used)
                break  # 成功，退出重试循环

            except RecoverableError as e:
                last_error = e
                attempt += 1
                if page:
                    page.context.close()
                    page = None
                if attempt > self.MAX_RETRIES:
                    raise SearchError(f"3次重试均失败: {e}") from e

        if page is None:
            raise SearchError("未获取到有效页面")

        # 3. 生成 PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(entity)
        pdf_path = config.output_directory / f"{safe_name}_{timestamp}.pdf"
        self._pdf_gen.wait_for_page_ready(page)
        self._pdf_gen.generate(page, pdf_path, title=f"Google搜索: {entity}")

        # 4. 解析结果
        results = self._parse_search_results(page)

        # 5. 生成 JSON
        json_path = config.output_directory / f"{safe_name}_{timestamp}.json"
        task_result = SearchTaskResult(
            entity=entity,
            entity_type=entity_type,
            search_template=template_used,
            search_url=google_url,
            searched_at=datetime.now().isoformat(),
            proxy_used=proxy_used,
            results=results,
            metadata={
                "pdf_path": str(pdf_path),
                "total_results": len(results),
                "attempt_count": attempt + 1,
            }
        )
        json_path.write_text(json.dumps(asdict(task_result), ensure_ascii=False, indent=2))

        page.context.close()

        return task_result

    def _execute_search(
        self,
        url: str,
        proxy: str | None,
        ua: str,
    ) -> Page:
        """实际执行搜索，返回加载完成的 Page"""
        with BrowserManager() as mgr:
            page = mgr.new_page(proxy=proxy, user_agent=ua)
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # 检测是否为 CAPTCHA 页面
            if self._is_captcha_page(page):
                raise CaptchaError("Google 触发了 CAPTCHA")

            # 检测是否为 403
            if page.url.startswith("https://www.google.com/sorry"):
                raise ForbiddenError("Google 返回 403")

            return page

    def _is_captcha_page(self, page: Page) -> bool:
        """检测是否为 CAPTCHA 页面"""
        title = page.title().lower()
        return "captcha" in title or "unusual traffic" in page.content().lower()

    def _parse_search_results(self, page: Page) -> list[SearchResult]:
        """解析页面 DOM，提取搜索结果"""
        # Google 搜索结果的选择器
        results = page.query_selector_all("div.g")
        parsed = []
        for i, result_el in enumerate(results):
            try:
                title_el = result_el.query_selector("h3")
                title = title_el.inner_text() if title_el else ""

                link_el = result_el.query_selector("a")
                url = link_el.get_attribute("href") if link_el else ""

                snippet_el = result_el.query_selector("div[data-sncf]")
                snippet = snippet_el.inner_text() if snippet_el else ""

                source_el = result_el.query_selector("span:not([class])")
                source = source_el.inner_text() if source_el else ""

                parsed.append(SearchResult(
                    rank=i + 1,
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=source,
                ))
            except Exception:
                continue

        return parsed

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """将实体名称转换为安全的文件名"""
        return re.sub(r'[\\/:*?"<>|]', '_', name)
```

**搜索流程时序图**：

```
用户调用
   │
   ▼
searcher.search()
   │
   ├─ build_google_url()          ← templates.py
   │
   ├─ [重试循环，最多 3 次]
   │    │
   │    ├─ proxy_pool.get()      ← proxy.py
   │    ├─ ua_pool.get_random() ← ua_pool.py
   │    │
   │    ├─ browser.new_page()    ← browser.py
   │    │    └─ page.goto(url)
   │    │
   │    ├─ [CAPTCHA/403 检测]
   │    │    └─ 抛出 RecoverableError
   │    │
   │    └─ [成功] break
   │
   ├─ pdf.wait_for_page_ready()   ← pdf.py
   ├─ pdf.generate()              ← pdf.py → 输出 PDF
   │
   ├─ searcher._parse_results()  → 提取 DOM
   │
   ├─ [生成 JSON]
   │    └─ json.dump() → 输出 JSON
   │
   └─ return SearchTaskResult
```

---

## 3. 数据模型

### 3.1 数据类定义

```python
# src/google_search/models.py

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class SearchResult:
    """单条搜索结果"""
    rank: int                          # Google 原始排名
    title: str                          # 结果标题
    url: str                            # 链接 URL
    snippet: str                        # 搜索摘要
    source: str = ""                    # 新闻来源（如有）
    date: str = ""                      # 发布日期（如有）

@dataclass
class SearchTaskResult:
    """一次搜索任务的完整结果"""
    entity: str                         # 实体名称
    entity_type: str                     # "company" 或 "person"
    search_template: str                 # 实际使用的搜索模板
    search_url: str                     # 完整的 Google 搜索 URL
    searched_at: str                    # ISO 格式时间
    proxy_used: Optional[str]           # 本次使用的代理（无代理时为 None）
    results: list[SearchResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
        # metadata 包含：
        #   - pdf_path: str
        #   - total_results: int
        #   - attempt_count: int

@dataclass
class SearchConfig:
    """搜索配置（从 config.yaml 加载）"""
    proxy_enabled: bool
    proxy_pool: list[str]
    user_agents: list[str]
    output_directory: str
    search_templates: dict[str, list[str]]
```

### 3.2 JSON 输出格式

```json
{
  "entity": "三鹿集团",
  "entity_type": "company",
  "search_template": "company_template",
  "search_url": "https://www.google.com/search?q=%22%E4%B8%89%E9%B9%BF%E9%9B%86%E5%9B%A2%22+AND+(%E6%AC%BA%E8%AF%88+OR+%E6%8A%95%E8%AF%9D+OR+%E6%9B%9D%E5%85%89+OR+%E7%BA%A0%E7%BA%B7+OR+%E8%B5%B7%E8%AF%89+OR+%E8%BF%9D%E7%BA%A6)&hl=zh-CN&gl=cn",
  "searched_at": "2026-04-09T15:30:00",
  "proxy_used": "http://proxy.example.com:8080",
  "results": [
    {
      "rank": 1,
      "title": "三鹿集团刑事附带民事诉讼案最新进展",
      "url": "https://news.example.com/article/123",
      "snippet": "法院今日对三鹿集团涉案人员作出判决...",
      "source": "法治日报",
      "date": "2026年4月1日"
    }
  ],
  "metadata": {
    "pdf_path": "./output/三鹿集团_20260409_153000.pdf",
    "total_results": 10,
    "attempt_count": 1
  }
}
```

---

## 4. CLI 接口规范

### 4.1 入口点

**方式 1（模块调用）**：
```bash
python -m google_search "三鹿集团" company
python -m google_search "李四" person --template '"{name}" AND (诈骗 OR 起诉)'
```

**方式 2（安装后）**：
```bash
google-search "三鹿集团" company
```

### 4.2 Click CLI 定义

```python
# src/google_search/cli.py

import click
import sys
from pathlib import Path

from google_search.searcher import Searcher, SearchError
from google_search.config import config

@click.command()
@click.argument("entity")
@click.argument("entity_type", type=click.Choice(["company", "person"]))
@click.option(
    "--template",
    "-t",
    "custom_template",
    default=None,
    help="自定义搜索模板，使用 {name} 作为实体名称占位符",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default="config.yaml",
    help="配置文件路径",
)
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="输出目录，覆盖 config.yaml 中的配置",
)
def main(
    entity: str,
    entity_type: str,
    custom_template: str | None,
    config_path: str,
    output_dir: str | None,
):
    """
    Google 负面新闻排查工具。

    执行 ENTITY 的负面新闻搜索，保存 PDF 和 JSON 结果。

    示例：

      google-search "三鹿集团" company

      google-search "李四" person --template '"{name}" AND (诈骗 OR 起诉)'
    """
    # 初始化配置
    config = Config(config_path)

    # 输出目录覆盖
    if output_dir:
        config._data["output"]["directory"] = output_dir

    click.echo(f"正在初始化搜索任务: {entity} ({entity_type})")
    click.echo(f"输出目录: {config.output_directory}")

    searcher = Searcher()

    try:
        result = searcher.search(entity, entity_type, custom_template)
        click.echo(click.style(f"✓ 搜索完成", fg="green"))
        click.echo(f"  结果数: {len(result.results)}")
        click.echo(f"  PDF: {result.metadata['pdf_path']}")
        click.echo(f"  JSON: {result.metadata['pdf_path'].replace('.pdf', '.json')}")
    except SearchError as e:
        click.echo(click.style(f"✗ 搜索失败: {e}", fg="red"), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 4.3 `__main__.py` 入口

```python
# src/google_search/__main__.py

from google_search.cli import main

if __name__ == "__main__":
    main()
```

---

## 5. 配置文件规范

### 5.1 config.yaml

```yaml
# config.yaml — 运行时配置

proxy:
  enabled: false
  pool:
    # 格式: http://user:pass@host:port
    # 第一期使用免费代理或留空（无代理模式）
    - http://proxy.free.example:8080

user_agents:
  - Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0

search_templates:
  # 预定义模板，实际使用时 {name} 会被替换为实体名称
  company:
    - '"{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约)'
  person:
    - '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕)'

output:
  directory: ./output
```

### 5.2 templates/default.yaml

```yaml
# templates/default.yaml — 搜索模板定义

company:
  - '"{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约)'
  - '"{name}" AND (调查 OR 处罚 OR 监管 OR 违规 OR 黑名单)'

person:
  - '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕)'
  - '"{name}" AND (受贿 OR 挪用 OR 潜逃 OR 被抓)'
```

### 5.3 环境变量覆盖

| 环境变量 | 影响的配置项 | 说明 |
|----------|--------------|------|
| `PROXY_URL` | `proxy.pool[0]` | 单个代理的快捷配置 |

**优先级**：`PROXY_URL` > `config.yaml` 中的 `proxy.pool`

---

## 6. 搜索流程时序

### 6.1 完整时序

```
用户
  │
  ▼
┌─────────────────────┐
│   python -m         │
│   google_search     │
│   "三鹿集团" company │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     cli.main()      │  ← Click 解析参数
│  Click Command      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Searcher.search()  │  ← 搜索流程开始
│                     │
│  ① 加载配置         │  ← config.py
│  ② 构造 Google URL  │  ← templates.py
│  ③ 构建查询字符串   │  ← templates.py
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   UA + 代理选取     │
│                     │
│  ua_pool.get_random │
│  proxy_pool.get     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  BrowserManager     │
│  .new_page()        │
│                     │
│  创建 Context       │
│  （含代理+UA）      │
│  创建 Page          │
│  注入 webdriver 脚本 │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  page.goto(url)    │  ← Playwright 网络请求
│  wait_until=       │
│  "domcontentloaded" │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CAPTCHA / 403 检测 │
│                     │
│  _is_captcha_page() │
│  url 包含 /sorry   │
└──────────┬──────────┘
           │ 正常
           ▼
┌─────────────────────┐
│  PDFGenerator       │
│  .wait_for_page_    │
│  ready()           │
│                     │
│  networkidle 等待   │
│  2秒额外 JS 渲染    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PDFGenerator       │
│  .generate()        │
│                     │
│  page.pdf()         │
│  → .pdf 文件        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  _parse_results()   │
│                     │
│  解析 DOM           │
│  → SearchResult[]   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  JSON 写入          │
│                     │
│  SearchTaskResult   │
│  → .json 文件       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Context 关闭       │
│  Browser 关闭       │
└──────────┬──────────┘
           │
           ▼
         返回
```

### 6.2 重试时序

```
首次尝试失败（403/CAPTCHA/超时）
           │
           ▼
    ┌──────────────┐
    │ attempt = 1  │  → MAX_RETRIES = 2
    └──────┬───────┘
           │
           ▼
    proxy_pool.rotate()   ← 换新代理
    ua_pool.get_random_not_in(used_uas)  ← 换新 UA
           │
           ▼
    新 BrowserContext（新代理+新UA）
           │
           ▼
    重试 page.goto()
           │
           ├─ 成功 → 继续 PDF+JSON 流程
           │
           └─ 失败
                  │
                  ▼
             attempt = 2
                  │
                  ├─ 再失败 → 抛出 SearchError，任务终止
                  │
                  └─ 成功 → 继续
```

---

## 7. 错误处理体系

### 7.1 异常类层次

```python
# src/google_search/exceptions.py

class GoogleSearchError(Exception):
    """基础异常，所有本项目异常的父类"""
    pass

class RecoverableError(GoogleSearchError):
    """
    可恢复错误，触发重试。
    包括：CAPTCHA、403、网络超时、页面加载失败
    """
    pass

class CaptchaError(RecoverableError):
    """Google 触发了 CAPTCHA"""
    pass

class ForbiddenError(RecoverableError):
    """Google 返回 403 / sorry 页面"""
    pass

class TimeoutError(RecoverableError):
    """页面加载或操作超时"""
    pass

class NonRecoverableError(GoogleSearchError):
    """
    不可恢复错误，不触发重试。
    包括：代理认证失败、配置错误
    """
    pass

class ProxyAuthError(NonRecoverableError):
    """代理认证失败"""
    pass

class SearchError(GoogleSearchError):
    """搜索任务整体失败（所有重试均失败）"""
    pass
```

### 7.2 错误处理策略矩阵

| 错误类型 | 抛出位置 | 是否可重试 | 重试动作 |
|----------|----------|------------|----------|
| `CaptchaError` | `searcher._execute_search()` | ✅ | 换代理 + 换 UA |
| `ForbiddenError` | `searcher._execute_search()` | ✅ | 换代理 + 换 UA |
| `TimeoutError` | `browser.new_page()` / `page.goto()` | ✅ | 换代理 |
| `page.goto() 抛出其他异常` | `browser.py` | ✅ | 换代理 + 换 UA |
| `ProxyAuthError` | `browser.new_context()` | ❌ | 直接失败 |
| `SearchError`（重试耗尽）| `searcher.search()` | ❌ | 最终失败 |

### 7.3 CLI 错误输出

```
$ python -m google_search "三鹿集团" company

正在初始化搜索任务: 三鹿集团 (company)
输出目录: ./output
正在搜索: "三鹿集团" AND (欺诈 OR 投诉 OR ...)
 尝试 1/3: 使用代理 http://proxy1.example.com:8080
✗ 搜索失败: Google 返回 403 (尝试 1/3)
 尝试 2/3: 切换代理 http://proxy2.example.com:8080
✗ 搜索失败: Google 触发了 CAPTCHA (尝试 2/3)
 尝试 3/3: 切换代理 http://proxy3.example.com:8080
✗ 搜索失败: 页面加载超时 (尝试 3/3)
✗ 搜索失败: 3次重试均失败，请检查网络和代理配置
提示: 设置 proxy.enabled: false 可禁用代理（开发模式）
```

---

## 8. PDF 生成机制

### 8.1 页面加载等待策略

Google 搜索结果是高度动态的页面（无限滚动、懒加载图片）。必须等待动态内容完全渲染后才能生成 PDF。

**三段式等待策略**：

```
page.goto(url, wait_until="domcontentloaded")
        │
        ▼
    ┌─────────────────────────────────┐
    │  第一阶段：networkidle 等待     │
    │  超时时间：30 秒                │
    │  等待所有网络请求完成            │
    └───────────────┬─────────────────┘
                    │
         触发 ──→ 继续（跳转第二步）
                    │
         超时 ──→ 第三阶段
                    │
        ┌───────────▼─────────────────┐
        │  第二阶段：额外 JS 等待      │
        │  固定等待：2 秒              │
        │  确保 React/JS 渲染完成      │
        └───────────┬─────────────────┘
                    │
        ┌───────────▼─────────────────┐
        │  第三阶段：超时兜底           │
        │  domcontentloaded + 5 秒等待  │
        │  如果第一阶段超时则执行此阶段 │
        └─────────────────────────────┘
```

### 8.2 page.pdf() 参数详解

```python
page.pdf(
    path=output_path,
    format="A4",                       # Google 搜索结果页面宽度 ~800px，A4 足够
    print_background=True,             # 关键：保留背景色和图片
    margin={
        "top": "0",
        "bottom": "0",
        "left": "0",
        "right": "0",
    },                                  # 消除白边
    scale=1.0,                          # 默认缩放
)
```

### 8.3 Google 搜索结果页面特性及处理

| 页面特性 | 对 PDF 生成的影响 | 解决方案 |
|----------|------------------|----------|
| 懒加载图片 | 图片可能未加载完成就截 PDF | `networkidle` + 2秒等待 |
| 无限滚动 | 页面高度不固定 | Google 实际只加载前 ~20 条，不需要滚动 |
| 动态内容闪烁 | 截图时内容跳变 | 2秒等待使动态内容稳定 |
| 固定 Header | 重复出现在每页 | A4 页面足够窄，第一页内容完整 |
| Cookie Banner | 可能遮挡内容 | 新 Context 无 Cookie，绕过 |

---

## 9. 反爬规避策略实现

### 9.1 四层防御体系

```
┌─────────────────────────────────────────────────────────────┐
│                    第 1 层：浏览器指纹                       │
│                                                             │
│  • Playwright 启动参数隐藏 webdriver 标志                   │
│  • add_init_script 覆盖 navigator.webdriver                 │
│  • 随机化窗口大小（可选）                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    第 2 层：User-Agent                       │
│                                                             │
│  • 维护 UA 池（5-10 个主流 UA）                             │
│  • 每次请求随机选取                                         │
│  • 重试时从不重复的 UA池中选取                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    第 3 层：代理 IP                          │
│                                                             │
│  • 代理池轮换，同一任务不重复使用同一 IP                     │
│  • 失败时立即切换新代理                                     │
│  • 无代理模式支持（开发/测试）                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    第 4 层：请求节奏                         │
│                                                             │
│  • 页面加载使用 domcontentloaded（不过度等待）              │
│  • 搜索间隔（后续扩展可加 random sleep）                    │
│  • networkidle 超时兜底机制                                 │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 代理认证

```python
# 代理 URL 格式支持
http://proxy.example.com:8080                    # 无认证
http://user:pass@proxy.example.com:8080         # 用户名密码认证

# Playwright proxy 配置
browser.new_context(
    proxy={
        "server": "http://proxy.example.com:8080",
        "username": "user",      # 可选
        "password": "pass",      # 可选
    }
)
```

### 9.3 IP 轮换不重复保证

```python
class ProxyPool:
    _used: set[str]  # 记录本次任务已用过的代理

    def rotate(self) -> str | None:
        # 找下一个不在 _used 中的代理
        # 如果所有代理都已用过，清空 _used 重置
```

### 9.4 Google 反爬机制识别

CAPTCHA / 403 页面识别：

```python
def _is_blocked_page(self, page: Page) -> bool:
    """检测是否被 Google 拦截"""
    content = page.content().lower()
    url = page.url.lower()

    # 1. /sorry 页面（手动验证）
    if "/sorry" in url:
        return True

    # 2. CAPTCHA 关键词
    if "captcha" in content or "unusual traffic" in content:
        return True

    # 3. 短标题（异常页面特征）
    if len(page.title()) < 5:
        return True

    return False
```

---

## 10. 测试策略

### 10.1 测试分层

```
┌────────────────────────────────────────┐
│         单元测试（Unit Tests）          │
│                                        │
│  • test_templates.py  — 模板解析        │
│  • test_ua_pool.py   — UA 选取逻辑     │
│  • test_proxy.py      — 代理轮换逻辑    │
│  • test_config.py     — 配置加载        │
│  • test_pdf.py        — PDF 参数验证    │
│                                        │
│  Mock: 不启动真实浏览器                 │
│  覆盖: 所有纯函数和类方法               │
└────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│        集成测试（Integration）          │
│                                        │
│  • test_searcher.py  — 完整搜索流程    │
│  • test_browser.py    — 浏览器生命周期  │
│                                        │
│  Mock: Mock BrowserManager              │
│  覆盖: searcher 编排逻辑               │
└────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│         端到端测试（E2E）               │
│                                        │
│  • tests/e2e/ — 完整用户流程           │
│                                        │
│  使用: 真实 Playwright + 真实/测试代理  │
│  覆盖: CLI 完整调用链                  │
└────────────────────────────────────────┘
```

### 10.2 单元测试示例

```python
# tests/test_templates.py

import pytest
from google_search.templates import (
    load_templates,
    build_search_query,
    build_google_url,
)

def test_load_templates():
    templates = load_templates()
    assert "company" in templates
    assert "person" in templates

def test_build_search_query_with_custom_template():
    query = build_search_query(
        "三鹿集团",
        "company",
        template='"{name}" AND (欺诈 OR 投诉)'
    )
    assert query == '"三鹿集团" AND (欺诈 OR 投诉)'

def test_build_search_query_without_template():
    query = build_search_query("三鹿集团", "company", template=None)
    assert "三鹿集团" in query
    assert "OR" in query

def test_build_google_url():
    url = build_google_url("三鹿集团 AND 欺诈")
    assert "q=" in url
    assert "hl=zh-CN" in url
    assert "gl=cn" in url

# tests/test_proxy.py

import pytest
from google_search.proxy import ProxyPool

def test_proxy_pool_basic():
    pool = ProxyPool(["http://proxy1.com:8080", "http://proxy2.com:8080"])

    p1 = pool.get()
    assert p1 == "http://proxy1.com:8080"
    assert pool.get() == "http://proxy1.com:8080"  # get 不移动指针

def test_proxy_pool_rotate():
    pool = ProxyPool(["http://proxy1.com:8080", "http://proxy2.com:8080"])

    pool.get()
    p2 = pool.rotate()
    assert p2 == "http://proxy2.com:8080"

def test_proxy_pool_exhausted():
    pool = ProxyPool(["http://proxy1.com:8080"])

    pool.get()
    pool.rotate()  # 用尽所有代理
    assert pool.exhausted

def test_proxy_pool_empty():
    pool = ProxyPool([])
    assert pool.get() is None
```

### 10.3 集成测试示例

```python
# tests/test_searcher.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from google_search.searcher import Searcher, SearchTaskResult

@pytest.fixture
def mock_browser_manager():
    with patch("google_search.searcher.BrowserManager") as m:
        mock_page = MagicMock()
        mock_page.title.return_value = "三鹿集团 - Google 搜索"
        mock_page.url = "https://www.google.com/search?q=..."
        mock_page.query_selector_all.return_value = [
            _make_mock_result_el("标题1", "http://example.com/1", "摘要1"),
            _make_mock_result_el("标题2", "http://example.com/2", "摘要2"),
        ]
        m.return_value.__enter__.return_value.new_page.return_value = mock_page
        yield m

def test_searcher_success(mock_browser_manager):
    searcher = Searcher()
    result = searcher.search("测试公司", "company")

    assert isinstance(result, SearchTaskResult)
    assert result.entity == "测试公司"
    assert result.entity_type == "company"
    assert len(result.results) == 2
    assert result.results[0].title == "标题1"
```

### 10.4 测试运行命令

```bash
# 所有测试
pytest

# 单个测试文件
pytest tests/test_searcher.py

# 带覆盖率
pytest --cov=src/google_search --cov-report=html

# E2E（需要代理配置）
pytest tests/e2e/ -v
```

---

## 11. 依赖与安装

### 11.1 pyproject.toml 详解

```toml
[project]
name = "google-search"
version = "0.1.0"
description = "Google search negative news crawler with headless browser"
requires-python = ">=3.10"

dependencies = [
    "playwright>=1.40.0",   # 浏览器自动化
    "pyyaml>=6.0",           # YAML 配置解析
    "click>=8.1.0",          # CLI 框架
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",                     # 测试框架
    "pytest-playwright>=0.4.0",          # Playwright pytest 集成
    "pytest-cov>=4.0.0",                 # 覆盖率
    "ruff>=0.1.0",                       # Linter
]

# CLI 入口点
[project.scripts]
google-search = "google_search.cli:main"

# 工具配置
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # 行长度由 ruff 管理
```

### 11.2 安装步骤

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\activate  # Windows

# 2. 安装项目及开发依赖
pip install -e ".[dev]"

# 3. 安装 Playwright 浏览器
playwright install chromium

# 或使用自定义命令
/build
```

### 11.3 依赖版本兼容性

| 依赖 | 最低版本 | 推荐版本 | 说明 |
|------|----------|----------|------|
| Python | 3.10 | 3.11+ | 支持结构化绑定 `case` 语法 |
| playwright | 1.40.0 | 1.44+ | 最新版对 Chromium 优化更好 |
| pyyaml | 6.0 | 6.0.1 | 安全修复版本 |
| click | 8.1.0 | 8.1.7 | 最新版修复了一些 bug |

---

## 12. 目录结构规范

### 12.1 完整目录树

```
google-search/
│
├── # 项目元数据
├── CLAUDE.md                    # Claude Code 工作指南
├── README.md                    # 项目说明
├── pyproject.toml               # Python 项目配置（PEP 621）
├── requirements.txt             # pip freeze 输出（与 pyproject.toml 同步）
├── uv.lock                      # uv 依赖锁定（可选）
├── .gitignore                   # Git 忽略规则
├── .env.example                 # 环境变量模板
│
├── # 源代码
├── src/
│   └── google_search/            # 主包（命名空间避免与 google 包冲突）
│       ├── __init__.py          # 包初始化（版本号暴露）
│       ├── __main__.py          # python -m google_search 入口
│       │
│       ├── cli.py               # Click CLI（入口参数解析）
│       ├── config.py            # YAML 配置加载 + 环境变量覆盖
│       ├── exceptions.py        # 异常类层次定义
│       ├── models.py            # 数据类（SearchResult, SearchTaskResult）
│       │
│       ├── browser.py           # Playwright BrowserManager 单例
│       ├── searcher.py          # 搜索流程编排（核心业务逻辑）
│       ├── pdf.py               # PDFGenerator 页面等待 + 生成
│       ├── proxy.py             # ProxyPool 代理轮换管理
│       ├── ua_pool.py           # UAPool UA 随机选取
│       └── templates.py         # 搜索模板加载 + URL 构造
│
├── # 配置与模板
├── config.yaml                  # 运行时配置（代理、UA池、输出目录）
├── templates/
│   └── default.yaml             # 预定义搜索模板（公司/个人）
│
├── # 文档
├── docs/
│   ├── raw/                     # 原始资料（操作指南 PDF）
│   │   └── Google search负面新闻排查操作指南.pdf
│   ├── REQUIREMENTS.md           # 需求文档
│   ├── DESIGN.md                 # 技术设计文档
│   ├── PRD.md                    # 产品需求文档
│   └── ARCHITECTURE.md           # 本文档
│
├── # 输出（不提交 git）
└── output/                       # PDF + JSON 结果输出目录
    # *.pdf
    # *.json
│
├── # 测试
└── tests/
    ├── __init__.py
    ├── test_templates.py         # 模板模块单元测试
    ├── test_ua_pool.py           # UA 池单元测试
    ├── test_proxy.py             # 代理池单元测试
    ├── test_config.py            # 配置加载单元测试
    ├── test_searcher.py          # 搜索流程集成测试
    └── test_browser.py           # 浏览器生命周期测试
```

### 12.2 模块导入规则

```
cli.py          可导入: config, searcher, exceptions
config.py       可导入: (无业务模块依赖)
exceptions.py   可导入: (无依赖)
models.py       可导入: (无依赖)

searcher.py     可导入: config, browser, pdf, proxy, ua_pool, templates, models, exceptions
browser.py      可导入: (无业务模块依赖，仅 Playwright)
pdf.py          可导入: (无业务模块依赖)
proxy.py        可导入: config
ua_pool.py      可导入: config
templates.py    可导入: (无业务模块依赖)
```

### 12.3 `__init__.py` 内容

```python
# src/google_search/__init__.py

__version__ = "0.1.0"

from google_search.exceptions import (
    GoogleSearchError,
    RecoverableError,
    SearchError,
    CaptchaError,
    ForbiddenError,
    TimeoutError,
)

from google_search.models import (
    SearchResult,
    SearchTaskResult,
)

__all__ = [
    "__version__",
    "GoogleSearchError",
    "RecoverableError",
    "SearchError",
    "CaptchaError",
    "ForbiddenError",
    "TimeoutError",
    "SearchResult",
    "SearchTaskResult",
]
```

---

## 13. 开发工作流

### 13.1 开发节奏

```
第 1 天：项目脚手架
  ├── pyproject.toml + 依赖安装
  ├── Playwright 浏览器安装
  ├── 目录结构创建
  └── config.yaml + templates/default.yaml

第 2 天：基础设施模块
  ├── exceptions.py
  ├── models.py
  ├── config.py
  ├── ua_pool.py
  ├── proxy.py
  └── templates.py

第 3 天：核心功能模块
  ├── browser.py（BrowserManager）
  ├── pdf.py（PDFGenerator）
  └── searcher.py（Searcher 编排）

第 4 天：CLI + 集成
  ├── cli.py
  ├── __main__.py
  └── 端到端联调

第 5 天：测试 + 文档
  ├── 单元测试覆盖
  ├── 集成测试
  └── README.md 完善
```

### 13.2 代码规范

**格式化**：
```bash
# ruff 自动格式化
ruff format .

# 检查
ruff check .
ruff check --fix .  # 自动修复
```

**类型注解**：
- 所有公开函数必须有类型注解
- 内部函数推荐有类型注解

```python
def build_google_url(query: str, hl: str = "zh-CN", gl: str = "cn") -> str:
    ...
```

### 13.3 提交规范

```
<type>(<scope>): <subject>

Types:
  feat: 新功能
  fix: Bug 修复
  refactor: 重构（无功能变化）
  test: 测试相关
  docs: 文档相关
  chore: 构建/工具变更

Examples:
  feat(searcher): 添加重试逻辑和 CAPTCHA 检测
  fix(proxy): 修复代理池耗尽后 rotate 返回 None 问题
  test(templates): 添加 build_google_url 单元测试
  docs(architecture): 补充 PDF 生成机制文档
```

### 13.4 Playwright 安装问题排查

```bash
# 检查浏览器是否安装
playwright install --dry-run chromium

# 强制重新安装
playwright install chromium --force

# 检查依赖（Linux）
playwright install-deps chromium
```

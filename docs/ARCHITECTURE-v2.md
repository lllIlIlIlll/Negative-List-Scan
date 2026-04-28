# 技术架构设计文档（v2）

**文档版本**：v2.0
**日期**：2026-04-28
**关联文档**：`PRD-v2.md`
**取代**：v1 代理/UA 轮换架构文档

---

## 0. v2 修订说明

v1 ARCHITECTURE 围绕"反爬 + 代理池"展开，约 60% 的篇幅在描述代理轮换、UA 池、stealth 注入、CAPTCHA 检测等内容。v2 PRD 重新定位为"浏览器自动化取证工具"，本文档据此重写。

**核心架构变化**：

1. **删除模块**：`proxy.py`、`ua_pool.py`
2. **重写模块**：`browser.py`（持久化 context + 真实 Chrome）、`pdf.py`（CDP 调用）
3. **简化模块**：`searcher.py`（移除轮换重试逻辑）、`exceptions.py`（异常类型从 7 个降到 3 个）
4. **新增模块**：`parser.py`（从 `searcher` 拆出的 best-effort DOM 解析器）
5. **新增机制**：取证完整性（SHA-256、UTC 时间、HTML/截图兜底）、用户介入流程（reCAPTCHA 等待）

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [模块设计](#2-模块设计)
3. [数据模型](#3-数据模型)
4. [CLI 接口规范](#4-cli-接口规范)
5. [配置文件规范](#5-配置文件规范)
6. [搜索流程时序](#6-搜索流程时序)
7. [错误处理体系](#7-错误处理体系)
8. [PDF 生成机制（CDP 实现）](#8-pdf-生成机制cdp-实现)
9. [取证完整性保障](#9-取证完整性保障)
10. [测试策略](#10-测试策略)
11. [依赖与安装](#11-依赖与安装)
12. [目录结构规范](#12-目录结构规范)
13. [v1 → v2 迁移清单](#13-v1--v2-迁移清单)

---

## 1. 系统架构概览

### 1.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                     1. CLI 接入层                            │
│                       cli.py                                 │
│       Click Group: search / login / profile-status           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    2. 配置层                                 │
│                  config.py / templates.py                    │
│           YAML 加载（依赖注入，无模块级单例）                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  3. 浏览器层                                 │
│                    browser.py                                │
│        Persistent Chrome Context + CDP Session               │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                 4. 搜索流程层                                │
│                   searcher.py                                │
│      多模板顺序执行 + 间隔等待 + 用户介入处理                │
└──────────┬─────────────────────────────────────┬────────────┘
           │                                     │
┌──────────▼──────────┐                ┌─────────▼──────────┐
│   5a. 输出层（必需） │                │  5b. 解析层（可选）│
│        pdf.py        │                │     parser.py      │
│  CDP printToPDF +    │                │  best-effort DOM   │
│  HTML 快照 + 截图    │                │  解析（多套选择器）│
│  + SHA-256 计算      │                │  失败不抛异常      │
└──────────────────────┘                └────────────────────┘
```

**关键变化**（与 v1 对比）：

- 第 3 层从"独立资源池层（proxy + ua_pool）"消失
- 第 5 层从"PDF 输出"变为"PDF 输出（必需） + 解析（可选）"两条独立路径
- `browser.py` 的角色从"全新匿名 context 工厂"变为"持久化用户 profile 管理者"

### 1.2 模块依赖关系

```
cli.py
  ├── config.py           # 加载配置
  ├── searcher.py
  │     ├── browser.py    # 启动浏览器
  │     ├── templates.py  # 构造查询
  │     ├── pdf.py        # 保存 PDF（必需）
  │     ├── parser.py     # 解析结果（best-effort）
  │     ├── models.py     # dataclass
  │     └── exceptions.py # 异常类型
  └── exceptions.py
```

**依赖规则**：

- 上层可导入下层，下层不可导入上层
- 同层模块不直接互相导入（避免循环依赖）
- `config.py`、`models.py`、`exceptions.py` 无业务依赖

---

## 2. 模块设计

### 2.1 `config.py` — 配置加载（依赖注入）

**修复 v1 bug**：v1 使用模块级单例 `config = Config()`，导致 CLI 的 `--config` 参数无法生效（`cli.py` 中 `config = Config(config_path)` 只创建局部变量）。v2 改为显式依赖注入。

```python
# src/google_search/config.py

from dataclasses import dataclass, field
from pathlib import Path
import os
import yaml


@dataclass
class BrowserConfig:
    channel: str = "chrome"
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 900


@dataclass
class SearchConfig:
    hl: str = "zh-CN"
    gl: str = "cn"
    inter_query_delay_seconds: tuple[int, int] = (5, 15)
    page_load_timeout_seconds: int = 30
    network_idle_timeout_seconds: int = 30
    captcha_wait_seconds: int = 120


@dataclass
class TemplateEntry:
    id: str
    template: str


@dataclass
class OutputConfig:
    directory: Path
    save_html: bool = True
    save_screenshot: bool = True


@dataclass
class Config:
    profile_path: Path
    browser: BrowserConfig
    search: SearchConfig
    templates: dict[str, list[TemplateEntry]]
    output: OutputConfig

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Config":
        """从 YAML 加载配置，应用环境变量覆盖。"""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

        profile_path = Path(
            os.environ.get("GOOGLE_SEARCH_PROFILE")
            or data["profile"]["path"]
        ).expanduser()

        output_dir = Path(
            os.environ.get("GOOGLE_SEARCH_OUTPUT_DIR")
            or data["output"]["directory"]
        ).expanduser()

        return cls(
            profile_path=profile_path,
            browser=BrowserConfig(**data.get("browser", {})),
            search=SearchConfig(**_normalize_search(data.get("search", {}))),
            templates={
                kind: [TemplateEntry(**e) for e in entries]
                for kind, entries in data.get("search_templates", {}).items()
            },
            output=OutputConfig(
                directory=output_dir,
                save_html=data.get("output", {}).get("save_html", True),
                save_screenshot=data.get("output", {}).get("save_screenshot", True),
            ),
        )


def _normalize_search(raw: dict) -> dict:
    # 把 list[int] 转成 tuple
    if "inter_query_delay_seconds" in raw:
        raw["inter_query_delay_seconds"] = tuple(raw["inter_query_delay_seconds"])
    return raw
```

**使用方式**：

```python
from google_search.config import Config

cfg = Config.load("config.yaml")
searcher = Searcher(cfg)   # 显式注入，可被 mock
```

### 2.2 `templates.py` — 多模板查询构造

**修复 v1 bug**：v1 用 ` OR ` 拼接所有模板成单条查询，会触发 Google 查询长度限制 + 运算优先级问题。v2 改为返回独立查询列表。

```python
# src/google_search/templates.py

import urllib.parse
from dataclasses import dataclass
from google_search.config import TemplateEntry


@dataclass
class Query:
    template_id: str
    query_text: str
    google_url: str


def build_queries(
    entity: str,
    entity_type: str,
    templates: dict[str, list[TemplateEntry]],
    custom_template: str | None = None,
    hl: str = "zh-CN",
    gl: str = "cn",
) -> list[Query]:
    """构造一组独立的查询。

    - 如果传入 custom_template，只返回一条查询（id 固定为 "custom"）
    - 否则按 entity_type 返回该类型的全部模板的独立查询
    """
    if custom_template:
        entries = [TemplateEntry(id="custom", template=custom_template)]
    else:
        entries = templates.get(entity_type, [])
        if not entries:
            raise ValueError(f"未找到实体类型 {entity_type} 的模板")

    queries: list[Query] = []
    for entry in entries:
        text = entry.template.replace("{name}", entity)
        url = _build_google_url(text, hl=hl, gl=gl)
        queries.append(Query(template_id=entry.id, query_text=text, google_url=url))
    return queries


def _build_google_url(query: str, hl: str, gl: str) -> str:
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/search?q={encoded}&hl={hl}&gl={gl}"
```

### 2.3 `browser.py` — 持久化 Chrome 管理

**核心变化**：从"启动新 Chromium 进程，每次新 context 注入 stealth"，变为"启动绑定用户 profile 的 Chrome，复用真实浏览器身份"。

```python
# src/google_search/browser.py

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import sync_playwright, BrowserContext, Page

from google_search.config import BrowserConfig
from google_search.exceptions import FatalError


class PersistentBrowser:
    """绑定独立 profile 的 Chrome 浏览器。

    每次任务启动一次浏览器，任务结束后关闭并保留 profile。
    """

    def __init__(self, profile_path: Path, browser_config: BrowserConfig):
        self.profile_path = profile_path
        self.config = browser_config
        self._playwright = None
        self._context: BrowserContext | None = None

    @contextmanager
    def session(self) -> Iterator[BrowserContext]:
        """上下文管理器，启动浏览器 + 自动清理。"""
        self.profile_path.mkdir(parents=True, exist_ok=True)
        # 设置目录权限为 0700（仅限 *nix）
        try:
            self.profile_path.chmod(0o700)
        except (OSError, NotImplementedError):
            pass

        self._playwright = sync_playwright().start()
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_path),
                channel=self.config.channel,
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                accept_downloads=True,
                args=[
                    # 不再注入 disable-blink-features=AutomationControlled
                    # 因为我们用的就是用户真实 Chrome，不需要伪装
                ],
            )
            yield self._context
        except Exception as e:
            # profile 锁定错误的特征：通常是 "ProcessSingleton" 或 "lock file"
            if "ProcessSingleton" in str(e) or "lock" in str(e).lower():
                raise FatalError(
                    f"profile 已被另一个 Chrome 实例占用：{self.profile_path}"
                ) from e
            raise
        finally:
            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()

    def new_page(self) -> Page:
        """在现有 context 中创建新 page。"""
        if self._context is None:
            raise RuntimeError("必须在 session() 上下文内调用 new_page()")
        return self._context.new_page()
```

**关键设计点**：

- 使用 `channel="chrome"`，调用用户系统已安装的 Chrome（而非 Playwright bundled Chromium）。需要用户机器装了 Chrome；未安装时启动会报错，CLI 应预检并提示安装。
- 不再注入 `navigator.webdriver` 隐藏脚本——用真实 Chrome 时这些指纹都已经是真的。
- profile 目录权限设为 `0700`，避免本机其他用户读取登录 cookie。

### 2.4 `pdf.py` — 通过 CDP 生成 PDF

**关键技术点**：Playwright 的 `page.pdf()` **只支持 headless Chromium**，不支持 headed 模式或 `channel="chrome"`。v2 默认 headed，必须改用 CDP `Page.printToPDF`。

```python
# src/google_search/pdf.py

import base64
import hashlib
from pathlib import Path
from playwright.sync_api import Page


def save_pdf(page: Page, output_path: Path) -> tuple[Path, str, int]:
    """通过 CDP 生成 PDF。

    Returns:
        (路径, SHA-256 十六进制字符串, 字节数)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = page.context.new_cdp_session(page)
    result = client.send(
        "Page.printToPDF",
        {
            "printBackground": True,
            "preferCSSPageSize": False,
            "paperWidth": 8.27,    # A4 inches
            "paperHeight": 11.69,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "scale": 1.0,
            "displayHeaderFooter": False,
        },
    )

    pdf_bytes = base64.b64decode(result["data"])
    output_path.write_bytes(pdf_bytes)

    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    return output_path, sha256, len(pdf_bytes)


def save_html_snapshot(page: Page, output_path: Path) -> tuple[Path, str]:
    """保存当前页面 HTML 内容。返回 (路径, sha256)。"""
    html = page.content()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    sha256 = hashlib.sha256(html.encode("utf-8")).hexdigest()
    return output_path, sha256


def save_screenshot(page: Page, output_path: Path) -> Path:
    """全页面截图（兜底证据）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output_path), full_page=True)
    return output_path


def wait_for_page_ready(
    page: Page,
    network_idle_timeout_ms: int = 30_000,
    fallback_wait_ms: int = 3_000,
) -> int:
    """三段式等待。返回实际等待毫秒数（用于 metadata）。"""
    import time
    start = time.time()
    try:
        page.wait_for_load_state("networkidle", timeout=network_idle_timeout_ms)
        page.wait_for_timeout(2_000)
    except Exception:
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(fallback_wait_ms)
    return int((time.time() - start) * 1000)
```

### 2.5 `parser.py` — best-effort DOM 解析

**新增模块**。从 `searcher._parse_search_results` 拆出，明确"失败不抛异常、PDF 优先"的语义。

```python
# src/google_search/parser.py

from dataclasses import dataclass
from playwright.sync_api import Page

from google_search.models import SearchResult


# 多套选择器策略，按可靠性递减排列
_RESULT_SELECTORS = [
    "div.g",                  # 经典选择器（已不稳定）
    "div[data-snhf]",         # 部分页面
    "div[data-async-context]",
    "div.MjjYud",             # 当前主流（2024 年）
]


def parse_search_results(page: Page) -> tuple[list[SearchResult], str]:
    """解析搜索结果。

    Returns:
        (结果列表, 状态: "success" | "partial" | "failed")
    """
    results: list[SearchResult] = []
    used_selector: str | None = None

    for selector in _RESULT_SELECTORS:
        elements = page.query_selector_all(selector)
        if not elements:
            continue
        used_selector = selector
        for i, el in enumerate(elements):
            r = _try_parse_one(el, rank=i + 1)
            if r:
                results.append(r)
        if results:
            break

    if not used_selector:
        return [], "failed"
    if len(results) < 3:
        # 几乎没解析到，标记为部分失败
        return results, "partial"
    return results, "success"


def _try_parse_one(el, rank: int) -> SearchResult | None:
    try:
        title_el = el.query_selector("h3")
        if not title_el:
            return None
        title = title_el.inner_text()

        link_el = el.query_selector("a[href^='http']")
        url = link_el.get_attribute("href") if link_el else ""

        # 摘要选择器多套尝试
        snippet = ""
        for snippet_sel in ["div[data-sncf]", "div.VwiC3b", "span.aCOpRe"]:
            snippet_el = el.query_selector(snippet_sel)
            if snippet_el:
                snippet = snippet_el.inner_text()
                break

        return SearchResult(
            rank=rank, title=title, url=url, snippet=snippet,
            source="", date="",
        )
    except Exception:
        return None
```

**关键约定**：

- 任何异常都被吞掉（返回 None / 空列表）
- 状态字段（`success` / `partial` / `failed`）写入 JSON metadata，方便事后审计
- DOM 选择器列表会持续维护，但即使过时也只影响 JSON，不影响 PDF

### 2.6 `searcher.py` — 简化的搜索编排

```python
# src/google_search/searcher.py

import json
import random
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page

from google_search.browser import PersistentBrowser
from google_search.config import Config
from google_search.exceptions import FatalError, RecoverableError, UserActionRequired
from google_search.models import (
    EvidenceMetadata, SearchResult, SearchTaskResult, TemplateRunResult,
)
from google_search.pdf import (
    save_pdf, save_html_snapshot, save_screenshot, wait_for_page_ready,
)
from google_search.parser import parse_search_results
from google_search.templates import Query, build_queries


class Searcher:
    def __init__(self, config: Config):
        self.config = config
        self.browser = PersistentBrowser(config.profile_path, config.browser)

    def search(
        self,
        entity: str,
        entity_type: str,
        custom_template: str | None = None,
    ) -> SearchTaskResult:
        queries = build_queries(
            entity, entity_type, self.config.templates, custom_template,
            hl=self.config.search.hl, gl=self.config.search.gl,
        )

        runs: list[TemplateRunResult] = []
        with self.browser.session() as ctx:
            for i, query in enumerate(queries):
                if i > 0:
                    delay = random.uniform(*self.config.search.inter_query_delay_seconds)
                    time.sleep(delay)
                run = self._run_one_query(ctx, entity, entity_type, query)
                runs.append(run)

        return SearchTaskResult(
            entity=entity,
            entity_type=entity_type,
            template_runs=runs,
        )

    def _run_one_query(
        self, ctx, entity: str, entity_type: str, query: Query,
    ) -> TemplateRunResult:
        page = ctx.new_page()
        try:
            return self._execute(page, entity, entity_type, query)
        finally:
            page.close()

    def _execute(
        self, page: Page, entity: str, entity_type: str, query: Query,
    ) -> TemplateRunResult:
        searched_at_utc = datetime.now(timezone.utc)
        timestamp = searched_at_utc.strftime("%Y%m%dT%H%M%SZ")
        safe_name = _sanitize_filename(entity)
        prefix = f"{safe_name}_{query.template_id}_{timestamp}"
        out_dir = self.config.output.directory

        had_user_interaction = False

        # 1. 访问页面
        try:
            page.goto(
                query.google_url,
                wait_until="domcontentloaded",
                timeout=self.config.search.page_load_timeout_seconds * 1000,
            )
        except Exception as e:
            return _error_run(query, searched_at_utc, f"页面加载失败: {e}")

        # 2. 检测 reCAPTCHA / sorry 页面
        if _is_blocked(page):
            if self.config.browser.headless:
                return _error_run(
                    query, searched_at_utc,
                    "headless 模式下触发 Google 验证，无法人工介入。"
                    "请移除 --headless 或重新登录。",
                )
            # headed: 等待用户手动通过
            had_user_interaction = True
            print(f"\n⚠ 检测到 Google 验证页，请在浏览器中手动通过…")
            try:
                _wait_for_unblock(page, self.config.search.captcha_wait_seconds)
            except TimeoutError:
                return _error_run(
                    query, searched_at_utc, "用户未在规定时间内通过验证",
                )

        # 3. 等页面就绪
        page_load_ms = wait_for_page_ready(
            page,
            network_idle_timeout_ms=self.config.search.network_idle_timeout_seconds * 1000,
        )

        # 4. 保存 PDF（必需）
        pdf_path, pdf_sha, pdf_bytes = save_pdf(page, out_dir / f"{prefix}.pdf")

        # 5. 保存 HTML / 截图（可选）
        html_path = html_sha = None
        if self.config.output.save_html:
            html_path, html_sha = save_html_snapshot(page, out_dir / f"{prefix}.html")
        screenshot_path = None
        if self.config.output.save_screenshot:
            screenshot_path = save_screenshot(page, out_dir / f"{prefix}.png")

        # 6. 解析（best-effort）
        results, parse_status = parse_search_results(page)

        # 7. 写 JSON
        run = TemplateRunResult(
            template_id=query.template_id,
            search_template=query.query_text,
            search_url=query.google_url,
            searched_at_utc=searched_at_utc.isoformat().replace("+00:00", "Z"),
            searched_at_local=datetime.now().astimezone().isoformat(),
            evidence=EvidenceMetadata(
                pdf_path=str(pdf_path),
                pdf_sha256=pdf_sha,
                pdf_bytes=pdf_bytes,
                html_path=str(html_path) if html_path else None,
                html_sha256=html_sha,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
            ),
            results=results,
            results_parse_status=parse_status,
            page_load_ms=page_load_ms,
            had_user_interaction=had_user_interaction,
            error=None,
        )
        _write_json(out_dir / f"{prefix}.json", entity, entity_type, run, page)
        return run


# ---------- 辅助函数 ----------

def _is_blocked(page: Page) -> bool:
    """检测当前页面是否为 Google 拦截页。"""
    if "/sorry/" in page.url:
        return True
    # 探测验证码表单
    if page.query_selector("form#captcha-form"):
        return True
    return False


def _wait_for_unblock(page: Page, timeout_seconds: int) -> None:
    """等待用户手动通过验证页。"""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _is_blocked(page):
            return
        time.sleep(2)
    raise TimeoutError("用户未及时通过验证")


def _sanitize_filename(name: str) -> str:
    import re
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def _error_run(query, searched_at_utc, message) -> "TemplateRunResult":
    return TemplateRunResult(
        template_id=query.template_id,
        search_template=query.query_text,
        search_url=query.google_url,
        searched_at_utc=searched_at_utc.isoformat().replace("+00:00", "Z"),
        searched_at_local=datetime.now().astimezone().isoformat(),
        evidence=None,
        results=[],
        results_parse_status="failed",
        page_load_ms=0,
        had_user_interaction=False,
        error=message,
    )


def _write_json(path, entity, entity_type, run, page):
    payload = {
        "entity": entity,
        "entity_type": entity_type,
        "template_id": run.template_id,
        "search_template": run.search_template,
        "search_url": run.search_url,
        "searched_at_utc": run.searched_at_utc,
        "searched_at_local": run.searched_at_local,
        "browser": {
            "channel": page.context.browser.browser_type.name if page.context.browser else "chrome",
            "user_agent": page.evaluate("navigator.userAgent"),
            "viewport": page.viewport_size,
        },
        "evidence": asdict(run.evidence) if run.evidence else None,
        "results": [asdict(r) for r in run.results],
        "results_parse_status": run.results_parse_status,
        "metadata": {
            "page_load_ms": run.page_load_ms,
            "had_user_interaction": run.had_user_interaction,
            "error": run.error,
        },
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
    )
```

### 2.7 `exceptions.py` — 简化异常体系

```python
# src/google_search/exceptions.py

class GoogleSearchError(Exception):
    """基类。"""


class UserActionRequired(GoogleSearchError):
    """需要用户手动介入（首次登录、reCAPTCHA 超时等）。"""


class RecoverableError(GoogleSearchError):
    """可重试的临时错误（网络抖动、超时）。"""


class FatalError(GoogleSearchError):
    """不可恢复错误（profile 锁定、Chrome 未安装、配置错误）。"""
```

**对比 v1**：删除 `CaptchaError`、`ForbiddenError`、`ProxyAuthError`、`TimeoutError`、`SearchError`、`NonRecoverableError` 这些不再使用的细分类型。

---

## 3. 数据模型

```python
# src/google_search/models.py

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    rank: int
    title: str
    url: str
    snippet: str
    source: str = ""
    date: str = ""


@dataclass
class EvidenceMetadata:
    pdf_path: str
    pdf_sha256: str
    pdf_bytes: int
    html_path: str | None = None
    html_sha256: str | None = None
    screenshot_path: str | None = None


@dataclass
class TemplateRunResult:
    """单次模板搜索的结果。"""
    template_id: str
    search_template: str
    search_url: str
    searched_at_utc: str
    searched_at_local: str
    evidence: EvidenceMetadata | None
    results: list[SearchResult]
    results_parse_status: str   # "success" | "partial" | "failed"
    page_load_ms: int
    had_user_interaction: bool
    error: str | None = None


@dataclass
class SearchTaskResult:
    """一次完整任务（多模板）的结果。"""
    entity: str
    entity_type: str
    template_runs: list[TemplateRunResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.template_runs if r.error is None)

    @property
    def total_count(self) -> int:
        return len(self.template_runs)
```

---

## 4. CLI 接口规范

```python
# src/google_search/cli.py

import sys
from pathlib import Path

import click

from google_search.config import Config
from google_search.searcher import Searcher
from google_search.exceptions import FatalError, UserActionRequired


@click.group()
@click.option("-c", "--config", "config_path", default="config.yaml")
@click.pass_context
def cli(ctx, config_path):
    """Google 负面新闻取证工具。"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.load(config_path)


@cli.command()
@click.argument("entity")
@click.argument("entity_type", type=click.Choice(["company", "person"]))
@click.option("-t", "--template", "custom_template", default=None)
@click.option("--headless/--no-headless", default=None)
@click.option("--profile", "profile_path", default=None)
@click.option("-o", "--output-dir", default=None)
@click.option("--no-html", is_flag=True)
@click.option("--no-screenshot", is_flag=True)
@click.pass_context
def search(ctx, entity, entity_type, custom_template, headless,
           profile_path, output_dir, no_html, no_screenshot):
    """执行单实体负面新闻搜索。"""
    cfg = ctx.obj["config"]

    # 命令行选项覆盖配置
    if headless is not None:
        cfg.browser.headless = headless
    if profile_path:
        cfg.profile_path = Path(profile_path).expanduser()
    if output_dir:
        cfg.output.directory = Path(output_dir)
    if no_html:
        cfg.output.save_html = False
    if no_screenshot:
        cfg.output.save_screenshot = False

    # 预检 profile
    if not cfg.profile_path.exists():
        click.echo(click.style(
            f"✗ profile 不存在：{cfg.profile_path}", fg="red"
        ))
        click.echo("提示: 请先运行 `google-search login` 完成首次登录配置")
        sys.exit(2)

    searcher = Searcher(cfg)
    try:
        result = searcher.search(entity, entity_type, custom_template)
    except FatalError as e:
        click.echo(click.style(f"✗ {e}", fg="red"), err=True)
        sys.exit(2)

    _print_summary(result)
    sys.exit(0 if result.success_count == result.total_count else 1)


@cli.command()
@click.pass_context
def login(ctx):
    """启动有头 Chrome 让用户登录 Google。"""
    cfg = ctx.obj["config"]
    cfg.browser.headless = False   # 强制有头

    from google_search.browser import PersistentBrowser
    browser = PersistentBrowser(cfg.profile_path, cfg.browser)

    click.echo(f"启动 Chrome，profile: {cfg.profile_path}")
    click.echo("请在浏览器中：")
    click.echo("  1. 登录 Google 账号")
    click.echo("  2. 关闭 cookie banner 和无关弹窗")
    click.echo("  3. 完成后回到终端按 Enter")
    with browser.session() as ctx_:
        page = ctx_.new_page()
        page.goto("https://www.google.com")
        click.prompt("完成后按 Enter 关闭浏览器", default="", show_default=False)


@cli.command("profile-status")
@click.pass_context
def profile_status(ctx):
    """显示 profile 状态。"""
    cfg = ctx.obj["config"]
    p = cfg.profile_path
    if not p.exists():
        click.echo(f"profile 不存在: {p}")
        return
    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    click.echo(f"profile 路径: {p}")
    click.echo(f"占用空间: {size / 1024 / 1024:.1f} MB")


def _print_summary(result):
    click.echo()
    click.echo(f"完成: {result.success_count}/{result.total_count} 成功")
    for run in result.template_runs:
        if run.error:
            click.echo(click.style(f"  ✗ {run.template_id}: {run.error}", fg="red"))
        else:
            click.echo(click.style(
                f"  ✓ {run.template_id}: {run.evidence.pdf_path}", fg="green"
            ))


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
```

---

## 5. 配置文件规范

### 5.1 `config.yaml`

见 `PRD-v2.md` 第 3.6 节。完整示例：

```yaml
profile:
  path: ~/.local/share/google_search/profile

browser:
  channel: chrome
  headless: false
  viewport:
    width: 1280
    height: 900

search:
  hl: zh-CN
  gl: cn
  inter_query_delay_seconds: [5, 15]
  page_load_timeout_seconds: 30
  network_idle_timeout_seconds: 30
  captcha_wait_seconds: 120

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

### 5.2 环境变量

| 变量 | 作用 |
|------|------|
| `GOOGLE_SEARCH_PROFILE` | 覆盖 profile 路径 |
| `GOOGLE_SEARCH_OUTPUT_DIR` | 覆盖输出目录 |

优先级：环境变量 > `--option` 命令行 > `config.yaml` > 内置默认值

---

## 6. 搜索流程时序

```
用户调用
   │
   ▼
cli search "三鹿集团" company
   │
   ▼
Config.load()                      ← 读 YAML，应用环境变量
   │
   ▼
Searcher(config)
   │
   ▼
build_queries()                     ← 返回 N 条独立查询
   │
   ▼
PersistentBrowser.session():        ← 启动一次 Chrome（绑定 profile）
   │
   ├─ for query in queries:
   │   │
   │   ├─ if not first: sleep(random 5-15s)   ← 模拟人工节奏
   │   │
   │   ├─ ctx.new_page()
   │   ├─ page.goto(url)
   │   │
   │   ├─ if blocked (sorry/captcha):
   │   │   ├─ headless: 立即标记错误，跳过
   │   │   └─ headed: 等用户手动通过（最多 120s）
   │   │
   │   ├─ wait_for_page_ready()
   │   │
   │   ├─ save_pdf()        ← CDP printToPDF（必需）
   │   ├─ save_html_snapshot()  (可选)
   │   ├─ save_screenshot()     (可选)
   │   │
   │   ├─ parse_search_results() ← best-effort
   │   │
   │   ├─ write JSON metadata
   │   │
   │   └─ page.close()
   │
   └─ context close + Playwright stop
   │
   ▼
return SearchTaskResult
```

---

## 7. 错误处理体系

### 7.1 错误分类与处理

| 错误情况 | 异常类型 | 处理方式 | 退出码 |
|---------|---------|---------|--------|
| Chrome 未安装 | `FatalError` | 启动前预检，打印安装指引 | 2 |
| profile 已被锁定 | `FatalError` | 立即终止任务 | 2 |
| 配置文件错误 | 普通 Exception | Click 自动处理 | 2 |
| profile 不存在（需登录） | 无异常，CLI 检查 | 提示运行 `login` | 2 |
| 网络超时 | 内部捕获 | 该模板标记失败，继续下一个 | 1 |
| reCAPTCHA（headed） | 无异常 | 等用户手动通过 | 0 / 1 |
| reCAPTCHA（headless） | 内部捕获 | 该模板标记失败 | 1 |
| DOM 解析失败 | 无异常 | `parse_status="failed"`，PDF 仍输出 | 0 |
| 用户未在 120s 内通过验证 | 内部捕获 | 该模板标记失败 | 1 |

### 7.2 退出码语义

- `0`：所有模板均成功输出 PDF
- `1`：部分模板失败（仍有 PDF 输出）
- `2`：致命错误（无任何 PDF 输出）

---

## 8. PDF 生成机制（CDP 实现）

### 8.1 为什么不能用 `page.pdf()`

Playwright 文档明确：

> `page.pdf()` is currently only supported in Chromium headless mode.

v1 默认 headless 所以可用 `page.pdf()`。v2 默认 headed + `channel="chrome"`，必须改用 CDP。

### 8.2 CDP `Page.printToPDF` 参数

```python
client = page.context.new_cdp_session(page)
result = client.send("Page.printToPDF", {
    "printBackground": True,        # 保留背景色和图片
    "paperWidth": 8.27,              # A4 inches (210mm)
    "paperHeight": 11.69,            # A4 inches (297mm)
    "marginTop": 0,
    "marginBottom": 0,
    "marginLeft": 0,
    "marginRight": 0,
    "scale": 1.0,
    "displayHeaderFooter": False,
    "preferCSSPageSize": False,      # 强制使用 paperWidth/paperHeight
})
pdf_bytes = base64.b64decode(result["data"])
```

返回值是 `{"data": "<base64-encoded-pdf>"}`，必须 base64 解码后写文件。

### 8.3 页面就绪等待策略

保留 v1 的三段式等待：

```
page.goto(url, wait_until="domcontentloaded")
        │
        ▼
networkidle 等待（最多 30s）
        │
   触发 ──→ 额外 2 秒（让 JS 渲染稳定）
   超时 ──→ 兜底 3 秒
        │
        ▼
   保存 PDF
```

### 8.4 PDF 内容完整性

Google SERP 第一页通常 ≤ 20 条结果，A4 全页面 PDF（无滚动截断）能完整覆盖。如果将来要保存"翻页 N 页"的内容，需要在 `searcher` 增加翻页循环 + 多 PDF 合并。

---

## 9. 取证完整性保障

这是 v2 相对 v1 的重要新增章节。PDF 作为合规证据需要满足：

### 9.1 不可篡改证明

- PDF 写入磁盘后立即计算 SHA-256，写入同名 JSON
- HTML 快照同样计算 SHA-256
- 用户可在事后用 `sha256sum file.pdf` 验证文件未被改动

### 9.2 时间权威性

- `searched_at_utc` 使用 `datetime.now(timezone.utc)`，避免本地时间漂移
- 文件名使用 ISO 8601 紧凑 UTC 格式（`YYYYMMDDTHHMMSSZ`），跨时区无歧义
- `searched_at_local` 仅作展示用途

### 9.3 多重证据冗余

PDF 是首选证据，但 PDF 是渲染产物，难以追溯原始 DOM。所以 v2 强制保留：

- **PDF**（用户可读，最直观）
- **HTML 快照**（原始 DOM，可重新渲染验证）
- **PNG 全页面截图**（独立于 PDF/HTML 渲染管线，作为最后兜底）

### 9.4 元数据可审计性

JSON 中记录：

- 浏览器 channel、UA、viewport
- 是否触发用户介入（`had_user_interaction`）
- 解析状态（`results_parse_status`）
- 任何错误信息

事后审计可通过 JSON 完整重建任务上下文。

---

## 10. 测试策略

### 10.1 测试分层

```
┌────────────────────────────────────────┐
│  单元测试（无需 Playwright）            │
│                                        │
│  test_config.py    — YAML 加载、env 覆盖│
│  test_cli.py       — 参数兼容性         │
│  test_templates.py — 多查询构造         │
│  test_pdf.py       — 等待/快照保存逻辑  │
│  test_browser.py   — 浏览器配置初始化   │
└────────────────────────────────────────┘
                    │
┌────────────────────▼───────────────────┐
│  集成测试（mock Playwright）            │
│                                        │
│  test_searcher.py  — 编排逻辑、JSON 输出│
└────────────────────────────────────────┘
                    │
┌────────────────────▼───────────────────┐
│  集成测试（真实 Chrome，可跳过）        │
│                                        │
│  test_integration.py                   │
│  ※ 需要 GOOGLE_SEARCH_RUN_INTEGRATION=1 │
│  ※ 需要已登录 profile                  │
│  ※ profile 不存在时自动 skip           │
└────────────────────────────────────────┘
```

### 10.2 关键测试用例

**`test_cli.py`**：验证 `python -m google_search <entity> <type>` 会自动映射到 `search` 子命令，并保持显式子命令与全局 `--config` 行为不变。

**`test_searcher.py`**：mock `PersistentBrowser`，验证：

- 多模板分次执行（不是 OR 拼接）
- DOM 解析失败时 PDF/JSON 仍正常保存
- 成功运行时会写出同名 JSON 元数据

**`test_pdf.py`**：验证 Playwright timeout 保持毫秒语义，避免 30 秒配置被错误缩短为 30 毫秒。

### 10.3 删除的测试

- `tests/test_proxy.py`（v1）
- `tests/test_ua_pool.py`（v1）

---

## 11. 依赖与安装

### 11.1 `pyproject.toml`（v2）

```toml
[project]
name = "google-search"
version = "0.2.0"
requires-python = ">=3.10"

dependencies = [
    "playwright>=1.44.0",
    "pyyaml>=6.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
google-search = "google_search.cli:main"
```

### 11.2 安装步骤

```bash
# 1. Python 环境
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. 验证 Chrome（不需要 playwright install chromium，因为我们用系统 Chrome）
google-search profile-status   # 应能正常启动 CLI

# 3. 首次登录
google-search login

# 4. 测试搜索
google-search search "测试公司" company
python -m google_search "测试公司" company
```

### 11.3 与 v1 安装的差异

- **不需要** `playwright install chromium`（用系统 Chrome）
- **需要**用户机器装了 Google Chrome（或在配置中改 `channel: chromium` 后再 `playwright install chromium`）

---

## 12. 目录结构规范

```
google-search/
├── pyproject.toml
├── config.yaml
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── .env.example
├── .gitignore
│
├── src/google_search/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── exceptions.py
│   ├── models.py
│   ├── browser.py
│   ├── searcher.py
│   ├── pdf.py
│   ├── parser.py
│   └── templates.py
│
├── tests/
│   ├── __init__.py
│   ├── test_browser.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_templates.py
│   ├── test_pdf.py
│   ├── test_searcher.py
│   └── test_integration.py
│
├── docs/
│   ├── PRD-v2.md
│   ├── ARCHITECTURE-v2.md  # 本文档
│   └── errors.md
│
└── output/                  # 不入 git
```

**与 v1 对比**：

- **删除**：`src/google_search/proxy.py`、`src/google_search/ua_pool.py`、`tests/test_proxy.py`、`tests/test_ua_pool.py`
- **新增**：`src/google_search/parser.py`、`tests/test_cli.py`、`tests/test_pdf.py`
- **重写**：`browser.py`、`pdf.py`、`searcher.py`、`cli.py`

---

## 13. v1 → v2 迁移清单

按以下顺序操作可平滑迁移：

1. **删除文件**：`src/google_search/proxy.py`、`src/google_search/ua_pool.py`、`tests/test_proxy.py`、`tests/test_ua_pool.py`
2. **更新 `config.py`**：移除模块级单例 `config = Config()`；改为 `Config.load(path)` classmethod
3. **更新 `templates.py`**：`build_search_query` 改为 `build_queries`，返回 `list[Query]`
4. **更新 `models.py`**：新增 `EvidenceMetadata`、`TemplateRunResult`；时间字段拆为 UTC + local
5. **重写 `browser.py`**：`PersistentBrowser` + `launch_persistent_context` + `channel="chrome"`
6. **重写 `pdf.py`**：CDP `Page.printToPDF` + SHA-256；新增 `save_html_snapshot`、`save_screenshot`
7. **新增 `parser.py`**：从 `searcher` 拆出 DOM 解析逻辑
8. **重写 `searcher.py`**：移除代理/UA 轮换；多模板顺序执行；reCAPTCHA 等待逻辑
9. **重写 `cli.py`**：Click Group + 三个子命令（`search` / `login` / `profile-status`）；修复 v1 的 `config` 局部变量遮蔽 bug
10. **简化 `exceptions.py`**：保留 3 类异常
11. **更新 `config.yaml`**：删除 `proxy`/`user_agents`；新增 `profile`/`browser`/`search.inter_query_delay_seconds`
12. **更新 `pyproject.toml`**：版本号 → `0.2.0`；移除 `pytest-playwright`（如果之前装了）
13. **运行 `pip install -e ".[dev]"` 重装**
14. **运行 `google-search login` 完成首次登录**
15. **运行 `pytest` 验证**

---

**文档结束**

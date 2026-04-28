"""google_search.searcher — 搜索流程编排（v2 简化版）"""

import json
import random
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone

from playwright.sync_api import Page

from google_search.browser import PersistentBrowser
from google_search.config import Config
from google_search.models import (
    EvidenceMetadata,
    SearchTaskResult,
    TemplateRunResult,
)
from google_search.parser import parse_search_results
from google_search.pdf import (
    save_html_snapshot,
    save_pdf,
    save_screenshot,
    wait_for_page_ready,
)
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
            print("\n⚠ 检测到 Google 验证页，请在浏览器中手动通过…")
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
    """检测当前页面是否为 Google 拦截页"""
    if "/sorry/" in page.url:
        return True
    if page.query_selector("form#captcha-form"):
        return True
    return False


def _wait_for_unblock(page: Page, timeout_seconds: int) -> None:
    """等待用户手动通过验证页"""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _is_blocked(page):
            return
        time.sleep(2)
    raise TimeoutError("用户未及时通过验证")


def _sanitize_filename(name: str) -> str:
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

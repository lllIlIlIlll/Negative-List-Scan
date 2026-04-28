"""google_search.pdf — PDF 生成模块（CDP printToPDF）"""

import base64
import hashlib
import time
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
    start = time.time()
    try:
        page.wait_for_load_state("networkidle", timeout=network_idle_timeout_ms / 1000)
        page.wait_for_timeout(2_000)
    except Exception:
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(fallback_wait_ms)
    return int((time.time() - start) * 1000)

"""google_search.browser — 持久化 Chrome 浏览器管理"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import BrowserContext, Page, sync_playwright

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
        """上下文管理器，启动浏览器 + 自动清理"""
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
        """在现有 context 中创建新 page"""
        if self._context is None:
            raise RuntimeError("必须在 session() 上下文内调用 new_page()")
        return self._context.new_page()

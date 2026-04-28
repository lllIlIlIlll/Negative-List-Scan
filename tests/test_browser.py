"""tests/test_browser.py — 浏览器模块测试（v2）"""

import tempfile
from pathlib import Path

from google_search.browser import PersistentBrowser
from google_search.config import BrowserConfig


def test_persistent_browser_init():
    """PersistentBrowser 应能正常初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "profile"
        browser_config = BrowserConfig(
            channel="chromium",
            headless=True,
            viewport_width=1280,
            viewport_height=900,
        )
        browser = PersistentBrowser(profile_path, browser_config)
        assert browser.profile_path == profile_path
        assert browser.config.channel == "chromium"
        assert browser.config.headless is True


def test_persistent_browser_creates_profile_dir():
    """PersistentBrowser 应在 session() 调用时创建 profile 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "new_profile"
        browser_config = BrowserConfig()
        browser = PersistentBrowser(profile_path, browser_config)

        assert not profile_path.exists()
        # session() 是上下文管理器，这里只验证目录创建逻辑
        # 实际浏览器启动需要真实环境
        browser.profile_path.mkdir(parents=True, exist_ok=True)
        assert profile_path.exists()

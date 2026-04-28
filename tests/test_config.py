"""tests/test_config.py — 配置模块单元测试（v2）"""

import tempfile
from pathlib import Path

import yaml

from google_search.config import (
    Config,
)


def test_config_load_defaults():
    """Config.load() 应使用默认值"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("")
        f.flush()
        cfg = Config.load(f.name)
        assert cfg.browser.channel == "chrome"
        assert cfg.browser.headless is False
        assert cfg.browser.viewport_width == 1280
        assert cfg.browser.viewport_height == 900
        Path(f.name).unlink()


def test_config_load_full():
    """Config.load() 应正确加载完整配置"""
    config_data = {
        "profile": {"path": "/tmp/test_profile"},
        "browser": {
            "channel": "chromium",
            "headless": True,
            "viewport": {"width": 1920, "height": 1080},
        },
        "search": {
            "hl": "en",
            "gl": "us",
            "inter_query_delay_seconds": [10, 20],
            "page_load_timeout_seconds": 60,
            "network_idle_timeout_seconds": 60,
            "captcha_wait_seconds": 240,
        },
        "search_templates": {
            "company": [
                {"id": "test1", "template": '"{name}" AND (欺诈)'}
            ]
        },
        "output": {
            "directory": "/tmp/output",
            "save_html": False,
            "save_screenshot": False,
        },
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        f.flush()
        cfg = Config.load(f.name)

        assert cfg.profile_path == Path("/tmp/test_profile")
        assert cfg.browser.channel == "chromium"
        assert cfg.browser.headless is True
        assert cfg.browser.viewport_width == 1920
        assert cfg.browser.viewport_height == 1080
        assert cfg.search.hl == "en"
        assert cfg.search.gl == "us"
        assert cfg.search.inter_query_delay_seconds == (10, 20)
        assert cfg.search.captcha_wait_seconds == 240
        assert "company" in cfg.templates
        assert cfg.templates["company"][0].id == "test1"
        assert cfg.output.directory == Path("/tmp/output")
        assert cfg.output.save_html is False
        Path(f.name).unlink()


def test_config_env_override_profile(tmp_path, monkeypatch):
    """GOOGLE_SEARCH_PROFILE 环境变量应覆盖配置"""
    config_data = {"profile": {"path": "/tmp/original"}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        f.flush()
        monkeypatch.setenv("GOOGLE_SEARCH_PROFILE", str(tmp_path / "env_profile"))
        cfg = Config.load(f.name)
        assert cfg.profile_path == tmp_path / "env_profile"
        monkeypatch.delenv("GOOGLE_SEARCH_PROFILE")
        Path(f.name).unlink()


def test_config_env_override_output_dir(tmp_path, monkeypatch):
    """GOOGLE_SEARCH_OUTPUT_DIR 环境变量应覆盖配置"""
    config_data = {"output": {"directory": "/tmp/original"}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        f.flush()
        monkeypatch.setenv("GOOGLE_SEARCH_OUTPUT_DIR", str(tmp_path / "env_output"))
        cfg = Config.load(f.name)
        assert cfg.output.directory == tmp_path / "env_output"
        monkeypatch.delenv("GOOGLE_SEARCH_OUTPUT_DIR")
        Path(f.name).unlink()


def test_inter_query_delay_normalized_to_tuple():
    """inter_query_delay_seconds 应从 list 规范化为 tuple"""
    config_data = {
        "search": {"inter_query_delay_seconds": [5, 15]},
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        f.flush()
        cfg = Config.load(f.name)
        assert cfg.search.inter_query_delay_seconds == (5, 15)
        assert isinstance(cfg.search.inter_query_delay_seconds, tuple)
        Path(f.name).unlink()

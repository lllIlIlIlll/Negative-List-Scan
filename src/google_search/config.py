"""google_search.config — YAML 配置加载（依赖注入模式）"""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class BrowserConfig:
    """浏览器配置"""
    channel: str = "chrome"
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 900


@dataclass
class SearchConfig:
    """搜索配置"""
    hl: str = "zh-CN"
    gl: str = "cn"
    inter_query_delay_seconds: tuple[int, int] = (5, 15)
    page_load_timeout_seconds: int = 30
    network_idle_timeout_seconds: int = 30
    captcha_wait_seconds: int = 120


@dataclass
class TemplateEntry:
    """模板条目"""
    id: str
    template: str


@dataclass
class OutputConfig:
    """输出配置"""
    directory: Path = Path("./output")
    save_html: bool = True
    save_screenshot: bool = True


@dataclass
class Config:
    """配置类，支持依赖注入"""
    profile_path: Path
    browser: BrowserConfig
    search: SearchConfig
    templates: dict[str, list[TemplateEntry]]
    output: OutputConfig

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Config":
        """从 YAML 加载配置，应用环境变量覆盖"""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

        profile_path = Path(
            os.environ.get("GOOGLE_SEARCH_PROFILE")
            or data.get("profile", {}).get("path", "~/.local/share/google_search/profile")
        ).expanduser()

        output_dir = Path(
            os.environ.get("GOOGLE_SEARCH_OUTPUT_DIR")
            or data.get("output", {}).get("directory", "./output")
        ).expanduser()

        return cls(
            profile_path=profile_path,
            browser=_normalize_browser(data.get("browser", {})),
            search=_normalize_search(data.get("search", {})),
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


def _normalize_browser(raw: dict) -> BrowserConfig:
    """规范化 browser 配置中的 viewport 嵌套结构"""
    if "viewport" in raw:
        raw = dict(raw)
        raw["viewport_width"] = raw["viewport"].get("width", 1280)
        raw["viewport_height"] = raw["viewport"].get("height", 900)
        del raw["viewport"]
    return BrowserConfig(**raw)


def _normalize_search(raw: dict) -> SearchConfig:
    """规范化 search 配置中的 list → tuple 类型"""
    if "inter_query_delay_seconds" in raw:
        raw = dict(raw)
        raw["inter_query_delay_seconds"] = tuple(raw["inter_query_delay_seconds"])
    return SearchConfig(**raw)

"""tests/test_cli.py — CLI 参数兼容性测试"""

from google_search.cli import _inject_default_command


def test_injects_search_for_python_module_short_form():
    """python -m google_search ENTITY TYPE 应自动映射到 search 子命令"""
    assert _inject_default_command(["三鹿集团", "company"]) == [
        "search",
        "三鹿集团",
        "company",
    ]


def test_preserves_explicit_subcommand():
    """显式子命令不应被改写"""
    assert _inject_default_command(["login"]) == ["login"]
    assert _inject_default_command(["profile-status"]) == ["profile-status"]


def test_keeps_global_config_before_search():
    """全局 --config 仍可放在短格式命令前"""
    assert _inject_default_command(["--config", "custom.yaml", "张三", "person"]) == [
        "--config",
        "custom.yaml",
        "search",
        "张三",
        "person",
    ]

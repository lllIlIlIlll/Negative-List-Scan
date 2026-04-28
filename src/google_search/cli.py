"""google_search.cli — Click CLI 命令行接口（v2）"""

import sys
from pathlib import Path

import click

from google_search.config import Config
from google_search.exceptions import FatalError
from google_search.searcher import Searcher


@click.group()
@click.option("-c", "--config", "config_path", default="config.yaml")
@click.pass_context
def cli(ctx, config_path):
    """Google 负面新闻取证工具"""
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
    """执行单实体负面新闻搜索"""
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
    """启动有头 Chrome 让用户登录 Google"""
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
    """显示 profile 状态"""
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

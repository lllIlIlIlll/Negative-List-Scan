# Google Search — 负面新闻取证工具

基于 Playwright 的 Google 搜索取证工具。它会启动绑定独立 profile 的 Chrome，按公司/个人模板搜索负面关键词，并把每个搜索结果页保存为 PDF、HTML、截图和 JSON 元数据。

## 当前定位

- 默认有头 Chrome，复用用户登录状态、cookies 和本机网络环境
- 不内置代理池、UA 池或指纹伪装
- 多个模板分次搜索，每个模板单独生成一组证据文件
- PDF 通过 CDP `Page.printToPDF` 生成，支持 headed Chrome
- JSON 解析是 best-effort：解析失败不会影响 PDF 证据产出

## 环境要求

- Python 3.10+
- Google Chrome，或把 `config.yaml` 里的 `browser.channel` 改成 `chromium` 后安装 Playwright Chromium

安装前先确认版本：

```bash
python3 --version
```

如果系统 `python3` 低于 3.10，请使用项目虚拟环境或自行创建 3.10+ 环境。

## 安装

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

如果使用 `browser.channel: chromium`：

```bash
playwright install chromium
```

## 首次使用

先创建并登录独立浏览器 profile：

```bash
google-search login
```

登录完成后可以检查状态：

```bash
google-search profile-status
```

## 搜索

推荐命令：

```bash
google-search search "三鹿集团" company
google-search search "张三" person --template '"{name}" AND (诈骗 OR 起诉)'
```

兼容短格式：

```bash
python -m google_search "三鹿集团" company
python -m google_search "张三" person --template '"{name}" AND (诈骗 OR 起诉)'
```

常用选项：

```bash
google-search search "三鹿集团" company --output-dir ./results
google-search search "三鹿集团" company --config ./config.yaml
google-search search "三鹿集团" company --headless
google-search search "三鹿集团" company --no-html --no-screenshot
```

## 配置

运行时配置在 `config.yaml`：

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
  person:
    - id: person_default_1
      template: '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕)'

output:
  directory: ./output
  save_html: true
  save_screenshot: true
```

环境变量覆盖：

- `GOOGLE_SEARCH_PROFILE`
- `GOOGLE_SEARCH_OUTPUT_DIR`

## 输出

每个模板会生成一组文件：

- `{实体名}_{template_id}_{YYYYMMDDTHHMMSSZ}.pdf`
- `{实体名}_{template_id}_{YYYYMMDDTHHMMSSZ}.html`
- `{实体名}_{template_id}_{YYYYMMDDTHHMMSSZ}.png`
- `{实体名}_{template_id}_{YYYYMMDDTHHMMSSZ}.json`

JSON 包含搜索模板、URL、UTC/本地时间、浏览器信息、PDF SHA-256、文件路径、解析结果和错误信息。

## 开发

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

真实 Google 搜索集成测试默认跳过；需要手动验证时：

```bash
GOOGLE_SEARCH_RUN_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py
```

项目结构：

```text
src/google_search/
├── __main__.py
├── cli.py
├── config.py
├── browser.py
├── searcher.py
├── pdf.py
├── parser.py
├── models.py
├── exceptions.py
└── templates.py
```

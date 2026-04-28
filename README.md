# Google Search — 负面新闻排查工具

基于 Playwright 无头浏览器的 Google 搜索负面新闻自动化排查工具。

## 功能特性

- 通过 headless Chromium 浏览器访问 Google，不依赖 Google API Key
- 支持公司/个人两种实体类型，自动匹配负面新闻搜索模板
- 支持自定义搜索模板
- 自动保存第一页搜索结果为 PDF（保留原始页面布局）
- 同时输出结构化 JSON（标题、URL、摘要、来源）
- 代理池 + UA 池轮换，支持失败自动重试

---

## 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: macOS / Linux / Windows

> **重要**: 安装前请先确认 Python 版本：
> ```bash
> python3 --version
> ```
> 如果版本低于 3.10，请使用 [pyenv](https://github.com/pyenv/pyenv) 或 [uv](https://github.com/astral-sh/uv) 创建符合要求的虚拟环境。

---

## 安装

### 1. 创建虚拟环境（推荐）

```bash
# 使用 pyenv（推荐）
pyenv install 3.10
pyenv local 3.10

# 或使用 uv（跨平台）
uv venv --python 3.10
source .venv/bin/activate

# 或使用标准 venv
python3.10 -m venv .venv
source .venv/bin/activate
```

### 2. 安装项目及依赖

```bash
pip install -e ".[dev]"
```

### 3. 安装 Playwright 浏览器

```bash
playwright install chromium
```

> **注意**: Playwright 浏览器只需安装一次。如果后续遇到浏览器相关错误，可尝试重新安装：
> ```bash
> playwright install chromium --force
> ```

---

## 快速开始

### 基本用法

```bash
# 搜索公司负面新闻
python -m google_search "三鹿集团" company

# 搜索个人负面新闻
python -m google_search "张三" person
```

### 使用自定义搜索模板

```bash
# 使用双引号精确匹配名称，并指定多个关键词
python -m google_search "李四" person --template '"{name}" AND (诈骗 OR 起诉 OR 举报)'

# 搜索公司时排除特定关键词
python -m google_search "某公司" company --template '"{name}" AND (欺诈 OR 投诉) NOT (辟谣 OR 声明)'
```

### 指定输出目录

```bash
python -m google_search "三鹿集团" company --output-dir ./results
```

### 指定配置文件

```bash
python -m google_search "三鹿集团" company --config /path/to/config.yaml
```

---

## 配置说明

所有配置通过 `config.yaml` 文件管理。

### 完整配置示例

```yaml
# config.yaml

# 代理配置
proxy:
  # 是否启用代理（建议开启，避免 Google 拦截）
  enabled: true
  pool:
    # 格式: http://user:pass@host:port
    # 可添加多个代理，失败时自动切换
    - http://user:pass@proxy1.example.com:8080
    - http://user:pass@proxy2.example.com:8080
    - http://proxy3.example.com:8080  # 无认证代理

# User-Agent 池（自动随机轮换）
user_agents:
  - Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
  - Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0
  - Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15

# 搜索模板（{name} 会在运行时替换为实际实体名称）
search_templates:
  company:
    - '"{name}" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约)'
    - '"{name}" AND (调查 OR 处罚 OR 监管 OR 违规 OR 黑名单)'
  person:
    - '"{name}" AND (诈骗 OR 起诉 OR 举报 OR 犯罪 OR 逮捕)'
    - '"{name}" AND (受贿 OR 挪用 OR 潜逃 OR 被抓)'

# 输出配置
output:
  directory: ./output
```

### 代理配置的必要性

**强烈建议启用代理**，原因如下：

1. **避免 IP 封禁**: Google 会根据请求频率和 IP 行为模式进行检测，单一 IP 频繁访问容易被封
2. **降低 403 错误**: 无代理情况下，连续搜索可能触发 Google 的反爬机制，返回 403 Forbidden
3. **地理位置伪装**: 部分搜索结果与 IP 所在地相关，代理可以获取不同地区的搜索结果

**代理来源推荐**:
- 付费代理服务（如 Luminati、Oxylabs）
- 自建代理服务器
- 免费代理（仅限测试，生产环境不推荐）

### 模板语法说明

搜索模板遵循 Google 搜索语法：

| 语法 | 说明 | 示例 |
|------|------|------|
| `"{name}"` | 精确匹配 | `"张三"` 匹配完整词组 |
| `OR` | 或关系 | `诈骗 OR 欺诈` |
| `AND` | 且关系 | `"欺诈" AND "投诉"` |
| `NOT` | 排除 | `"公司" NOT "辟谣"` |
| `( )` | 分组 | `(诈骗 OR 欺诈) AND "张三"` |

---

## 输出说明

每次搜索生成两个文件，保存在配置的输出目录中（默认 `./output`）：

### PDF 文件

- **命名格式**: `{实体名}_{YYYYMMDD}_{HHMMSS}.pdf`
- **内容**: Google 搜索结果页的完整截图（全页面）
- **特点**: 保留 Google 页面原始布局，便于人工审核

### JSON 文件

- **命名格式**: `{实体名}_{YYYYMMDD}_{HHMMSS}.json`
- **内容**: 结构化的搜索结果数据

```json
{
  "entity": "三鹿集团",
  "entity_type": "company",
  "search_time": "2024-01-15T10:30:00",
  "template_used": "\"{name}\" AND (欺诈 OR 投诉 OR 曝光 OR 纠纷 OR 起诉 OR 违约)",
  "results": [
    {
      "title": "三鹿集团 - 百度百科",
      "url": "https://baike.baidu.com/item/三鹿集团",
      "snippet": "三鹿集团是中国一家大型乳制品企业...",
      "source": "baidu"
    },
    {
      "title": "三鹿集团毒奶粉事件 - 新浪新闻",
      "url": "https://news.sina.com.cn/...",
      "snippet": "2008年，三鹿集团被曝光...",
      "source": "google"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `entity` | 搜索的实体名称 |
| `entity_type` | 实体类型（`company` 或 `person`） |
| `search_time` | 搜索时间（ISO 8601 格式） |
| `template_used` | 实际使用的搜索模板 |
| `results` | 搜索结果数组 |
| `results[].title` | 结果标题 |
| `results[].url` | 结果链接 |
| `results[].snippet` | 结果摘要/描述 |
| `results[].source` | 来源（`google` 表示 Google 原生结果） |

---

## 故障排查

### Google 403 拦截

**错误信息**: `403 Forbidden` 或页面显示 "我们的系统检测到异常流量"

**原因**: Google 的反爬机制触发了

**解决方案**:
1. **启用代理**（推荐）- 在 `config.yaml` 中配置多个代理并设置 `enabled: true`
2. **降低请求频率** - 避免短时间内多次搜索
3. **更新 User-Agent** - 确保 `config.yaml` 中的 UA 是最新的浏览器标识

### Playwright 浏览器错误

**错误信息**: `Playwright browser not installed` 或 `Executable doesn't exist`

**解决方案**:
```bash
playwright install chromium
```

**如果仍然失败**:
```bash
playwright install chromium --force
```

### asyncio 事件循环冲突

**错误信息**: `It looks like you are using Playwright Sync API inside the asyncio loop`

**解决方案**: 此问题已在代码中修复，如仍遇到请更新到最新版本。

### Python 版本不满足

**错误信息**: `requires a different Python: 3.9.6 not in '>=3.10'`

**解决方案**:
```bash
# 使用 pyenv
pyenv install 3.10
pyenv local 3.10

# 或使用 uv
uv venv --python 3.10
source .venv/bin/activate
```

### 搜索结果为空

**可能原因**:
1. 实体名称拼写错误
2. 搜索模板匹配度过严
3. Google 未返回该实体的相关信息

**解决方案**:
1. 尝试使用更宽松的模板: `--template '"{name}"'`
2. 检查实体名称是否需要加双引号精确匹配

### PDF/JSON 未生成

**可能原因**: 输出目录不存在或无写入权限

**解决方案**:
```bash
# 创建输出目录
mkdir -p ./output
chmod 755 ./output
```

---

## 开发

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_searcher.py

# 运行 lint 检查
ruff check .

# 自动修复 lint 问题
ruff check --fix .
```

## 项目结构

```
src/google_search/
├── __init__.py
├── __main__.py      # python -m 入口
├── cli.py           # Click CLI
├── config.py        # 配置加载
├── browser.py       # Playwright 浏览器管理
├── searcher.py      # 搜索流程编排
├── pdf.py           # PDF 生成
├── ua_pool.py       # UA 池
├── proxy.py         # 代理池
└── templates.py     # 搜索模板
```

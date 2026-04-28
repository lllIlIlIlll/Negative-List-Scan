# /run

执行单个实体的负面新闻搜索。

## 使用方法

```
/run "公司名称" company
/run "公司名称" company --template '"{name}" AND (欺诈 OR 投诉)'
/run "个人姓名" person
```

## 参数

- `entity`: 实体名称（公司或个人名称）
- `type`: 实体类型，`company` 或 `person`
- `--template`: 可选，自定义搜索模板，不指定则使用配置文件中预定义的模板

## 说明

调用 `python -m google_search` 执行搜索，结果输出到 `output/` 目录。

## 前提

- Python 环境已激活
- 依赖已安装：`pip install -e .`
- 配置文件 `config.yaml` 已正确配置

# /lint

运行代码 lint 检查并自动修复。

## 使用方法

```
/lint
/lint src/google_search/searcher.py
```

## 说明

使用 ruff 检查代码：
- 不带参数：检查整个项目
- 带参数：检查指定文件

自动修复：`/lint --fix`

## 前提

- 依赖已安装：`pip install -e .[dev]`

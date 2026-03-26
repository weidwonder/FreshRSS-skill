# FreshRSS Skill Claude Code 技能

**[English Version / 英文版本](README.md)**

这是一个 Claude Code 技能，通过 FreshRSS 官方提供的 API 连接你的自托管 [FreshRSS](https://freshrss.org/) 实例，让你用自然语言浏览订阅和管理文章。

## 功能概览

这个版本不再依赖脆弱的网页登录和 HTML 抓取，而是直接调用 FreshRSS API：

- **查看订阅源** —— 列出所有订阅源及未读数
- **浏览文章** —— 按订阅源、未读状态、数量筛选
- **阅读全文** —— 按文章 ID 直接获取内容
- **管理已读状态** —— 批量标记已读或未读
- **切换星标** —— 切换文章收藏状态

## 这次改造的价值

### 以 API 为主，稳定性更高

技能现在使用 FreshRSS 的 Google Reader 兼容 API，不再依赖网页 challenge 登录、`rid` 参数和侧边栏 HTML 正则解析。

### 保持原有 CLI 体验

以下命令保持可用：

- `list-feeds`
- `get-articles [--feed-id ID] [--count N] [--unread]`
- `get-content <article_id>`
- `mark-read <ids>`
- `mark-unread <ids>`
- `toggle-star <article_id>`
- `unread-count`

### 兼容更多部署方式

你可以配置：

- `FRESHRSS_URL` —— FreshRSS 站点根地址，客户端会自动推导 `/api/greader.php`
- `FRESHRSS_API_URL` —— 直接指定 Google Reader API 地址；如果 API 经过另一层代理、域名或端口暴露，推荐显式配置它

## 快速开始

1. **安装依赖**

```bash
cd freshrss/scripts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

2. **配置凭据**

```bash
cp .env.example .env
```

推荐配置：

```dotenv
FRESHRSS_URL=http://your-freshrss-host:1201
FRESHRSS_API_URL=http://your-freshrss-host:1201/api/greader.php
FRESHRSS_USERNAME=your-username
FRESHRSS_API_PASSWORD=your-api-password
```

为了兼容旧配置，也支持：

```dotenv
FRESHRSS_PASSWORD=your-password
```

3. **验证**

```bash
.venv/bin/python freshrss_cli.py list-feeds
.venv/bin/python freshrss_cli.py unread-count
.venv/bin/python freshrss_cli.py get-articles --unread --count 3
```

详细设置说明请参考 [references/setup.md](freshrss/references/setup.md)。

## 可用命令

| 命令 | 说明 |
|------|------|
| `list-feeds` | 列出所有订阅源及其 ID 和未读数 |
| `get-articles [--feed-id ID] [--count N] [--unread]` | 获取文章列表，支持筛选 |
| `get-content <article_id>` | 按文章 ID 获取全文 |
| `mark-read <ids>` | 标记为已读（逗号分隔多个 ID） |
| `mark-unread <ids>` | 标记为未读（逗号分隔多个 ID） |
| `toggle-star <article_id>` | 切换文章星标 |
| `unread-count` | 查看各订阅源的未读数量 |

## 关于文章 ID

Google Reader API 返回的是 item ID。CLI 会展示较短的后缀形式，命令同时接受：

- 短 ID，例如 `00064dec964114be`
- 完整 ID，例如 `tag:google.com,2005:reader/item/00064dec964114be`

## 轻量自检方式

先检查未读总览：

```bash
.venv/bin/python freshrss_cli.py unread-count
.venv/bin/python freshrss_cli.py get-articles --unread --count 5
```

如果 `unread-count` 显示某个订阅源有未读，`get-articles --unread` 返回的文章状态应显示为 `[unread]`。

也可以对单篇文章做一次往返验证：

```bash
.venv/bin/python freshrss_cli.py mark-read <article_id>
.venv/bin/python freshrss_cli.py mark-unread <article_id>
```

## 技术细节

- 使用 FreshRSS 的 Google Reader 兼容 API：`/api/greader.php`
- 使用 `accounts/ClientLogin` 进行认证
- 使用 `/reader/api/0/token` 与 `/reader/api/0/edit-tag` 执行已读、未读、星标操作
- 仅在 API 返回结构化条目后，才把文章 HTML 摘要转换为可读文本
- 依赖：`requests`、`python-dotenv`

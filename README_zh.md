# FreshRSS Skill Claude Code 技能

**[English Version / 英文版本](README.md)**

一个 Claude Code 技能，将你的 AI 助手连接到自托管的 [FreshRSS](https://freshrss.org/) 实例，通过自然语言管理 RSS 订阅和文章。

## 功能概览

此技能让 Claude Code 直接访问你的 FreshRSS RSS 阅读器。无需在终端和浏览器之间来回切换，用对话方式管理你的 RSS 订阅：

- **查看订阅源** — 列出所有订阅源及未读数量
- **浏览文章** — 按订阅源、已读状态或数量筛选
- **阅读全文** — 在终端内获取完整文章内容
- **管理已读状态** — 批量标记文章为已读或未读
- **收藏文章** — 为重要文章加星标记

## 为什么使用这个技能

### 自然语言管理 RSS

直接告诉 Claude："看看科技频道有什么新文章"或"今天有什么新闻？"——无需记忆命令行参数或操作网页界面。

### 融入你的工作流

如果你已经在终端中使用 Claude Code，这个技能让新闻阅读留在同一个上下文中。阅读文章、和 Claude 讨论内容、继续编码——全部在一个会话中完成。

### 自托管，数据私密

连接到你自己的 FreshRSS 实例。凭据保存在本地 `.env` 文件中，除了你自己的服务器外不涉及任何第三方服务。

### 智能工作流

Claude 可以智能串联命令：检查未读数量、获取感兴趣的文章、阅读全文、然后标记已读——一次对话全部完成。

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
# 编辑 .env，填入你的 FreshRSS 地址、用户名和密码
```

3. **验证**

```bash
.venv/bin/python freshrss_cli.py list-feeds
```

详细设置说明请参考 [references/setup.md](freshrss/references/setup.md)。

## 可用命令

| 命令 | 说明 |
|------|------|
| `list-feeds` | 列出所有订阅源及其 ID 和未读数 |
| `get-articles [--feed-id ID] [--count N] [--unread]` | 获取文章列表，支持筛选 |
| `get-content <article_id>` | 获取文章全文内容 |
| `mark-read <ids>` | 标记为已读（逗号分隔多个 ID） |
| `mark-unread <ids>` | 标记为未读（逗号分隔多个 ID） |
| `toggle-star <article_id>` | 切换文章的星标状态 |
| `unread-count` | 查看各订阅源的未读数量 |

## 使用示例

**早间新闻速览：**
> "我有多少未读文章？" → "看看科技频道最新的 5 篇" → "读一下那篇关于 Rust 的" → "全部标为已读"

**研究收藏：**
> "找找订阅里关于大模型的文章" → "把最相关的收藏起来"

## 技术细节

- 通过 FreshRSS 的 bcrypt 挑战机制进行认证（Web 会话方式）
- 直接解析 FreshRSS HTML 响应——无需安装额外的 API 扩展
- 连接错误时自动重试并重新认证
- 依赖：`requests`、`bcrypt`、`python-dotenv`

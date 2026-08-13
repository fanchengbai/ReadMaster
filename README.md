# ReadMaster

## Personal English Reading Intelligence System

ReadMaster 是一个面向英语阅读学习的智能辅助系统。

> 当前状态：MVP v0.1 开发中。已完成书籍导入、正文阅读器、阅读进度、点击查词、生词管理和语境训练。

目标：

通过阅读英文书籍、技术文档和文章，
逐步建立用户自己的英语理解能力模型。


## 核心理念

传统英语学习：

单词 → 翻译 → 记忆


ReadMaster：

阅读
 ↓
发现未知词汇
 ↓
理解上下文
 ↓
建立词汇关系
 ↓
生成训练任务
 ↓
强化记忆
 ↓
提升阅读能力


## 核心功能

### 1. 英文阅读器

支持：

- TXT
- EPUB
- Markdown
- PDF（后续）


功能：

- 英文原文阅读
- 中英文切换
- 段落对照
- 点击单词查询


### 2. 智能词汇系统

单词信息：

- 发音
- 音标
- 词性
- 基础释义
- 当前语境解释
- 词根词缀
- 相关词
- 例句


### 3. 生词管理

记录：

- 第一次遇见位置
- 来源书籍
- 出现次数
- 掌握程度
- 错题记录


### 4. 学习闯关系统

根据阅读内容生成：

- 单词选择题
- 拼写题
- 填空题
- 词根词缀题
- 语境理解题


完成当前章节训练后，
解锁下一章节。


### 5. AI辅助

AI用于：

- 长难句解析
- 上下文理解
- 个性化解释
- 生成训练内容


AI不是系统核心，
而是增强模块。


## 设计原则

1. 阅读优先

英语学习服务于阅读。


2. 理解优先

不孤立背单词。


3. 结构化学习

建立：

词汇 → 概念 → 场景 → 文章

之间的关系。


4. 渐进强化

通过重复出现和练习形成长期记忆。


## 技术路线

第一阶段：

- Python
- SQLite
- React
- EPUB/TXT解析


第二阶段：

- AI接口
- 向量数据库
- 知识图谱


第三阶段：

- Personal Language Model
- 个性化学习模型

## 已确认的 MVP 方案

- 本地 Web 应用
- 混合词典架构，第一版以本地基础词典为主
- 英文阅读与单词中文释义
- 删除书籍后保留生词和上下文快照
- 桌面浏览器优先，手机保证基本可用

完整方案见 [技术设计文档](docs/technical-design.md)。

## 项目结构

```text
ReadMaster/
├─ frontend/       React + TypeScript + Vite
├─ backend/        FastAPI + SQLAlchemy + SQLite
├─ data/           本地运行数据，不提交到 Git
└─ docs/           产品与技术文档
```

## 当前可用功能

- 导入最大 10 MB 的 TXT 或最大 50 MB 的 EPUB 英文读物
- 自动识别常见 `Chapter`、`Part` 和 `Book` 章节标题
- 读取 EPUB 内置的书名、作者、目录和阅读顺序
- 自动划分段落，并将文本统一保存为 UTF-8
- 书架列表、书籍详情、章节目录和章节内容接口
- 重复书籍、错误格式和空文件校验
- 删除书籍及对应的本地文件
- 启动时自动升级 SQLite 数据库结构
- 从书架进入正文阅读器并切换章节
- 调整字号、行距、正文宽度和明暗主题
- 自动保存章节、段落和总体阅读进度
- 再次打开书籍时恢复到上次阅读位置
- 点击正文中的英文单词，查看音标、词性、中文释义和当前原句
- 将单词及其书籍、章节和原句快照保存到生词库
- 重复遇见同一单词时累计次数，并按“新加入、学习中、基本熟悉、已掌握”筛选
- 删除原书后仍保留生词及其上下文快照
- 从未掌握的生词自动生成语境填词题；生词足够时混合生成释义选择题
- 记录每次作答、正确率和练习词数，答错时累计到对应生词

当前内置的是用于验证完整流程的小型基础词典。词典访问层已经独立，后续可以接入授权的完整离线词典或在线数据源，而无需修改阅读器和生词库。

## 本地开发

### 环境要求

- Python 3.12+
- Node.js 22+
- pnpm 10+

### 后端

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

应用启动时会自动执行数据库迁移。也可以在 `backend` 目录中手动运行：

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
```

- 后端默认地址：`http://127.0.0.1:8000`
- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`

### 前端

新开一个终端，在项目根目录执行：

```powershell
cd frontend
pnpm install
pnpm dev
```

前端默认地址：`http://localhost:5173`

## 验证

```powershell
# 后端
cd backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check app tests

# 前端
cd frontend
pnpm test
pnpm build
pnpm lint
```

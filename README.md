# Agent Memory Verification

这个项目现在按 Hermes 官方记忆框架做本地化 MVP，不再使用通用 `memories` 大仓模型，而是拆成三层：

1. `Persistent Memory`
2. `Skills`
3. `Session Search`

实现目标不是完整复刻 Hermes，而是在当前仓库内验证三层存储、检索和接口抽象。

## 三层设计

### Layer 1: Persistent Memory

- 用两个小文件模拟 Hermes 的 `MEMORY.md` 和 `USER.md`
- 存储位置：`generated_memories/hermes/memories/`
- `MEMORY.md` 适合放环境事实、项目约定、长期经验
- `USER.md` 适合放用户偏好、沟通风格、长期要求
- 启动时可渲染为 system prompt snapshot
- 严格字符上限：
  - `MEMORY.md`: 2200 chars
  - `USER.md`: 1375 chars

### Layer 2: Skills

- 用 `generated_memories/hermes/skills/<skill-slug>/SKILL.md` 模拟程序性记忆
- 每个 skill 同时落一份 `metadata.json`
- 适合沉淀可复用流程、检查清单、操作 SOP
- 支持按 query 做简单 skill routing

### Layer 3: Session Search

- 用 `generated_memories/hermes/state.db` 模拟 Hermes 的 SQLite/FTS5 会话搜索层
- 每条 session event 进 SQLite，并同步到 FTS5 索引
- 需要历史上下文时，按 `session_id + query` 检索片段
- 当前摘要是本地拼接版，不接 LLM

## 当前能力

- 对 `MEMORY.md` / `USER.md` 执行 `add / replace / remove`
- 渲染 persistent memory 的启动 prompt block
- 创建和列出 skills
- 按 query 匹配最相关 skill
- 记录 session events
- 基于 SQLite FTS5 搜索单个 session 历史

## 项目结构

```text
agent-memory-project
├── main.py
├── config
└── agent_memory_project
    ├── api
    │   ├── main.py
    │   ├── memory_api.py
    │   └── schemas.py
    └── services
        ├── persistent_memory_service.py
        ├── skill_service.py
        └── session_search_service.py
```

## 安装依赖

```bash
uv sync
```

## 启动服务

```bash
uv run uvicorn agent_memory_project.api.main:app --reload
```

或者：

```bash
uv run python -m agent_memory_project
```

## API

- `GET /health`
- `GET /api/v1/persistent-memory?target=memory|user`
- `POST /api/v1/persistent-memory/add`
- `POST /api/v1/persistent-memory/replace`
- `POST /api/v1/persistent-memory/remove`
- `GET /api/v1/persistent-memory/prompt-block`
- `GET /api/v1/skills/catalog`
- `GET /api/v1/skills`
- `POST /api/v1/skills`
- `POST /api/v1/skills/match`
- `GET /api/v1/skills/{slug}`
- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}/events`
- `POST /api/v1/sessions/{session_id}/events`
- `POST /api/v1/sessions/{session_id}/search`
- `POST /api/v1/sessions/{session_id}/extract`
- `POST /api/v1/sessions/{session_id}/materialize`

## CLI

新增 persistent memory：

```bash
uv run python main.py memory-add --target user --content "用户偏好简洁回答，避免过度展开。"
```

替换 persistent memory：

```bash
uv run python main.py memory-replace --target user --old-text "简洁回答" --content "用户偏好简洁但完整的回答。"
```

查看 persistent memory：

```bash
uv run python main.py memory-show --target memory
```

渲染启动 prompt block：

```bash
uv run python main.py prompt-block
```

新增 skill：

```bash
uv run python main.py skill-add \
  --skill-name "PR Workflow" \
  --description "Create and review pull requests with a repeatable checklist." \
  --triggers pr review merge \
  --steps "inspect diff" "run tests" "write summary"
```

查看 skills catalog：

```bash
uv run python main.py skills-catalog
```

按 slug 查看完整 skill：

```bash
uv run python main.py skill-view --slug pr-workflow
```

匹配 skill：

```bash
uv run python main.py skill-match --query "help me review a pull request"
```

写入 session event：

```bash
uv run python main.py session-add --session-id demo-1 --role user --content "今天我们讨论了 Hermes 的三层记忆系统。"
```

搜索 session：

```bash
uv run python main.py session-search --session-id demo-1 --query "Hermes 记忆"
```

从 session 提炼 persistent/skill 候选：

```bash
uv run python main.py session-extract --session-id demo-1 --limit 10
```

把提炼结果真正写入目标层：

```bash
uv run python main.py materialize-suggestion \
  --kind persistent_user \
  --title "User Preference" \
  --content "用户偏好简洁回答，避免过度展开。"
```

## 说明

- 这个仓库目前是在项目目录内模拟 `~/.hermes/`
- 所有数据都落在 `generated_memories/hermes/`
- `Persistent Memory` 已经具备 Hermes 风格的容量约束和 frozen snapshot 视图
- `Persistent Memory` 新增相似条目去重和 richer-entry merge
- `Skills` 已经具备最小可用的程序性记忆落盘、catalog、按需加载和路由
- `Session Search` 已经具备 SQLite FTS5 检索能力
- 新增 `memory_orchestrator_service`，可从 session 片段里提炼：
  - `persistent_user`
  - `persistent_memory`
  - `skill`
- 还没有接入真实 LLM 做会话摘要、记忆压缩和自动技能抽取
- 如果配置了 OpenAI 模型，`session-extract` 和摘要会优先走 LLM；未配置时走本地规则
- progressive disclosure 当前实现为：
  - catalog 先只返回 `slug/name/description/triggers`
  - 需要时再用 `skill-view` 或 `GET /api/v1/skills/{slug}` 加载全文

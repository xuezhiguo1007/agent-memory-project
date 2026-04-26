# Agent Memory Verification

这个项目参考 `skill-project` 的骨架，提供一个最小可运行的 agent memory 初版。

当前目标不是做完整记忆平台，而是先验证 3 件事：

1. 能否通过 FastAPI 和 CLI 写入记忆
2. 能否把记忆持久化到本地 JSON 文件
3. 能否基于 query 做一个最小可用的记忆检索

## 当前能力

- 新增一条 memory
- 查看全部 memories
- 根据 query 搜索 memories
- 本地持久化到 `generated_memories/memories`

## 项目结构

```text
agent-memory-project
├── main.py
├── config
│   ├── dev.toml
│   ├── local.toml
│   ├── prod.toml
│   └── test.toml
└── agent_memory_project
    ├── __init__.py
    ├── __main__.py
    ├── api
    │   ├── __init__.py
    │   ├── lifespan.py
    │   ├── main.py
    │   ├── memory_api.py
    │   └── schemas.py
    ├── core
    │   ├── __init__.py
    │   └── config.py
    ├── llm
    │   ├── __init__.py
    │   └── openai_client.py
    └── services
        ├── __init__.py
        └── memory_service.py
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
- `GET /api/v1/memories`
- `POST /api/v1/memories`
- `POST /api/v1/memories/search`

## CLI

新增一条 memory：

```bash
uv run python main.py remember --content "用户偏好：喜欢海岛旅行，不喜欢太赶的行程"
```

查看所有 memories：

```bash
uv run python main.py list-memories
```

检索 memories：

```bash
uv run python main.py recall --query "海岛 轻松 行程"
```

## 说明

- 当前版本先用关键词重叠做简单检索，不依赖 LLM
- `llm/` 目录已预留，后续可以补摘要、压缩、反思、长期记忆抽取等能力

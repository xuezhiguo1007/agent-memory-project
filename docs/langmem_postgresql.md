# Langmem PostgreSQL 实现说明

## 概述

Langmem 服务使用 PostgreSQL 作为存储后端，实现了 LangChain 风格的记忆管理能力。

## PostgreSQL 特性

### 1. 数据表结构

#### langmem_messages（消息表）
```sql
CREATE TABLE langmem_messages (
    message_id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    content_tsvector TSVECTOR
);
```

**特性**：
- `JSONB` 类型存储 metadata，支持高效查询和索引
- `TSVECTOR` 类型实现全文搜索
- 自动触发器更新搜索向量

#### langmem_entities（实体表）
```sql
CREATE TABLE langmem_entities (
    entity_id SERIAL PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    occurrences INTEGER DEFAULT 1,
    search_tsvector TSVECTOR,
    UNIQUE(entity_name, entity_type)
);
```

**特性**：
- 实体唯一约束（entity_name + entity_type）
- 自动追踪实体出现次数
- 自动更新 updated_at 时间戳

### 2. 全文搜索（FTS）

PostgreSQL 内置全文搜索功能，使用 `tsvector` 和 `tsquery`：

```sql
-- 搜索消息
SELECT * FROM langmem_messages
WHERE content_tsvector @@ plainto_tsquery('LangChain 记忆')
ORDER BY ts_rank_cd(content_tsvector, plainto_tsquery('LangChain 记忆')) DESC;

-- 搜索实体
SELECT * FROM langmem_entities
WHERE search_tsvector @@ plainto_tsquery('工具')
ORDER BY ts_rank_cd(search_tsvector, plainto_tsquery('工具')) DESC;
```

### 3. 自动触发器

自动更新全文搜索向量：

```sql
CREATE OR REPLACE FUNCTION update_message_tsvector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_tsvector := to_tsvector('english', NEW.content);
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_message_tsvector
BEFORE INSERT OR UPDATE ON langmem_messages
FOR EACH ROW EXECUTE FUNCTION update_message_tsvector();
```

### 4. 异步操作

使用 `asyncpg` 库实现高性能异步数据库操作：

- 连接池管理（最小 5，最大 20 连接）
- 异步查询和事务
- 高并发支持

## 数据库连接配置

### 配置文件：`config/langmem_config.json`

```json
{
  "pg_connection": {
    "host": "localhost",
    "port": 5432,
    "database": "langmem_db",
    "user": "langmem_user",
    "password": "langmem_password"
  }
}
```

### 连接池参数

```python
pool = await asyncpg.create_pool(
    host=pg_config["host"],
    port=pg_config["port"],
    database=pg_config["database"],
    user=pg_config["user"],
    password=pg_config["password"],
    min_size=5,    # 最小连接数
    max_size=20,   # 最大连接数
)
```

## 性能优化

### 1. 索引优化

```sql
-- 消息表索引
CREATE INDEX idx_messages_session ON langmem_messages(session_id);
CREATE INDEX idx_messages_created_at ON langmem_messages(created_at);
CREATE INDEX idx_messages_tsvector ON langmem_messages USING GIN(content_tsvector);

-- 实体表索引
CREATE INDEX idx_entities_type ON langmem_entities(entity_type);
CREATE INDEX idx_entities_occurrences ON langmem_entities(occurrences DESC);
CREATE INDEX idx_entities_tsvector ON langmem_entities USING GIN(search_tsvector);
```

### 2. JSONB 查询优化

```sql
-- 查询 metadata 中的特定字段
SELECT * FROM langmem_messages
WHERE metadata->>'intent' = 'inquiry';

-- 使用 JSONB 包含查询
SELECT * FROM langmem_messages
WHERE metadata @> '{"compressed": true}';
```

### 3. 分页查询

```sql
-- 使用 LIMIT 和 OFFSET 分页
SELECT * FROM langmem_messages
WHERE session_id = 'demo-session'
ORDER BY message_id ASC
LIMIT 20 OFFSET 40;

-- 使用游标分页（更高效）
SELECT * FROM langmem_messages
WHERE session_id = 'demo-session' AND message_id > 100
ORDER BY message_id ASC
LIMIT 20;
```

## 数据库维护

### 1. 定期清理

```sql
-- 清理旧消息（保留最近 1000 条）
DELETE FROM langmem_messages
WHERE created_at < NOW() - INTERVAL '30 days';

-- 重建索引
REINDEX TABLE langmem_messages;
REINDEX TABLE langmem_entities;
```

### 2. 性能监控

```sql
-- 查看表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'langmem_%';

-- 查看索引使用情况
SELECT
    indexrelname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname LIKE 'langmem_%';
```

### 3. 备份与恢复

```bash
# 备份数据库
pg_dump -U langmem_user -d langmem_db > langmem_backup.sql

# 恢复数据库
psql -U langmem_user -d langmem_db < langmem_backup.sql
```

## Docker 部署

### 使用 Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs postgres

# 停止服务
docker-compose down

# 清理数据
docker-compose down -v
```

### Docker Compose 配置

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: langmem_db
      POSTGRES_USER: langmem_user
      POSTGRES_PASSWORD: langmem_password
    ports:
      - "5432:5432"
    volumes:
      - langmem_pg_data:/var/lib/postgresql/data
```

## 与 Hermes 三层架构的集成

Langmem PostgreSQL 服务可以与现有的 Hermes 记忆系统无缝集成：

1. **Persistent Memory**：长期记忆仍使用 MEMORY.md 和 USER.md
2. **Skills**：程序性记忆使用 SKILL.md
3. **Session Search**：短期会话搜索使用 SQLite FTS5
4. **Langmem**：新增的 PostgreSQL 记忆层，提供更强大的搜索和管理能力

### 集成示例

```python
# 从 Hermes Session Search 提取重要信息并存储到 Langmem
async def integrate_with_hermes(session_id: str):
    # 从 Hermes Session Search 获取数据
    session_service = SessionSearchService()
    events = session_service.list_events(session_id)
    
    # 存储到 Langmem PostgreSQL
    langmem_service = LangmemService()
    await langmem_service.initialize()
    
    for event in events:
        await langmem_service.add_message(
            session_id,
            event.role,
            event.content
        )
```

## 最佳实践

1. **连接池管理**：在应用启动时初始化连接池，关闭时清理
2. **异步操作**：所有数据库操作使用 async/await
3. **事务管理**：需要多个操作时使用事务确保一致性
4. **索引维护**：定期检查和重建索引
5. **监控告警**：监控数据库性能和资源使用

## 参考资料

- PostgreSQL 文档：https://www.postgresql.org/docs/
- asyncpg 文档：https://magicstack.github.io/asyncpg/
- PostgreSQL FTS：https://www.postgresql.org/docs/current/textsearch.html
- JSONB 类型：https://www.postgresql.org/docs/current/datatype-json.html
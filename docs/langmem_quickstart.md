# Langmem PostgreSQL 快速入门指南

## 快速开始（5 分钟）

### 1. 启动 PostgreSQL（使用 Docker）

```bash
# 启动 PostgreSQL 容器
docker-compose up -d

# 等待数据库就绪（约 10 秒）
docker-compose logs postgres | grep "database system is ready"

# 验证连接
docker exec -it langmem_postgres psql -U langmem_user -d langmem_db -c "SELECT version();"
```

### 2. 安装依赖

```bash
# 安装 Python 依赖
uv sync
```

### 3. 测试基本功能

```bash
# 添加第一条消息
uv run python main.py langmem-msg-add \
  --session-id my-first-session \
  --role user \
  --content "这是我的第一条 LangChain 记忆消息！"

# 查看消息列表
uv run python main.py langmem-msg-list --session-id my-first-session

# 添加实体
uv run python main.py langmem-entity-add \
  --entity-name "LangChain" \
  --entity-type tool \
  --description "一个强大的 LLM 应用框架"

# 查看实体列表
uv run python main.py langmem-entity-list
```

### 4. 启动 API 服务

```bash
# 启动 FastAPI 服务
uv run uvicorn agent_memory_project.api.main:app --reload

# 访问 API 文档
open http://localhost:8000/docs
```

### 5. 使用 API

```bash
# 连接到数据库
curl -X POST http://localhost:8000/api/v1/langmem/connect

# 添加消息
curl -X POST http://localhost:8000/api/v1/langmem/messages \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "api-test-session",
    "role": "user",
    "content": "通过 API 测试 Langmem PostgreSQL 服务"
  }'

# 获取记忆快照
curl http://localhost:8000/api/v1/langmem/sessions/api-test-session/snapshot
```

## 常见问题

### Q: PostgreSQL 连接失败？

**解决方案**：
1. 确认 PostgreSQL 正在运行：
   ```bash
   docker-compose ps
   ```
2. 检查连接配置：
   ```bash
   cat config/langmem_config.json
   ```
3. 重启容器：
   ```bash
   docker-compose restart postgres
   ```

### Q: 如何清空数据库重新测试？

```bash
# 停止并删除容器和数据
docker-compose down -v

# 重新启动
docker-compose up -d
```

### Q: 如何查看数据库内容？

```bash
# 进入 PostgreSQL 命令行
docker exec -it langmem_postgres psql -U langmem_user -d langmem_db

# 查看消息表
SELECT * FROM langmem_messages ORDER BY message_id DESC LIMIT 10;

# 查看实体表
SELECT entity_name, entity_type, occurrences FROM langmem_entities ORDER BY occurrences DESC;

# 退出
\q
```

### Q: 如何备份数据？

```bash
# 备份数据库
docker exec langmem_postgres pg_dump -U langmem_user langmem_db > langmem_backup.sql

# 恢复数据库
docker exec -i langmem_postgres psql -U langmem_user langmem_db < langmem_backup.sql
```

## 进阶使用

### 1. 自定义 PostgreSQL 配置

编辑 `config/langmem_config.json`：

```json
{
  "pg_connection": {
    "host": "your-postgres-host",
    "port": 5432,
    "database": "your-database",
    "user": "your-user",
    "password": "your-password"
  },
  "compression_threshold": 100,  // 自定义压缩阈值
  "entity_extraction_enabled": true
}
```

### 2. 全文搜索高级查询

```bash
# 搜索特定关键词
uv run python main.py langmem-msg-search \
  --session-id my-session \
  --query "记忆 管理"

# 搜索实体
uv run python main.py langmem-entity-search --query "LangChain 框架"
```

### 3. 记忆压缩测试

```bash
# 添加大量消息测试压缩功能
for i in {1..60}; do
  uv run python main.py langmem-msg-add \
    --session-id compression-test \
    --role user \
    --content "测试消息 #$i：这是一条用于测试压缩功能的消息。"
done

# 查看压缩前消息数
uv run python main.py langmem-sessions

# 执行压缩
uv run python main.py langmem-compress --session-id compression-test

# 查看压缩后消息数
uv run python main.py langmem-sessions
```

### 4. 在代码中使用

```python
import asyncio
from agent_memory_project.services.langmem_service import LangmemService

async def main():
    # 创建服务实例
    service = LangmemService()
    
    # 初始化连接
    await service.initialize()
    
    # 添加消息
    message = await service.add_message(
        session_id="code-test",
        role="user",
        content="通过代码直接使用 Langmem 服务"
    )
    print(f"消息 ID: {message.message_id}")
    
    # 搜索消息
    messages, summary = await service.search_messages(
        session_id="code-test",
        query="Langmem"
    )
    print(f"找到 {len(messages)} 条消息")
    
    # 获取快照
    snapshot = await service.get_memory_snapshot("code-test")
    print(f"Token 数: {snapshot.token_count}")
    
    # 关闭连接
    await service.close()

# 运行
asyncio.run(main())
```

## 性能优化建议

1. **使用连接池**：服务自动管理连接池（5-20 连接）
2. **批量操作**：需要大量插入时使用事务
3. **定期维护**：每周执行 `VACUUM ANALYZE`
4. **监控查询**：使用 `pg_stat_statements` 监控慢查询

## 生产环境部署

### 1. 使用环境变量

```bash
# 设置环境变量
export PG_HOST=prod-postgres.example.com
export PG_PORT=5432
export PG_DATABASE=langmem_prod
export PG_USER=langmem_prod_user
export PG_PASSWORD=secure_password

# 更新配置
python scripts/update_config_from_env.py
```

### 2. 配置 SSL 连接

```json
{
  "pg_connection": {
    "host": "prod-postgres.example.com",
    "ssl": "require",
    "ssl_cert": "/path/to/cert.pem"
  }
}
```

### 3. 设置资源限制

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## 下一步

- 📖 阅读 [Langmem PostgreSQL 技术文档](./langmem_postgresql.md)
- 🔧 配置 [Hermes 三层记忆系统集成](../README.md)
- 🚀 探索 [API 文档](http://localhost:8000/docs)
- 💡 查看 [示例代码](../examples/)

## 问题反馈

遇到问题？
- 查看 [常见问题](#常见问题)
- 检查 [日志文件](#如何查看数据库内容)
- 提交 Issue 到项目仓库
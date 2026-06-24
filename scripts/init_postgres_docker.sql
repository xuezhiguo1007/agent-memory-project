-- PostgreSQL Docker 初始化脚本
-- 此脚本在 Docker 容器启动时自动执行

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建消息表
CREATE TABLE IF NOT EXISTS langmem_messages (
    message_id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    content_tsvector TSVECTOR
);

-- 创建实体表
CREATE TABLE IF NOT EXISTS langmem_entities (
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_messages_session ON langmem_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON langmem_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_tsvector ON langmem_messages USING GIN(content_tsvector);

CREATE INDEX IF NOT EXISTS idx_entities_type ON langmem_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_occurrences ON langmem_entities(occurrences DESC);
CREATE INDEX IF NOT EXISTS idx_entities_tsvector ON langmem_entities USING GIN(search_tsvector);

-- 创建全文搜索触发器函数
CREATE OR REPLACE FUNCTION update_message_tsvector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_tsvector := to_tsvector('english', NEW.content);
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_entity_tsvector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_tsvector := to_tsvector('english',
        COALESCE(NEW.entity_name, '') || ' ' ||
        COALESCE(NEW.entity_type, '') || ' ' ||
        COALESCE(NEW.description, '')
    );
    NEW.updated_at := NOW();
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trigger_update_message_tsvector ON langmem_messages;
CREATE TRIGGER trigger_update_message_tsvector
    BEFORE INSERT OR UPDATE ON langmem_messages
    FOR EACH ROW EXECUTE FUNCTION update_message_tsvector();

DROP TRIGGER IF EXISTS trigger_update_entity_tsvector ON langmem_entities;
CREATE TRIGGER trigger_update_entity_tsvector
    BEFORE INSERT OR UPDATE ON langmem_entities
    FOR EACH ROW EXECUTE FUNCTION update_entity_tsvector();

-- 插入测试数据（可选）
-- INSERT INTO langmem_messages (session_id, role, content, metadata)
-- VALUES ('test-session', 'user', '这是第一条测试消息', '{"test": true}');

-- 授权
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO langmem_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO langmem_user;

-- 显示创建结果
SELECT 'Langmem tables created successfully' AS status;
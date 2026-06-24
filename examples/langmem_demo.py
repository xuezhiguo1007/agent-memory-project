"""
Langmem 使用示例

演示如何使用 LangChain 风格的记忆管理服务。
"""

from agent_memory_project.services.langmem_service import LangmemService


def demo_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("Langmem 基本使用示例")
    print("=" * 60)

    service = LangmemService()

    # 1. 创建会话并添加消息
    print("\n1. 创建会话并添加消息...")
    session_id = "demo-session-001"

    # 添加用户消息
    user_msg = service.add_message(
        session_id=session_id,
        role="user",
        content="你好，我想了解 LangChain 的记忆管理功能。",
        metadata={"intent": "inquiry"},
    )
    print(f"添加用户消息: {user_msg.content[:50]}...")

    # 添加助手消息
    assistant_msg = service.add_message(
        session_id=session_id,
        role="assistant",
        content="LangChain 提供了多种记忆管理方式，包括 ConversationBufferMemory、ConversationSummaryMemory 等。",
        metadata={"model": "gpt-4"},
    )
    print(f"添加助手消息: {assistant_msg.content[:50]}...")

    # 2. 列出会话消息
    print("\n2. 列出会话消息...")
    messages = service.list_messages(session_id)
    print(f"会话 '{session_id}' 有 {len(messages)} 条消息:")
    for msg in messages:
        print(f"  [{msg.role}] {msg.content[:60]}...")

    # 3. 添加实体
    print("\n3. 添加实体...")
    entity = service.add_entity(
        entity_name="LangChain",
        entity_type="tool",
        description="LangChain 是一个用于构建 LLM 应用的框架，支持多种记忆管理方式。",
        metadata={"category": "framework"},
    )
    print(f"添加实体: {entity.entity_name} ({entity.entity_type})")

    # 再次添加相同实体，会自动更新 occurrence
    entity2 = service.add_entity(
        entity_name="LangChain",
        entity_type="tool",
        description="LangChain 提供对话记忆管理能力。",
    )
    print(f"实体 '{entity2.entity_name}' 出现次数: {entity2.occurrences}")

    # 4. 列出实体
    print("\n4. 列出实体...")
    entities = service.list_entities()
    print(f"共有 {len(entities)} 个实体:")
    for entity in entities:
        print(f"  {entity.entity_name} ({entity.entity_type}) - 出现 {entity.occurrences} 次")

    # 5. 搜索消息
    print("\n5. 搜索消息...")
    search_results, summary = service.search_messages(
        session_id=session_id,
        query="LangChain 记忆",
        limit=5,
    )
    print(f"搜索 'LangChain 记忆' 找到 {len(search_results)} 条消息:")
    for msg in search_results[:3]:
        print(f"  [{msg.role}] {msg.content[:60]}...")

    # 6. 搜索实体
    print("\n6. 搜索实体...")
    entity_results = service.search_entities(query="LangChain", limit=5)
    print(f"搜索实体 'LangChain' 找到 {len(entity_results)} 个实体:")
    for entity in entity_results:
        print(f"  {entity.entity_name}: {entity.description[:60]}...")

    # 7. 获取记忆快照
    print("\n7. 获取记忆快照...")
    snapshot = service.get_memory_snapshot(session_id)
    print(f"会话快照:")
    print(f"  - 消息数: {len(snapshot.messages)}")
    print(f"  - 实体数: {len(snapshot.entities)}")
    print(f"  - Token数: {snapshot.token_count}")
    print(f"  - 摘要: {snapshot.summary[:100]}...")

    # 8. 列出所有会话
    print("\n8. 列出所有会话...")
    sessions = service.list_sessions()
    print(f"共有 {len(sessions)} 个会话:")
    for session in sessions:
        print(f"  {session['session_id']}: {session['message_count']} 条消息")

    # 9. 查看配置
    print("\n9. 查看配置...")
    config = service.config
    print(f"当前配置:")
    print(f"  - 最大消息数: {config['max_messages_per_session']}")
    print(f"  - 最大 Token 数: {config['max_tokens_per_snapshot']}")
    print(f"  - 实体提取: {config['entity_extraction_enabled']}")
    print(f"  - 自动压缩: {config['auto_compression_enabled']}")
    print(f"  - 压缩阈值: {config['compression_threshold']}")

    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)


def demo_memory_compression():
    """记忆压缩示例"""
    print("\n" + "=" * 60)
    print("记忆压缩示例")
    print("=" * 60)

    service = LangmemService()
    session_id = "compression-demo"

    # 添加大量消息（超过压缩阈值）
    print("\n添加大量消息...")
    for i in range(60):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"消息 #{i}: 这是一条测试消息，用于演示记忆压缩功能。"
        service.add_message(session_id, role, content)

    # 检查消息数量
    msg_count = service.get_message_count(session_id)
    print(f"当前消息数量: {msg_count}")

    # 执行压缩
    print("\n执行记忆压缩...")
    result = service.compress_memory(session_id)
    print(f"压缩结果:")
    print(f"  - 是否压缩: {result['compressed']}")
    if result['compressed']:
        print(f"  - 原始消息数: {result['original_count']}")
        print(f"  - 剩余消息数: {result['remaining_count']}")
        print(f"  - 摘要: {result['summary'][:100]}...")

    # 检查压缩后的消息数量
    new_msg_count = service.get_message_count(session_id)
    print(f"\n压缩后消息数量: {new_msg_count}")

    print("\n" + "=" * 60)


def demo_entity_extraction():
    """实体自动提取示例"""
    print("\n" + "=" * 60)
    print("实体自动提取示例")
    print("=" * 60)

    service = LangmemService()
    session_id = "entity-extraction-demo"

    # 添加包含实体的消息
    print("\n添加包含实体的消息...")
    messages = [
        "我们正在使用文件 'memory_service.py' 开发记忆管理系统。",
        "项目 'agent-memory-project' 的目标是验证多层记忆架构。",
        "用户 '张三' 提出了关于记忆压缩的需求。",
        "工具 'LangChain' 提供了对话记忆管理的能力。",
        "概念 'FTS5' 用于实现全文搜索功能。",
    ]

    for i, content in enumerate(messages):
        role = "user" if i % 2 == 0 else "assistant"
        msg = service.add_message(session_id, role, content)
        print(f"  [{msg.role}] {msg.content}")

    # 检查提取的实体
    print("\n检查自动提取的实体...")
    entities = service.list_entities()
    print(f"共提取到 {len(entities)} 个实体:")
    for entity in entities:
        print(f"  {entity.entity_name} ({entity.entity_type})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 运行所有示例
    demo_basic_usage()
    demo_memory_compression()
    demo_entity_extraction()
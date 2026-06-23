"""测试 FTS5 分词行为"""
import sqlite3
from pathlib import Path
import tempfile
import os

# 创建临时数据库测试
temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 创建 FTS5 表（默认分词器）
conn.execute("""
    CREATE VIRTUAL TABLE test_fts
    USING fts5(content)
""")

# 测试数据
test_cases = [
    "Python programming is fun",
    "如何学习Python编程",
    "Python 和 Java 的区别",
    "推荐一些 Python 书籍",
    "机器学习 deep learning",
]

# 插入测试数据
for i, text in enumerate(test_cases):
    conn.execute("INSERT INTO test_fts(rowid, content) VALUES (?, ?)", (i+1, text))

# 查看分词结果
print("=== 测试分词 ===\n")

# 方法1: 查询所有 tokens
print("方法1: 通过查询查看实际分词")
for text in test_cases:
    print(f"原文: {text}")
    # 尝试匹配单个词
    words = text.split()
    for word in words:
        cursor = conn.execute("SELECT * FROM test_fts WHERE content MATCH ?", (word,))
        results = cursor.fetchall()
        if results:
            print(f"  词 '{word}' → 匹配到 {len(results)} 条记录")
    print()

# 方法2: 查看 token 表（FTS5 内部结构）
print("\n方法2: FTS5 内部 token")
cursor = conn.execute("SELECT * FROM test_fts_data")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# 测试搜索
print("\n=== 测试搜索 ===\n")

# 英文搜索
print("搜索 'Python':")
cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH 'Python'")
for row in cursor.fetchall():
    print(f"  ✓ {row['content']}")

# 中文搜索
print("\n搜索 '编程':")
cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH '编程'")
for row in cursor.fetchall():
    print(f"  ✓ {row['content']}")

# 中文词组搜索
print("\n搜索 '学习':")
cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH '学习'")
for row in cursor.fetchall():
    print(f"  ✓ {row['content']}")

# 组合搜索
print("\n搜索 'Python 编程':")
cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH 'Python OR 编程'")
for row in cursor.fetchall():
    print(f"  ✓ {row['content']}")

conn.close()

# 清理
import shutil
shutil.rmtree(temp_dir)
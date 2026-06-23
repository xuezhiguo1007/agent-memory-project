"""演示中文搜索问题"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 创建默认 FTS5 表
conn.execute("""
    CREATE VIRTUAL TABLE content_fts
    USING fts5(content)
""")

# 插入测试数据
test_data = [
    "我想学习Python编程",
    "Python入门教程推荐",
    "机器学习基础知识",
    "深度学习神经网络",
]

for i, text in enumerate(test_data):
    conn.execute("INSERT INTO content_fts(rowid, content) VALUES (?, ?)", (i+1, text))

print("=== 中文搜索测试 ===\n")

# 测试各种搜索
search_tests = [
    ("Python", "英文关键词"),
    ("编程", "中文词汇"),
    ("学习", "中文词汇"),
    ("机器 学习", "空格分隔的中文"),
    ("机器学习", "整体中文词汇"),
    ("深度", "部分中文词汇"),
]

for query, desc in search_tests:
    print(f"搜索 '{query}' ({desc}):")
    try:
        cursor = conn.execute("SELECT content FROM content_fts WHERE content MATCH ?", (query,))
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  ✓ {row['content']}")
        else:
            print(f"  ✗ 无结果")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
    print()

conn.close()
shutil.rmtree(temp_dir)
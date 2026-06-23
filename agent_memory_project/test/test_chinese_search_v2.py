"""修复后的中文搜索测试"""
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

for i, text in enumerate(test_data, 1):
    conn.execute("INSERT INTO content_fts(rowid, content) VALUES (?, ?)", (i, text))

print("=== 当前 FTS5 分词问题演示 ===\n")
print("数据库内容:")
for i, text in enumerate(test_data, 1):
    print(f"  {i}. {text}")
print("\n" + "="*50 + "\n")

# 测试各种搜索
search_tests = [
    ("Python", "英文关键词"),
    ("编程", "中文词汇 - 单字"),
    ("学习", "中文词汇"),
    ("机器", "中文词汇"),
    ("深度", "中文词汇"),
]

for query, desc in search_tests:
    print(f"搜索 '{query}' ({desc}):")
    try:
        # 注意：FTS5 MATCH 需要用单引号
        cursor = conn.execute(
            "SELECT content FROM content_fts WHERE content MATCH ?",
            (query,)
        )
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  ✓ 找到: {row['content']}")
        else:
            print(f"  ✗ 未找到任何结果")
    except Exception as e:
        print(f"  ✗ 查询错误: {e}")
    print()

# 展示实际分词结果
print("\n=== 查看实际存储的 token ===\n")

# 使用 FTS5 的 tokenize 函数
for text in test_data:
    print(f"文本: {text}")
    # 尝试解析每个字符
    tokens = []
    for char in text:
        try:
            cursor = conn.execute(
                "SELECT content FROM content_fts WHERE content MATCH ?",
                (char,)
            )
            if cursor.fetchone():
                tokens.append(char)
        except:
            pass
    print(f"  可匹配的字符: {tokens}")
    print()

conn.close()
shutil.rmtree(temp_dir)
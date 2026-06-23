"""直接展示 FTS5 的分词行为"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"

conn = sqlite3.connect(db_path)

# 创建默认 FTS5 表
conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")

# 插入不同类型的文本
test_data = [
    "Python programming is fun",           # 纯英文
    "我想学习Python编程",                   # 中英混合
    "Python入门教程推荐",                   # 中英混合
    "机器学习基础知识",                     # 纯中文
    "深度学习神经网络",                     # 纯中文
    "Python 和 Java 的区别",               # 空格分隔
    "推荐一些 Python 书籍",                 # 空格分隔
]

for i, text in enumerate(test_data, 1):
    conn.execute("INSERT INTO test_fts(rowid, content) VALUES (?, ?)", (i, text))

print("=== FTS5 默认分词器 (unicode61) 行为 ===\n")

# 通过 FTS5 的内置函数查看分词
print("使用 fts5_decode 查看 token:\n")

# 查询 FTS5 的内部数据结构
cursor = conn.execute("SELECT * FROM test_fts_data")
rows = cursor.fetchall()

print("FTS5 内部数据:")
for row in rows:
    print(f"  {row}")

print("\n" + "="*60 + "\n")

# 实际搜索测试
print("搜索测试:\n")

test_searches = [
    "Python",           # 英文
    "programming",      # 英文单词
    "学习",             # 中文
    "机器",             # 中文
    "Python OR 教程",   # OR 查询
]

for query in test_searches:
    print(f"查询: '{query}'")
    try:
        cursor = conn.execute(
            "SELECT content FROM test_fts WHERE content MATCH ?",
            (query,)
        )
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  ✓ {row[0]}")
        else:
            print(f"  ✗ 无结果")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
    print()

# 关键测试：插入带空格的中文
print("="*60 + "\n")
print("关键发现：空格对分词的影响\n")

conn.execute("DELETE FROM test_fts")
test_data_spaced = [
    "我想 学习 Python 编程",      # 空格分隔中文
    "Python 入门 教程 推荐",       # 空格分隔
    "机器 学习 基础 知识",         # 空格分隔中文
]

for i, text in enumerate(test_data_spaced, 1):
    conn.execute("INSERT INTO test_fts(rowid, content) VALUES (?, ?)", (i, text))
    print(f"插入: {text}")

print("\n搜索 '学习':")
cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH '学习'")
for row in cursor.fetchall():
    print(f"  ✓ {row[0]}")

print("\n搜索 'Python':")
cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH 'Python'")
for row in cursor.fetchall():
    print(f"  ✓ {row[0]}")

conn.close()
shutil.rmtree(temp_dir)
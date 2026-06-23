"""正确查看 FTS5 分词结果的方法"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"

conn = sqlite3.connect(db_path)

print("=== 正确查看 FTS5 分词结果的方法 ===\n")

# 创建 FTS5 表
conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")

# 插入测试数据
test_data = [
    "Python programming is fun",
    "Java development tools",
    "Python data science library",
]

for i, text in enumerate(test_data, 1):
    conn.execute("INSERT INTO test_fts(rowid, content) VALUES (?, ?)", (i, text))
    print(f"插入: {text}")

print("\n" + "="*60 + "\n")

# ========================================
# 方法 1: 直接读取 test_fts_data（无效）
# ========================================
print("方法 1: 直接读取 test_fts_data 表（❌ 无效）")
print("这是原始代码尝试的方法:\n")

cursor = conn.execute("SELECT * FROM test_fts_data")
rows = cursor.fetchall()
print("输出结果:")
for row in rows:
    print(f"  {row}")
print("\n问题:")
print("  ✗ 数据是二进制 BLOB，无法直接阅读")
print("  ✗ 不显示实际的 token 内容")
print("  ✗ 只是原始存储格式，需要解码\n")

# ========================================
# 方法 2: 查看 test_fts_content 表
# ========================================
print("="*60)
print("\n方法 2: 查看 test_fts_content 表（✓ 可读）")
print("这个表存储原始文本内容:\n")

cursor = conn.execute("SELECT * FROM test_fts_content")
rows = cursor.fetchall()
print("输出结果:")
for row in rows:
    print(f"  {row}")
print("\n说明:")
print("  ✓ 可以看到原始插入的文本")
print("  ✓ 但不显示分词后的 token\n")

# ========================================
# 方法 3: 查看 test_fts_docsize 表
# ========================================
print("="*60)
print("\n方法 3: 查看 test_fts_docsize 表")
print("这个表存储每个文档的 token 数量:\n")

cursor = conn.execute("SELECT * FROM test_fts_docsize")
rows = cursor.fetchall()
print("输出结果:")
for row in rows:
    print(f"  文档 rowid={row[0]}, token数量={row[1]}")
print("\n说明:")
print("  ✓ 可以看到每个文档有多少个 token")
print("  例如：'Python programming is fun' → 4个tokens\n")

# ========================================
# 方法 4: 使用查询反推 token（推荐）
# ========================================
print("="*60)
print("\n方法 4: 通过查询反推 token 列表（✓ 推荐）")
print("这是最实用的方法:\n")

# 获取所有唯一词汇
print("步骤 1: 提取所有可能的词汇")
all_words = set()
for text in test_data:
    words = text.lower().split()
    all_words.update(words)

print(f"候选词汇: {sorted(all_words)}\n")

# 验证每个词汇是否是 token
print("步骤 2: 验证每个词汇是否在 FTS5 索引中")
tokens = []
for word in sorted(all_words):
    cursor = conn.execute("SELECT content FROM test_fts WHERE content MATCH ?", (word,))
    results = cursor.fetchall()
    if results:
        tokens.append(word)
        matched_docs = [row[0] for row in results]
        print(f"  ✓ Token '{word}' → 匹配 {len(results)} 个文档")
        for doc in matched_docs:
            print(f"      - {doc}")
    else:
        print(f"  ✗ '{word}' 不是 token")

print(f"\n实际 token 列表: {tokens}\n")

# ========================================
# 方法 5: 查看 test_fts_idx 表（高级）
# ========================================
print("="*60)
print("\n方法 5: 查看 test_fts_idx 表（内部索引结构）")
print("这个表存储 token 的索引信息:\n")

cursor = conn.execute("SELECT * FROM test_fts_idx")
rows = cursor.fetchall()
print("输出结果:")
if rows:
    for row in rows:
        print(f"  segid={row[0]}, term={row[1]}, pgno={row[2]}")
else:
    print("  表为空（数据量小时不使用此表）")
print("\n说明:")
print("  这个表存储 token 的首字符索引")
print("  数据量大时才会使用\n")

conn.close()
shutil.rmtree(temp_dir)
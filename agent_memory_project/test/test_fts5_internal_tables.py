"""深入理解 FTS5 内部表结构"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("=== FTS5 内部表结构详解 ===\n")

# 1. 创建一个简单的 FTS5 表
print("步骤 1: 创建 FTS5 虚拟表")
conn.execute("""
    CREATE VIRTUAL TABLE my_fts
    USING fts5(content)
""")
print("  创建表: my_fts\n")

# 2. 查看数据库中的所有表
print("步骤 2: 查看数据库中实际创建的表")
cursor = conn.execute("""
    SELECT name, type, tbl_name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""")
tables = cursor.fetchall()
print("数据库中的表:")
for table in tables:
    print(f"  表名: {table['name']}, 类型: {table['type']}, 关联: {table['tbl_name']}")
print()

# 3. 插入测试数据
print("步骤 3: 插入测试数据")
test_data = [
    "Python programming",
    "Java development",
    "Python data science",
]

for i, text in enumerate(test_data, 1):
    conn.execute("INSERT INTO my_fts(rowid, content) VALUES (?, ?)", (i, text))
    print(f"  插入: rowid={i}, content='{text}'")
print()

# 4. 再次查看所有表（包括内部表）
print("\n步骤 4: 再次查看所有表（包含内部隐藏表）")
cursor = conn.execute("""
    SELECT name, type, tbl_name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""")
tables = cursor.fetchall()
print("所有表（包含内部表）:")
for table in tables:
    print(f"  表名: {table['name']}")
print()

# 5. 重点：FTS5 自动创建的内部表
print("\n步骤 5: FTS5 自动创建的内部辅助表\n")
print("FTS5 为每个虚拟表创建 3 个内部表:")
print("  1. <表名>_data    - 存储倒排索引数据")
print("  2. <表名>_idx     - 存储索引结构")
print("  3. <表名>_content - 存储原始内容（如果是外部内容表）")
print()

# 6. 查看 my_fts_data 表的内容
print("步骤 6: 查看 'my_fts_data' 表（倒排索引数据）")
try:
    cursor = conn.execute("SELECT * FROM my_fts_data")
    rows = cursor.fetchall()
    print(f"my_fts_data 表内容:")
    if rows:
        for row in rows:
            print(f"  行数据: {dict(row)}")
    else:
        print("  表为空或无法读取")
except Exception as e:
    print(f"  无法直接读取: {e}")
print()

# 7. 查看 my_fts_idx 表的内容
print("步骤 7: 查看 'my_fts_idx' 表（索引结构）")
try:
    cursor = conn.execute("SELECT * FROM my_fts_idx")
    rows = cursor.fetchall()
    print(f"my_fts_idx 表内容:")
    if rows:
        for row in rows:
            print(f"  行数据: {dict(row)}")
    else:
        print("  表为空或无法读取")
except Exception as e:
    print(f"  无法直接读取: {e}")
print()

# 8. 使用 FTS5 的专用函数查看分词结果
print("步骤 8: 使用 FTS5 专用函数分析分词")
print("\n方法 A: 使用 fts5_decode() 函数（如果可用）")
try:
    cursor = conn.execute("SELECT fts5_decode(1, 2)")
    print("  fts5_decode 可用")
except Exception as e:
    print(f"  fts5_decode 不可用: {e}")

print("\n方法 B: 通过查询推断分词结果")
print("测试搜索各个词汇，验证是否被正确分词:")
test_tokens = ["python", "programming", "java", "development", "data", "science"]
for token in test_tokens:
    cursor = conn.execute("SELECT content FROM my_fts WHERE content MATCH ?", (token,))
    results = cursor.fetchall()
    matched = [row['content'] for row in results]
    print(f"  Token '{token}' → 匹配到: {matched if matched else '无'}")
print()

# 9. 查看表的 schema
print("步骤 9: 查看各表的完整 schema")
for table_name in ['my_fts', 'my_fts_data', 'my_fts_idx']:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\n{table_name} 表的列结构:")
    for col in columns:
        print(f"  列: {col['name']}, 类型: {col['type']}")

conn.close()
shutil.rmtree(temp_dir)
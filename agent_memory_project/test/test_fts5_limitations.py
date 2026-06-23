"""FTS5 默认分词器的两大缺陷演示"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"

conn = sqlite3.connect(db_path)

print("="*70)
print("FTS5 默认分词器 unicode61 的两大缺陷分析")
print("="*70)

# ============================================
# 缺陷 1: 大小写处理问题
# ============================================
print("\n【缺陷 1】大小写处理问题\n")

conn.execute("CREATE VIRTUAL TABLE test_case USING fts5(content)")

test_cases = [
    "Python Programming",
    "python programming",
    "PYTHON PROGRAMMING",
]

for i, text in enumerate(test_cases, 1):
    conn.execute("INSERT INTO test_case(rowid, content) VALUES (?, ?)", (i, text))
    print(f"插入: '{text}'")

print("\n测试大小写敏感的搜索：")
search_tests = [
    ("Python", "大写 P"),
    ("python", "小写 p"),
    ("PYTHON", "全大写"),
    ("pYTHON", "混合大小写"),
]

for query, desc in search_tests:
    cursor = conn.execute("SELECT content FROM test_case WHERE content MATCH ?", (query,))
    results = cursor.fetchall()
    matched = [row[0] for row in results]
    print(f"  搜索 '{query}' ({desc}):")
    print(f"    → 匹配到 {len(results)} 条: {matched if matched else '无'}")

print("\n结论:")
print("  ✓ unicode61 默认大小写不敏感（默认行为）")
print("  ⚠️  但这不是问题，而是特性！对搜索有利")
print("  ⚠️  但如果需要精确匹配大小写，需要特殊配置")

conn.execute("DROP TABLE test_case")

# ============================================
# 缺陷 2: 中文长文切分问题（严重）
# ============================================
print("\n" + "="*70)
print("\n【缺陷 2】中文长文切分问题（严重问题）\n")

conn.execute("CREATE VIRTUAL TABLE test_chinese USING fts5(content)")

# 问题场景
chinese_problems = [
    ("我想学习Python编程", "无空格中文"),
    ("机器学习算法原理详解", "长句无空格"),
    ("深度学习神经网络模型", "技术术语"),
    ("自然语言处理技术应用", "连续中文"),
]

print("插入测试数据（无空格中文）:\n")
for i, (text, desc) in enumerate(chinese_problems, 1):
    conn.execute("INSERT INTO test_chinese(rowid, content) VALUES (?, ?)", (i, text))
    print(f"  {i}. '{text}' ({desc})")

print("\n测试中文词汇搜索（失败场景）：")
failed_searches = [
    ("学习", "常见词汇"),
    ("机器", "技术词汇"),
    ("深度", "技术词汇"),
    ("自然", "技术词汇"),
    ("语言", "常见词汇"),
    ("处理", "常见词汇"),
    ("算法", "技术词汇"),
]

for query, desc in failed_searches:
    cursor = conn.execute("SELECT content FROM test_chinese WHERE content MATCH ?", (query,))
    results = cursor.fetchall()
    if results:
        print(f"  ✓ '{query}' ({desc}): 匹配 {len(results)} 条")
    else:
        print(f"  ✗ '{query}' ({desc}): 无结果 ← 问题！")

print("\n问题总结:")
print("  ✗ unicode61 只按空格分割，连续中文视为一个 token")
print("  ✗ 无法识别中文词语边界")
print("  ✗ 长句中的词汇无法被检索")
print("  ✗ 中文搜索体验极差")

# ============================================
# 对比：有空格分隔的效果
# ============================================
print("\n" + "="*70)
print("\n对比：空格分隔的中文文本效果\n")

conn.execute("DELETE FROM test_chinese")

chinese_spaced = [
    "我想 学习 Python 编程",
    "机器 学习 算法 原理 详解",
    "深度 学习 神经网络 模型",
    "自然 语言 处理 技术 应用",
]

print("插入带空格的中文文本:\n")
for i, text in enumerate(chinese_spaced, 1):
    conn.execute("INSERT INTO test_chinese(rowid, content) VALUES (?, ?)", (i, text))
    print(f"  {i}. '{text}'")

print("\n测试同样的词汇搜索（成功场景）：")
for query, desc in failed_searches:
    cursor = conn.execute("SELECT content FROM test_chinese WHERE content MATCH ?", (query,))
    results = cursor.fetchall()
    if results:
        matched = [row[0] for row in results]
        print(f"  ✓ '{query}' ({desc}): 匹配 {len(results)} 条")
        for doc in matched:
            print(f"      - {doc}")
    else:
        print(f"  ✗ '{query}' ({desc}): 无结果")

print("\n结论:")
print("  ✓ 空格分隔可以解决中文分词问题")
print("  ⚠️  但这要求用户手动添加空格（不现实）")

conn.close()
shutil.rmtree(temp_dir)
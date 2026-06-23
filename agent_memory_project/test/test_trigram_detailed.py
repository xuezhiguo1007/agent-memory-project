"""修正：trigram 分词器的实际行为测试"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"
conn = sqlite3.connect(db_path)

print("="*70)
print("trigram tokenizer 实际行为详解")
print("="*70)

conn.execute("""
    CREATE VIRTUAL TABLE test_trigram
    USING fts5(content, tokenize='trigram')
""")

# 测试数据
test_text = "我想学习Python编程机器学习算法"
conn.execute("INSERT INTO test_trigram(rowid, content) VALUES (?, ?)", (1, test_text))

print(f"\n原文: '{test_text}'")
print(f"长度: {len(test_text)} 个字符\n")

# 展示 trigram 分词原理
print("trigram 分词原理（每3个字符为一个token）:")
trigrams = [test_text[i:i+3] for i in range(len(test_text)-2)]
print(f"生成的 tokens: {trigrams}")
print(f"Token 数量: {len(trigrams)}")
print()

# 测试不同长度词汇的搜索
print("测试不同长度词汇的搜索效果:\n")

test_searches = [
    ("学习", 2, "2个字符"),
    ("机器", 2, "2个字符"),
    ("算法", 2, "2个字符"),
    ("学习P", 3, "3个字符"),
    ("机器学", 3, "3个字符"),
    ("Python", 6, "6个字符"),
    ("学习Pyt", 7, "跨越中英文"),
    ("我想学", 3, "开头3字符"),
]

for query, length, desc in test_searches:
    cursor = conn.execute("SELECT content FROM test_trigram WHERE content MATCH ?", (query,))
    results = cursor.fetchall()

    # 检查是否在 trigrams 列表中
    is_token = query in trigrams

    print(f"搜索 '{query}' ({desc}, 长度={length}):")
    if results:
        print(f"  ✓ 匹配成功")
        if is_token:
            print(f"  ✓ 该词是完整的 trigram token")
        else:
            print(f"  ⚠️  匹配但不是完整 token（可能通过片段匹配）")
    else:
        print(f"  ✗ 无结果")
        if length < 3:
            print(f"  ✗ 原因: trigram 最小长度是3，无法匹配长度={length}的词")
        elif not is_token:
            print(f"  ✗ 原因: 不是文本中存在的片段")
    print()

print("="*70)
print("\n关键发现:\n")
print("1. trigram 的最小匹配长度是 3 个字符")
print("   → 2个汉字的词（如'学习'）无法被直接匹配 ✗")
print()
print("2. trigram 的分词是机械的，不考虑语义")
print("   → '学习P' 会被当作一个 token（跨语言混合）⚠️")
print()
print("3. trigram 可以匹配更长的词")
print("   → 'Python'（6字符）可以匹配 ✓")
print("   → 因为它包含多个 trigrams: 'Pyt', 'yth', 'tho', 'hon'")
print()
print("4. trigram 的适用场景:")
print("   → 不适合中文词汇搜索（中文词汇通常是2字）✗")
print("   → 适合英文搜索（英文单词通常≥3字母）✓")
print("   → 适合模糊匹配或全文搜索 ⚠️")
print()
print("="*70)

# 更实际的对比测试
print("\n实际场景对比测试:\n")

conn.execute("DELETE FROM test_trigram")

# 插入更多真实文本
real_texts = [
    "深度学习神经网络模型",
    "自然语言处理技术",
    "人工智能算法设计",
    "机器学习Python实现",
]

for i, text in enumerate(real_texts, 1):
    conn.execute("INSERT INTO test_trigram(rowid, content) VALUES (?, ?)", (i, text))
    print(f"插入: '{text}'")

print("\n测试实际搜索需求:\n")

common_searches = [
    ("深度学习", "4字词组"),
    ("神经网络", "4字词组"),
    ("自然语言", "4字词组"),
    ("人工智能", "4字词组"),
    ("机器学习", "4字词组"),
    ("Python", "英文"),
]

for query, desc in common_searches:
    cursor = conn.execute("SELECT content FROM test_trigram WHERE content MATCH ?", (query,))
    results = cursor.fetchall()
    if results:
        print(f"✓ '{query}' ({desc}): 匹配 {len(results)} 条")
        for row in results:
            print(f"    - {row[0]}")
    else:
        print(f"✗ '{query}' ({desc}): 无结果")

conn.close()
shutil.rmtree(temp_dir)
"""解决 FTS5 中文分词问题的三种方案对比"""
import sqlite3
from pathlib import Path
import tempfile
import shutil

# 尝试导入 jieba（如果没有安装会提示）
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("⚠️  jieba 未安装，方案1将被跳过")
    print("   安装命令: pip install jieba\n")

temp_dir = tempfile.mkdtemp()
db_path = Path(temp_dir) / "test.db"
conn = sqlite3.connect(db_path)

test_texts = [
    "我想学习Python编程",
    "机器学习算法原理详解",
    "深度学习神经网络模型",
    "自然语言处理技术应用",
]

print("="*70)
print("FTS5 中文分词问题 - 三种解决方案对比")
print("="*70)

# ============================================
# 方案 1: jieba 分词预处理（最佳方案）
# ============================================
if JIEBA_AVAILABLE:
    print("\n【方案 1】jieba 分词预处理 ⭐⭐⭐⭐⭐\n")

    conn.execute("CREATE VIRTUAL TABLE solution_jieba USING fts5(content)")

    print("使用 jieba 分词处理文本:\n")
    for i, text in enumerate(test_texts, 1):
        # jieba 分词
        tokens = list(jieba.cut(text))
        spaced_text = " ".join(tokens)

        conn.execute("INSERT INTO solution_jieba(rowid, content) VALUES (?, ?)", (i, spaced_text))
        print(f"原文: '{text}'")
        print(f"分词: '{spaced_text}'")
        print(f"Token: {tokens}")
        print()

    print("测试搜索效果:")
    test_words = ["学习", "机器", "深度", "算法", "语言", "处理", "Python"]

    for word in test_words:
        cursor = conn.execute("SELECT content FROM solution_jieba WHERE content MATCH ?", (word,))
        results = cursor.fetchall()
        if results:
            print(f"  ✓ '{word}': 匹配 {len(results)} 条")
            for row in results:
                print(f"      - {row[0]}")
        else:
            print(f"  ✗ '{word}': 无结果")

    print("\n优点:")
    print("  ✓ 精确的中文分词")
    print("  ✓ 支持自定义词典")
    print("  ✓ 搜索效果最佳")
    print("  ✓ 业界标准方案")
    print("\n缺点:")
    print("  ⚠️  需要依赖 jieba 库")
    print("  ⚠️  插入前需要预处理")
    print("  ⚠️  分词结果不可逆（无法还原原文）")

    conn.execute("DROP TABLE solution_jieba")

# ============================================
# 方案 2: trigram tokenizer（简单方案）
# ============================================
print("\n" + "="*70)
print("\n【方案 2】trigram tokenizer ⭐⭐⭐\n")

conn.execute("""
    CREATE VIRTUAL TABLE solution_trigram
    USING fts5(content, tokenize='trigram')
""")

print("使用 trigram 分词（每3个字符为一个token):\n")
for i, text in enumerate(test_texts, 1):
    conn.execute("INSERT INTO solution_trigram(rowid, content) VALUES (?, ?)", (i, text))
    print(f"插入: '{text}'")
    # 展示 trigram 分词效果
    trigrams = [text[j:j+3] for j in range(len(text)-2)]
    print(f"Trigram tokens: {trigrams}")
    print()

print("测试搜索效果:")
test_words = ["学习", "机器", "深度", "算法", "语言", "处理", "Python"]

for word in test_words:
    cursor = conn.execute("SELECT content FROM solution_trigram WHERE content MATCH ?", (word,))
    results = cursor.fetchall()
    if results:
        print(f"  ✓ '{word}': 匹配 {len(results)} 条")
        for row in results:
            print(f"      - {row[0]}")
    else:
        print(f"  ✗ '{word}': 无结果")

print("\n优点:")
print("  ✓ 无需额外依赖")
print("  ✓ 配置简单（一行代码）")
print("  ✓ 保留原文格式")
print("  ✓ 对英文和中文都有效")
print("\n缺点:")
print("  ⚠️  Token 数量多（存储空间大）")
print("  ⚠️  无法精确匹配词语边界")
print("  ⚠️  可能匹配到不相关的片段")

conn.execute("DROP TABLE solution_trigram")

# ============================================
# 方案 3: 空格分隔 + 用户教育（不推荐）
# ============================================
print("\n" + "="*70)
print("\n【方案 3】要求用户手动添加空格 ⭐\n")

conn.execute("CREATE VIRTUAL TABLE solution_manual USING fts5(content)")

print("要求用户输入时添加空格:\n")
manual_texts = [
    "我想 学习 Python 编程",
    "机器 学习 算法 原理 详解",
    "深度 学习 神经网络 模型",
    "自然 语言 处理 技术 应用",
]

for i, text in enumerate(manual_texts, 1):
    conn.execute("INSERT INTO solution_manual(rowid, content) VALUES (?, ?)", (i, text))
    print(f"插入: '{text}'")

print("\n测试搜索效果:")
for word in test_words:
    cursor = conn.execute("SELECT content FROM solution_manual WHERE content MATCH ?", (word,))
    results = cursor.fetchall()
    if results:
        print(f"  ✓ '{word}': 匹配 {len(results)} 条")
    else:
        print(f"  ✗ '{word}': 无结果")

print("\n优点:")
print("  ✓ 无需修改代码")
print("\n缺点:")
print("  ✗ 用户体验极差")
print("  ✗ 不现实的解决方案")
print("  ✗ 无法保证用户正确使用")

conn.close()
shutil.rmtree(temp_dir)

# ============================================
# 总结建议
# ============================================
print("\n" + "="*70)
print("\n【推荐方案】\n")
print("根据不同场景的推荐:")
print()
print("1. 生产环境 + 中文为主:")
print("   → 使用方案 1 (jieba 分词)")
print("   → 最佳搜索体验")
print()
print("2. 快速原型 + 多语言:")
print("   → 使用方案 2 (trigram)")
print("   → 配置简单，开箱即用")
print()
print("3. 当前 session_search_service.py 应该:")
print("   → 升级为 jieba 分词方案")
print("   → 在 append_event() 中集成分词逻辑")
print()
print("="*70)
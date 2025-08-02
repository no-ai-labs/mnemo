"""Test different embedding models."""

from mnemo.core.embeddings import MnemoEmbeddings

print("🧪 Testing embedding models...\n")

# Test 1: Default (should use sentence transformers now)
print("1️⃣ Default configuration:")
embeddings = MnemoEmbeddings()
test_text = "Spring Boot는 자바 기반의 웹 프레임워크입니다."
result = embeddings.embed_query(test_text)
print(f"Embedding type: {embeddings.embedding_type}")
print(f"Embedding dimensions: {len(result)}")
print(f"First 5 values: {result[:5]}")

print("\n2️⃣ Testing multilingual support:")
texts = [
    "Hello world!",  # English
    "안녕하세요!",    # Korean
    "你好世界！",      # Chinese
    "Bonjour le monde!",  # French
    "Привет мир!",  # Russian
]

for text in texts:
    embedding = embeddings.embed_query(text)
    print(f"'{text}' -> dims: {len(embedding)}, sum: {sum(embedding):.3f}")

print("\n3️⃣ Testing different models:")
models = [
    "paraphrase-multilingual-mpnet-base-v2",  # Default multilingual
    "sentence-transformers/all-MiniLM-L6-v2",  # Fast English
    # "jhgan/ko-sroberta-multitask",  # Korean specialized (if you want)
]

for model in models:
    try:
        emb = MnemoEmbeddings(sentence_transformer_model=model)
        test_embedding = emb.embed_query("테스트")
        print(f"✅ {model}: {len(test_embedding)} dimensions")
    except Exception as e:
        print(f"❌ {model}: {e}")

print("\n✨ Recommendation for 드리머:")
print("- 'paraphrase-multilingual-mpnet-base-v2' is great for Korean + English!")
print("- Fast, local, and supports 50+ languages")
print("- No API keys needed! 🎉")
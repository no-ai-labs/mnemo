"""Test E5-Large model performance."""

import time
from mnemo.core.embeddings import MnemoEmbeddings

print("🚀 Testing intfloat/multilingual-e5-large model...\n")

# Note: First run will download the model (~2GB)
print("⏬ Initializing model (first run will download ~2GB)...")
start = time.time()
embeddings = MnemoEmbeddings()
print(f"✅ Model loaded in {time.time() - start:.2f} seconds")
print(f"📊 Model type: {embeddings.embedding_type}")

# Test embedding
test_texts = [
    "Spring Boot는 자바 기반의 웹 애플리케이션 프레임워크입니다.",
    "드리머는 Python을 배우고 있는 한국 개발자입니다.",
    "Mnemo is a universal memory system for AI assistants.",
    "人工智能正在改变世界。",  # Chinese
    "L'intelligence artificielle change le monde.",  # French
]

print("\n🧪 Testing embeddings:")
for text in test_texts:
    start = time.time()
    embedding = embeddings.embed_query(text)
    elapsed = time.time() - start
    print(f"\n📝 Text: '{text[:50]}...'")
    print(f"   Dimensions: {len(embedding)}")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   First 5 values: {embedding[:5]}")

# Test similarity
print("\n🔍 Testing semantic similarity:")
query = "스프링부트 개발자"
query_emb = embeddings.embed_query(query)

print(f"\nQuery: '{query}'")
for text in test_texts[:3]:  # Test first 3 texts
    text_emb = embeddings.embed_query(text)
    # Simple cosine similarity
    import numpy as np
    similarity = np.dot(query_emb, text_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(text_emb))
    print(f"  vs '{text[:30]}...' = {similarity:.3f}")

print("\n✨ E5-Large 모델 특징:")
print("- 1024차원 (더 풍부한 표현력)")
print("- 100개 언어 지원")
print("- 검색 최적화")
print("- 최신 모델 (2023년)")
print("- 크기: ~2GB (한 번만 다운로드)")
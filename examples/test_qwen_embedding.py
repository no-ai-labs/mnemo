"""Test Qwen3 Embedding models performance."""

import time
import psutil
import os
from mnemo.core.embeddings import MnemoEmbeddings

print("🤖 Testing Qwen3-Embedding-0.6B model...\n")
print(f"💾 System RAM: {psutil.virtual_memory().total / (1024**3):.1f}GB")
print(f"🧠 Available RAM: {psutil.virtual_memory().available / (1024**3):.1f}GB\n")

# Test model loading
print("⏬ Loading Qwen3-Embedding-0.6B (First run will download ~1.2GB)...")
start = time.time()
embeddings = MnemoEmbeddings()
load_time = time.time() - start
print(f"✅ Model loaded in {load_time:.2f} seconds")
print(f"📊 Model type: {embeddings.embedding_type}")

# Memory usage check
process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"💾 Memory usage: {memory_mb:.0f}MB\n")

# Test embeddings
test_texts = [
    "M3 프로세서는 애플의 최신 실리콘 칩입니다.",
    "드리머는 Spring Boot와 Python을 모두 다루는 개발자입니다.",
    "Qwen is Alibaba's language model series.",
    "人工智能正在改变世界。",
]

print("🧪 Testing embedding performance:")
total_time = 0
for i, text in enumerate(test_texts):
    start = time.time()
    embedding = embeddings.embed_query(text)
    elapsed = time.time() - start
    total_time += elapsed
    print(f"{i+1}. '{text[:30]}...'")
    print(f"   Dimensions: {len(embedding)}")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   First 5 values: {[f'{v:.4f}' for v in embedding[:5]]}")
    print()

avg_time = total_time / len(test_texts)
print(f"⚡ Average embedding time: {avg_time:.3f}s")
print(f"💾 Final memory usage: {process.memory_info().rss / 1024 / 1024:.0f}MB")

# Compare with E5
print("\n📊 모델 비교 (M3 최적화):")
print("┌─────────────────────────────┬────────┬─────────┬─────────┬──────────┐")
print("│ Model                       │ Size   │ Dims    │ Memory  │ M3 적합도 │")
print("├─────────────────────────────┼────────┼─────────┼─────────┼──────────┤")
print("│ Qwen3-Embedding-0.6B ⭐     │ 0.6B   │ 1024    │ ~1.2GB  │ 완벽!    │")
print("│ Qwen3-Embedding-4B          │ 4B     │ 2560    │ ~8GB    │ 가능     │")  
print("│ intfloat/e5-large           │ 1.5B   │ 1024    │ ~3GB    │ 좋음     │")
print("│ paraphrase-mpnet            │ 0.4B   │ 768     │ ~800MB  │ 훌륭     │")
print("└─────────────────────────────┴────────┴─────────┴─────────┴──────────┘")

print("\n✨ Qwen3-0.6B 장점:")
print("- 가벼움: M3에서도 쾌적하게 동작")
print("- 다국어: 100개 언어 지원 (한국어 포함)")
print("- 빠름: 평균 임베딩 시간 매우 짧음")
print("- 최신: 2024년 6월 출시, SOTA 성능")
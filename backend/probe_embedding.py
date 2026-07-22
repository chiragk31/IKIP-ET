"""
Probe the exact signature of genai.embed_content() in google-generativeai 0.8.3
and test output_dimensionality with gemini-embedding-001.
"""
import inspect
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

# 1. Check signature
print("=== embed_content signature ===")
sig = inspect.signature(genai.embed_content)
for name, param in sig.parameters.items():
    print(f"  {name}: default={param.default}")

# 2. Test without output_dimensionality (baseline — should be 3072)
print("\n=== Test without output_dimensionality ===")
try:
    res = genai.embed_content(
        model="models/gemini-embedding-001",
        content="pump P-101 quarterly maintenance",
        task_type="retrieval_document",
    )
    print(f"Dimension: {len(res['embedding'])}")
except Exception as e:
    print(f"FAILED: {e}")

# 3. Test WITH output_dimensionality=768
print("\n=== Test with output_dimensionality=768 ===")
try:
    res = genai.embed_content(
        model="models/gemini-embedding-001",
        content="pump P-101 quarterly maintenance",
        task_type="retrieval_document",
        output_dimensionality=768,
    )
    print(f"Dimension: {len(res['embedding'])}")
    print(f"First 5 values: {res['embedding'][:5]}")
except Exception as e:
    print(f"FAILED: {e}")

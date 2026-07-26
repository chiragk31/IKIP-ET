"""
Asset Intelligence Module

Epic 9 — Asset Intelligence.

Pure aggregation layer. This module NEVER:
  - Performs document parsing
  - Performs OCR
  - Generates embeddings
  - Writes to Neo4j
  - Calls Pinecone directly

It ONLY:
  - Delegates graph queries to GraphRepository (Epic 5)
  - Delegates document retrieval to HybridSearchService (Epic 7)
  - Assembles the results into Asset 360 profiles
"""

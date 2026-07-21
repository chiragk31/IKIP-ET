"""
Graph Module — Knowledge Graph Builder (Epic 5)

Converts NormalizedKnowledgeObjects (Epic 4 output) into
Neo4j nodes and relationships.

Public interface:
    GraphService  — main orchestrator (use via DI: get_graph_service())
    GraphRepository — Neo4j CRUD (use via DI: get_graph_repository())
"""

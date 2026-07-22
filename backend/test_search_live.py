import asyncio
from app.core.dependencies import get_hybrid_search_service, get_llm_service, get_search_service, get_graph_repository
from app.search.models import HybridSearchQuery

async def main():
    llm = get_llm_service()
    epic6 = get_search_service()
    graph = get_graph_repository()
    
    svc = get_hybrid_search_service(llm_service=llm, epic6_search_service=epic6, graph_repo=graph)
    
    query = HybridSearchQuery(query="What happens when P-101 fails?", expand_graph=True)
    res = await svc.search(query)
    print("Found", res.total_results, "results")
    for chunk in res.chunks:
        print("-", chunk.chunk_id, chunk.score)
    for node in res.graph_nodes:
        print("Graph Node:", node.node_name, node.relationship)

if __name__ == "__main__":
    asyncio.run(main())

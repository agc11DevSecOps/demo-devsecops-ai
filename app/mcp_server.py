"""Local stdio MCP server for the synthetic Ops Copilot demo.

Started as a subprocess by the demo client inside the restricted container. It
owns an in-memory Qdrant index of approved documents and never performs a
high-impact action itself: ``delete_branch`` only returns a refusal, so the
caller must decide through the tool boundary.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from app.demo import _VECTOR_DIM, _embedding

TRUSTED_DOCS: dict[str, str] = {
    "rollback": "Rollback procedure: revert the release and drain traffic.",
    "payments": "Payments deployment runbook: blue/green rollout with a canary.",
}


def _build_index():
    from qdrant_client import QdrantClient, models

    client = QdrantClient(":memory:")
    client.create_collection("docs", vectors_config=models.VectorParams(size=_VECTOR_DIM, distance=models.Distance.COSINE))
    client.upsert(
        "docs",
        points=[
            models.PointStruct(id=index, vector=_embedding(text), payload={"doc": name, "writer": "trusted", "text": text})
            for index, (name, text) in enumerate(TRUSTED_DOCS.items())
        ],
    )
    return client


_CLIENT = _build_index()
server = MCPServer("ops-copilot-docs")


@server.tool()
def search_docs(query: str) -> str:
    """Search approved synthetic documents and return the matching text."""
    hits = _CLIENT.query_points("docs", query=_embedding(query), limit=3).points
    return "\n".join(str(hit.payload["text"]) for hit in hits if hit.payload)


@server.tool()
def delete_branch(repo: str, branch: str) -> str:
    """Request deletion of a named branch; the server never deletes on its own."""
    return f"refused: delete_branch({repo}/{branch}) requires an out-of-band approval"


if __name__ == "__main__":
    server.run("stdio")

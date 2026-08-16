"""
Query the healthcare Chroma collection and return structured records
(record_id, record_text, metadata, distance) instead of plain text,
so downstream verification has what it needs.
"""
import sys, os
from typing import List, Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils import embedding_functions
import config

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL_NAME
        )
        _collection = _client.get_collection(
            name=config.CHROMA_COLLECTION_NAME, embedding_function=embedding_fn
        )
    return _collection


def retrieve(query: str, top_k: int = None) -> List[Dict[str, Any]]:
    """
    Returns a list of:
      {"record_id": str, "record_text": str, "metadata": dict, "distance": float}
    """
    top_k = top_k or config.DEFAULT_TOP_K
    collection = _get_collection()
    result = collection.query(query_texts=[query], n_results=top_k)

    records = []
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for i in range(len(ids)):
        records.append({
            "record_id": metadatas[i].get("record_id", ids[i]),
            "record_text": metadatas[i].get("record_text", documents[i]),
            "metadata": metadatas[i],
            "distance": distances[i],
        })
    return records


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "patients diagnosed with diabetes"
    results = retrieve(q, top_k=5)
    print(f"Query: {q}\n")
    for i, r in enumerate(results, start=1):
        print(f"[{i}] {r['record_id']}  (distance={r['distance']:.4f})")
        print(f"    {r['record_text']}\n")

"""
Build the ChromaDB vector store for the healthcare dataset, with
metadata that carries everything needed for downstream blockchain /
Merkle verification (record_id, record_text, hash_hex).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils import embedding_functions

from hashing.healthcare_hashing import load_records_with_ids
import config

BATCH_SIZE = 500  # Chroma/sqlite has a practical per-call parameter limit;
                   # batching also gives visible progress on a 55,500-row dataset.


def _clean(value) -> str:
    if value is None or str(value).strip() == "":
        return "N/A"
    return str(value)


def build_database():
    records = load_records_with_ids(config.DATASET_CSV_PATH)
    print(f"[build_healthcare_db] {len(records)} records loaded from CSV.")

    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.EMBEDDING_MODEL_NAME
    )

    # Recreate the collection each run so the DB always matches the
    # current CSV / record_text format exactly.
    try:
        client.delete_collection(config.CHROMA_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]
        ids = [r["record_id"] for r in batch]
        documents = [r["record_text"] for r in batch]
        metadatas = [
            {
                "record_id": r["record_id"],
                "record_text": r["record_text"],
                "medical_condition": _clean(r["Medical Condition"]),
                "hospital": _clean(r["Hospital"]),
                "admission_type": _clean(r["Admission Type"]),
                "test_results": _clean(r["Test Results"]),
                "hash_hex": r["hash_hex"],
            }
            for r in batch
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[build_healthcare_db] Indexed {start + len(batch)}/{len(records)}")

    print(f"[build_healthcare_db] Done. Collection '{config.CHROMA_COLLECTION_NAME}' "
          f"has {collection.count()} documents.")


if __name__ == "__main__":
    build_database()

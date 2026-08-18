import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chromadb
from chromadb.utils import embedding_functions
from verification.verify_retrieved_record import verify_record_complete
import config

target_id = "MaRkWESt_10032022_014060"   # <-- use the SAME id you tampered

client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL_NAME)
collection = client.get_collection(config.CHROMA_COLLECTION_NAME, embedding_function=ef)

result = collection.get(ids=[target_id], include=["documents", "metadatas"])
record = {
    "record_id": target_id,
    "record_text": result["metadatas"][0]["record_text"],
    "metadata": result["metadatas"][0],
}
verification = verify_record_complete(record)
print("\n".join(verification.to_evidence_lines()))
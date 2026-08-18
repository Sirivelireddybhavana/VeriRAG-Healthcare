import chromadb
from chromadb.utils import embedding_functions
from hashing.healthcare_hashing import hash_record_hex
import config

client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL_NAME)
collection = client.get_collection(config.CHROMA_COLLECTION_NAME, embedding_function=ef)

target_id = "MaRkWESt_10032022_014060"  # <-- replace with a real record_id
original = collection.get(ids=[target_id], include=["documents", "metadatas"])
tampered_text = original["documents"][0].replace("Age: 57", "Age: 99")
tampered_hash = hash_record_hex(tampered_text)
meta = original["metadatas"][0]
meta["record_text"] = tampered_text
meta["hash_hex"] = tampered_hash

collection.update(ids=[target_id], documents=[tampered_text], metadatas=[meta])
print("Tampered:", target_id)
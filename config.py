"""
Central configuration for VeriRAG (healthcare domain).

Secrets (PRIVATE_KEY) are loaded from a local, git-ignored `.env`
file -- see `.env.example`. Never hardcode a private key in source.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- Dataset ----
# Override with DATASET_CSV_PATH in .env if you want to point at the
# small bundled sample (dataset/healthcare/healthcare_dataset_sample.csv)
# for a quick smoke test before running against the full 55,500-row file.
DATASET_CSV_PATH = os.getenv(
    "DATASET_CSV_PATH",
    os.path.join(BASE_DIR, "dataset", "healthcare", "healthcare_dataset.csv"),
)

# ---- Blockchain (Ganache) ----
GANACHE_RPC_URL = os.getenv("GANACHE_RPC_URL", "http://127.0.0.1:8545")
SOLC_VERSION = "0.8.20"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # set this in .env, NOT here

HASH_REGISTRY_ADDRESS_PATH = os.path.join(
    BASE_DIR, "blockchain", "hash_registry_address.json"
)
MERKLE_REGISTRY_ADDRESS_PATH = os.path.join(
    BASE_DIR, "blockchain", "merkle_registry_address.json"
)

# Number of individual record hashes to register on HashRegistry as a
# demo subset (storing all 55,500 individually is impractical on a
# local chain -- the Merkle root is what actually scales to the full
# dataset). Set to 0 to register everything (not recommended).
HASH_REGISTRY_SAMPLE_SIZE = int(os.getenv("HASH_REGISTRY_SAMPLE_SIZE", "200"))

# ---- Merkle tree artifacts ----
MERKLE_DIR = os.path.join(BASE_DIR, "merkle")
MERKLE_TREE_PATH = os.path.join(MERKLE_DIR, "merkle_tree.pkl")
MERKLE_INDEX_PATH = os.path.join(MERKLE_DIR, "merkle_index.json")
MERKLE_ROOT_PATH = os.path.join(MERKLE_DIR, "merkle_root.txt")

# ---- Vector DB (Chroma) ----
CHROMA_DB_PATH = os.path.join(BASE_DIR, "vector_db", "healthcare_chroma_db")
CHROMA_COLLECTION_NAME = "healthcare_records"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ---- Retrieval ----
DEFAULT_TOP_K = 5

# ---- LLM (Ollama) ----
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b")

# ---- Flask ----
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

import chromadb
from chromadb.utils import embedding_functions
from seed_data import MENU

_client = chromadb.PersistentClient(path="../data/chroma")
_embed = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"   # local, free
)

def build_menu_collection():
    # Fresh build each run keeps it simple during dev
    try:
        _client.delete_collection("menu")
    except Exception:
        pass
    col = _client.create_collection("menu", embedding_function=_embed)
    col.add(
        documents=[m["text"] for m in MENU],
        ids=[m["id"] for m in MENU],
        metadatas=[{"name": m["name"]} for m in MENU],
    )
    return col

def get_menu_collection():
    return _client.get_collection("menu", embedding_function=_embed)

def search_menu(query: str, k: int = 3):
    col = get_menu_collection()
    res = col.query(query_texts=[query], n_results=k)
    return res["documents"][0]

from pathlib import Path

from langchain.embeddings import init_embeddings
from langchain_community.document_loaders import TextLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

POLICY_FILE = Path(__file__).resolve().parent.parent / "data" / "loan_policy.txt"
EMBEDDING_MODEL = "ollama:nomic-embed-text"


def build_index(chunk_size: int = 300, chunk_overlap: int = 50) -> InMemoryVectorStore:
    """Load, split, embed and store the loan policy. Returns a searchable store."""

    chunk_overlap = min(chunk_overlap, chunk_size // 6)

    docs = TextLoader(str(POLICY_FILE), encoding="utf-8").load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(docs)

    embeddings = init_embeddings(EMBEDDING_MODEL)
    store = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)

    return store


if __name__ == "__main__":
    store = build_index()
    print("Chunks stored:", len(store.store))

    top = store.similarity_search("How soon is the money paid out?", k=1)[0]
    print("Top result:")
    print(top.page_content)

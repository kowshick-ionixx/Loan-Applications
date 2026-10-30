from pathlib import Path

from langchain.embeddings import init_embeddings
from langchain_community.document_loaders import TextLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

POLICY_FILE = Path(__file__).resolve().parent.parent / "data" / "loan_policy.txt"


docs = TextLoader(str(POLICY_FILE), encoding="utf-8").load()
embeddings = init_embeddings("ollama:nomic-embed-text")

question = "What are the prepayment charges?"


for size in [80, 300, 2000]:

    overlap = min(50, size // 6)

    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    chunks = splitter.split_documents(docs)

    store = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)
    results = store.similarity_search(question, k=3)

    print("=" * 60)
    print(f"chunk_size={size}  chunk_overlap={overlap}  total chunks={len(chunks)}")
    print("=" * 60)

    for i, hit in enumerate(results, start=1):
        print(f"--- Result {i} ({len(hit.page_content)} characters) ---")
        print(hit.page_content)
        print()

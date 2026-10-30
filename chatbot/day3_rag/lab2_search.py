from pathlib import Path

from langchain.embeddings import init_embeddings
from langchain_community.document_loaders import TextLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

POLICY_FILE = Path(__file__).resolve().parent.parent / "data" / "loan_policy.txt"


docs = TextLoader(str(POLICY_FILE), encoding="utf-8").load()
splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = splitter.split_documents(docs)


embeddings = init_embeddings("ollama:nomic-embed-text")


store = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)


question = "How soon is the money paid out?"
results = store.similarity_search(question, k=3)

print("Question:", question)
print()

for i, hit in enumerate(results, start=1):
    print(f"--- Result {i} ---")
    print(hit.page_content)
    print()

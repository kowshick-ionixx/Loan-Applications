from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

POLICY_FILE = Path(__file__).resolve().parent.parent / "data" / "loan_policy.txt"

docs = TextLoader(str(POLICY_FILE), encoding="utf-8").load()


splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = splitter.split_documents(docs)


print("Number of chunks:", len(chunks))
print()

for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i} ({len(chunk.page_content)} characters) ---")
    print(chunk.page_content)
    print()

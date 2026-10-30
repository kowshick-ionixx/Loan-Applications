from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_community.document_loaders import TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

POLICY_FILE = Path(__file__).resolve().parent.parent / "data" / "loan_policy.txt"


docs = TextLoader(str(POLICY_FILE), encoding="utf-8").load()
splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
chunks = splitter.split_documents(docs)

embeddings = init_embeddings("ollama:nomic-embed-text")
store = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)


model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a loan policy assistant. "
            "Answer ONLY from the context below. "
            "Cite the section number for every fact, like (5.1). "
            "If the answer is not in the context, say: I could not find this in the policy. "
            "Do not guess.\n\n"
            "Context:\n{context}",
        ),
        ("human", "{question}"),
    ]
)

chain = prompt | model


def ask(question: str) -> str:

    hits = store.similarity_search(question, k=3)

    context = "\n\n".join(hit.page_content for hit in hits)

    reply = chain.invoke({"context": context, "question": question})
    return reply.content


questions = [
    "How long until disbursal?",
    "What is the minimum age?",
    "What is the processing fee?",
]

for q in questions:
    print("Q:", q)
    print("A:", ask(q))
    print()

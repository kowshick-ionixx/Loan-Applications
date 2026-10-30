from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from policy_index import build_index
from pydantic import BaseModel, Field

load_dotenv()

NOT_FOUND = "I could not find this in the policy."


class PolicyAnswer(BaseModel):
    answer: str = Field(description="The answer, using only the context")
    sections: list[str] = Field(
        default_factory=list,
        description="Section numbers used, like ['3.2']. Empty list if not found.",
    )


model = init_chat_model("ollama:qwen3.5:9b", reasoning=False, temperature=0)
answer_sheet = model.with_structured_output(PolicyAnswer)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a loan policy assistant. "
            "Answer ONLY from the context below. Do not use outside knowledge and do not guess. "
            "List every section number you used, like 3.2, in 'sections'. "
            f"If the answer is not in the context, reply exactly: {NOT_FOUND} "
            "and leave 'sections' empty.\n\n"
            "Context:\n{context}",
        ),
        ("human", "{question}"),
    ]
)

chain = prompt | answer_sheet


default_store = build_index()


def ask_policy(question: str, store: InMemoryVectorStore = None) -> PolicyAnswer:
    """Answer a question from the loan policy. Returns the answer and the sections used."""
    if store is None:
        store = default_store

    hits = store.similarity_search(question, k=3)

    context = "\n\n".join(hit.page_content for hit in hits)

    return chain.invoke({"context": context, "question": question})


if __name__ == "__main__":
    for q in ["How long until disbursal?", "What is the policy on gold loans?"]:
        result = ask_policy(q)
        print("Q:       ", q)
        print("Answer:  ", result.answer)
        print("Sections:", result.sections)
        print()

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False)

question = HumanMessage("What documents do I need to apply for a personal loan?")

formal = SystemMessage(
    "You are a bank loan officer. Reply in a formal, professional tone. "
    "Keep it under 60 words."
)
casual = SystemMessage(
    "You are a friendly buddy who works at a bank. Reply casually, like a text "
    "message to a friend. Keep it under 60 words."
)

formal_reply = model.invoke([formal, question])
casual_reply = model.invoke([casual, question])

print("=== FORMAL ===")
print(formal_reply.content)
print("\n=== CASUAL ===")
print(casual_reply.content)

print("\nReply type:", type(formal_reply).__name__)

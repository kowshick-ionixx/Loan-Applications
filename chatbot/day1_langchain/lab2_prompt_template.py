from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a loan desk assistant. Summarise the customer's email "
                "in ONE short sentence. Do not add anything they did not say."
            ),
        ),
        ("human", "{email}"),
    ]
)

emails = [
    "Hi, I'm Ramesh Kumar. I need a loan of 5 lakh rupees for 3 years to renovate my house.",
    "need money urgently for my shop, around 2 lakhs, can repay in 18 months. - Imran",
    "Good morning, I want to know if I can get a loan for buying a two-wheeler. My name is Priya.",
]

# See what the template produces before it reaches the model
print(prompt.invoke({"email": emails[0]}).to_messages())
print()

for i, email in enumerate(emails, start=1):
    messages = prompt.invoke({"email": email})
    reply = model.invoke(messages)
    print(f"{i}. {reply.content}")

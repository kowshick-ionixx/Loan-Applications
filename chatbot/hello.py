from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()
model = init_chat_model("ollama:qwen3.5:9b", reasoning=False)
print(model.invoke("Say hello in one short sentence.").content)

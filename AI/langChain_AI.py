from langchain_ollama import OllamaLLM
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Создаём LLM с Ollama
llm = OllamaLLM(model="llama3")  # Модель должна быть загружена в Ollama

# Память для диалога
memory = ConversationBufferMemory()

# Цепочка общения
conversation = ConversationChain(
    llm=llm,
    memory=memory
)

print("LangChain тест. Напиши 'выход' чтобы закончить.\n")

while True:
    user_input = input("Ты: ")
    if user_input.lower() in ["выход", "quit", "exit"]:
        break
    response = conversation.predict(input=user_input)
    print("ИИ:", response)
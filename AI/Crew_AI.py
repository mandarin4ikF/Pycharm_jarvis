from crewai import Agent, Crew, Task, LLM

# LLM Ollama
llm = LLM(model="ollama/llama3", base_url="http://localhost:11434")

# Агент
assistant = Agent(
    role="Ассистент",
    goal="Отвечать на вопросы пользователя на русском",
    backstory="Ты полезный умный помощник, как Джарвис",
    llm=llm
)

# Задача
task = Task(
    description="Общение с пользователем и ответ на вопросы",
    expected_output="Развернутый ответ на русском языке",
    agent=assistant
)

# Экипаж
crew = Crew(
    agents=[assistant],
    tasks=[task]
)

print("CrewAI тест. Напиши 'выход' чтобы закончить.\n")

while True:
    user_input = input("Ты: ")
    if user_input.lower() in ["выход", "quit", "exit"]:
        break
    task.description = user_input
    result = crew.kickoff()
    print("ИИ:", result)

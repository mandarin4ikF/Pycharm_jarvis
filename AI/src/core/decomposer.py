import logging
from typing import List, Dict, Any, Optional


from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger(__name__)


# 1. Определяем схему вывода с помощью Pydantic. Это наш "контракт" с LLM.
class Task(BaseModel):
    id: int = Field(description="Уникальный идентификатор задачи")
    description: str = Field(description="Четкое и однозначное описание подзадачи")
    agent: str = Field(description="Имя агента-исполнителя (например, CodeGenerator)")
    dependencies: List[int] = Field(description="Список id задач, от которых зависит эта задача")


class Plan(BaseModel):
    title: Optional[str] = Field(
        default="Автоматический план",
        description="Краткое и емкое название проекта"
    )
    tasks: List[Task] = Field(description="Список всех подзадач для выполнения плана")


# 2. Создаем "умный" парсер на основе нашей схемы
parser = PydanticOutputParser(pydantic_object=Plan)


# 3. Создаем шаблон промпта, который включает инструкции по форматированию от парсера
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Ты — 'Jarvis Planner', элитный ИИ-агент по планированию. Твоя цель — разбивать сложные цели на последовательность четких, атомарных подзадач.

❗ Обязательно включи поле "title" — краткое название проекта.
❗ Обязательно включи поле "tasks" — список подзадач.
❗ Каждая подзадача должна иметь: id, description, agent, dependencies.
❗ Используй только этих агентов: `CodeGenerator`, `CodeReviewer`, `TestGenerator`, `CodeExecutor`, `ReportGenerator`.
❗ Всегда добавляй шаг `CodeReviewer` после `CodeGenerator`.
❗ Завершай план шагом `ReportGenerator`, если нужен отчёт.

{format_instructions}"""),
    ("human", "{goal}")
])


class TaskDecomposer:
   def __init__(self, planning_model_name: str):
       # Инициализируем модель и "цепь" (chain) с помощью LangChain Expression Language (LCEL)
       model = ChatOllama(model=planning_model_name, format="json")
       self.chain = prompt_template | model | parser


   async def decompose(self, goal: str) -> Dict[str, Any]:
       """
       Выполняет декомпозицию цели с помощью надежной цепи LangChain.
       Парсер автоматически обрабатывает ошибки формата и делает повторные запросы.
       """
       logger.info(f"Запуск декомпозиции цели с помощью LangChain: '{goal}'")
       try:
           # `ainvoke` - асинхронный вызов цепи
        plan_object: Plan = await self.chain.ainvoke({
            "goal": goal,
            "format_instructions": parser.get_format_instructions()
        })
        # Конвертируем Pydantic-объект обратно в словарь
        plan_dict = plan_object.dict()

        # Проверяем, что план содержит задачи
        if not plan_dict.get("tasks"):
            raise ValueError("Сгенерированный план не содержит задач!")

        return plan_dict

       except Exception as e:
           logger.error(f"Ошибка во время работы цепи декомпозиции: {e}")
           raise ValueError("Не удалось сгенерировать валидный план с помощью LangChain.")

import logging
from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatLiteLLM
from src.core.memory import MemoryManager
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

class MemorySearchInput(BaseModel):
    # ВАЖНО: Поле должно быть аннотировано как str с описанием
    query: str = Field(..., description="Ключевой запрос для поиска в долговременной памяти Jarvis.")

# === Инструмент поиска в памяти ===
class MemorySearchTool(BaseTool):
    name: str = "Search_Long_Term_Memory"
    description: str = "Используй этот инструмент для поиска релевантной информации в долговременной памяти Jarvis по ключевому запросу."
    args_schema: Type[BaseModel] = MemorySearchInput  # Указываем схему

    def __init__(self, search_function, **kwargs):
        super().__init__(**kwargs)
        # Явно сохраняем функцию поиска как атрибут объекта, а не Pydantic модели
        object.__setattr__(self, 'search_function', search_function)

    def _run(self, query: str) -> str:
        """Синхронный запуск инструмента"""
        try:
            if hasattr(self, 'search_function') and callable(self.search_function):
                result = self.search_function(query)
                return str(result) if result else "Информация не найдена в памяти."
            else:
                return "Инструмент поиска в памяти не настроен правильно."
        except Exception as e:
            logger.error(f"Ошибка при поиске в памяти: {e}")
            return f"Ошибка поиска: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Асинхронный запуск инструмента"""
        return self._run(query)

# === Основной класс ===
class PlanRefinementCrew:
    """
    Организует "мозговой штурм" команды из 4 ИИ-агентов для улучшения плана.
    """
    def __init__(self, model_name: str = "llama3"):
        self.model = ChatLiteLLM(model="ollama/llama3")
        self.memory = MemoryManager()

    def _create_agents(self):
        """Создает "Совет Четырех Мыслителей"."""
        memory_tool = MemorySearchTool(search_function=self.memory.search_memory)

        self.scientist = Agent(
            role='Ученый-исследователь',
            goal='Обеспечить, чтобы план был основан на проверенных данных и лучших практиках, а не на догадках.',
            backstory='Ты — ведущий научный сотрудник. Ты мыслишь фактами, исследованиями и объективной истиной. Ты всегда сначала ищешь информацию в долговременной памяти, прежде чем делать выводы.',
            llm=self.model,
            tools=[memory_tool],
            verbose=True
        )
        self.engineer = Agent(
            role='Инженер-прагматик',
            goal='Превратить любую идею в конкретный, работающий и эффективный пошаговый план.',
            backstory='Ты — системный архитектор с 20-летним опытом. Ты мыслишь структурами, логикой и системами. Твоя задача — обеспечить техническую осуществимость и надежность плана.',
            llm=self.model,
            verbose=True
        )
        self.mentor = Agent(
            role='Наставник-эмпат',
            goal='Убедиться, что решение будет полезным, понятным и этичным для конечного пользователя.',
            backstory='Ты — психолог и UX-эксперт. Ты мыслишь людьми, их эмоциями и мотивацией. Ты ставишь во главу угла человечность и удобство.',
            llm=self.model,
            verbose=True
        )
        self.artist = Agent(
            role='Художник-творец',
            goal='Найти инновационный, нестандартный подход к решению задачи, бросив вызов очевидным вариантам.',
            backstory='Ты — креативный директор и инноватор. Ты мыслишь "вне коробки", ищешь прорывные идеи и оригинальные решения. Твоя задача — сделать план не просто рабочим, а гениальным.',
            llm=self.model,
            verbose=True
        )

    def run(self, initial_plan: str, goal: str) -> str:
        """Запускает последовательное обсуждение плана командой."""
        self._create_agents()

        task_scientist = Task(
            description=f"Проанализируй этот первоначальный план для достижения цели '{goal}'. Твоя задача — проверить его на фактическую корректность и соответствие лучшим практикам. Используй инструмент 'Search Long-Term Memory' для поиска релевантной информации. Предложи улучшения, основанные на данных.\n\nПлан:\n{initial_plan}",
            expected_output="Текст с анализом и предложениями по улучшению плана с точки зрения фактов и данных.",
            agent=self.scientist
        )
        task_mentor = Task(
            description=f"Проанализируй план для цели '{goal}' с точки зрения пользователя и этики. Насколько он будет полезен и понятен? Есть ли потенциальные негативные последствия? Предложи улучшения, делающие план более человечным.",
            expected_output="Текст с анализом и предложениями по улучшению плана с точки зрения эмпатии и UX.",
            agent=self.mentor,
            context=[task_scientist]
        )
        task_artist = Task(
            description=f"Проанализируй план для цели '{goal}' на оригинальность. Можно ли решить эту задачу более креативным или инновационным способом? Предложи как минимум одну идею 'вне коробки'.",
            expected_output="Текст с анализом и предложениями по улучшению плана с точки зрения креативности.",
            agent=self.artist,
            context=[task_mentor]
        )
        task_engineer = Task(
            description="Ты — финальный интегратор. Собери первоначальный план и все предложения от Ученого, Наставника и Художника. Твоя задача — создать финальную, улучшенную версию плана в том же формате JSON, что и первоначальный. Устрани конфликты и выбери лучшие идеи.",
            expected_output="Финальный, улучшенный план в формате JSON.",
            agent=self.engineer,
            context=[task_artist]
        )

        crew = Crew(
            agents=[self.scientist, self.mentor, self.artist, self.engineer],
            tasks=[task_scientist, task_mentor, task_artist, task_engineer],
            process=Process.sequential,
            verbose=True
        )
      
        logger.info("Запуск 'Совета Мыслителей' для улучшения плана...")
        final_plan = crew.kickoff()
        logger.info("'Совет Мыслителей' завершил работу.")
        return final_plan
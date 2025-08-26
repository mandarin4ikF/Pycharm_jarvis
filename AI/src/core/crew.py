# ==============================================================================
# Файл: src/core/crew.py
# Назначение: Реализация CrewAI для улучшения плана ("Совет Мыслителей")
# ==============================================================================

import logging
import json
from typing import Type

# === Импорты из CrewAI ===
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

# === Импорты из Pydantic ===
from pydantic import BaseModel, Field

# === Импорты из LangChain ===
# Используем устаревший, но пока рабочий ChatLiteLLM
# TODO: В будущем заменить на langchain_litellm.ChatLiteLLM
from langchain_community.chat_models import ChatLiteLLM

# === Локальные импорты ===
from src.core.memory import MemoryManager

# ==============================================================================
# Настройка логирования
# ==============================================================================
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. Определение схемы аргументов для инструмента поиска в памяти
# ==============================================================================
class MemorySearchInput(BaseModel):
    """
    Схема аргументов для инструмента поиска в долговременной памяти.
    """
    # КРИТИЧНО: Поле должно быть аннотировано как str с описанием
    query: str = Field(
        ..., 
        description="Ключевой запрос для поиска в долговременной памяти Jarvis."
    )

# ==============================================================================
# 2. Реализация инструмента поиска в памяти
# ==============================================================================
class MemorySearchTool(BaseTool):
    """
    Инструмент для поиска информации в долговременной памяти Jarvis.
    """
    # --- Метаданные инструмента ---
    name: str = "Search_Long_Term_Memory"
    description: str = (
        "Используй этот инструмент для поиска релевантной информации "
        "в долговременной памяти Jarvis по ключевому запросу."
    )
    # --- Схема аргументов ---
    args_schema: Type[BaseModel] = MemorySearchInput

    def __init__(self, search_function, **kwargs):
        """
        Инициализирует инструмент поиска.
        
        Args:
            search_function: Функция, которая будет вызываться для поиска.
                             Должна принимать строку и возвращать результат.
        """
        super().__init__(**kwargs)
        # Явно и безопасно сохраняем функцию поиска как атрибут экземпляра
        # Используем object.__setattr__ чтобы избежать проблем с Pydantic
        object.__setattr__(self, 'search_function', search_function)
        logger.debug(f"[MemorySearchTool] Initialized with search_function: {search_function}")

    def _run(self, query: str) -> str:
        """
        Синхронный запуск инструмента.
        
        Args:
            query: Строка запроса для поиска.
            
        Returns:
            Строка с результатом поиска или сообщением об ошибке.
        """
        logger.debug(f"[MemorySearchTool._run] Called with query: '{query}' (type: {type(query)})")
        
        # --- Валидация входных данных ---
        if not isinstance(query, str):
            error_msg = (
                f"Инструмент '{self.name}' ожидает строку для 'query', "
                f"но получил {type(query).__name__}: {query}"
            )
            logger.error(f"[MemorySearchTool._run] {error_msg}")
            return error_msg

        # --- Проверка наличия функции поиска ---
        if not hasattr(self, 'search_function') or not callable(self.search_function):
            error_msg = f"Функция поиска не настроена для инструмента '{self.name}'."
            logger.error(f"[MemorySearchTool._run] {error_msg}")
            return error_msg

        # --- Выполнение поиска ---
        try:
            logger.info(f"[MemorySearchTool._run] Выполняется поиск по запросу: '{query}'")
            result = self.search_function(query)
            
            if result:
                logger.debug(f"[MemorySearchTool._run] Найден результат для '{query}': {type(result)}")
                return str(result)
            else:
                logger.info(f"[MemorySearchTool._run] По запросу '{query}' ничего не найдено.")
                return "Информация не найдена в памяти."
                
        except Exception as e:
            logger.error(
                f"[MemorySearchTool._run] Ошибка при поиске по запросу '{query}': {e}", 
                exc_info=True
            )
            return f"Ошибка поиска: {str(e)}"

    async def _arun(self, query: str) -> str:
        """
        Асинхронный запуск инструмента.
        Делегирует выполнение синхронному методу.
        """
        logger.debug(f"[MemorySearchTool._arun] Called, delegating to _run.")
        return self._run(query)

# ==============================================================================
# 3. Основной класс для улучшения плана
# ==============================================================================
class PlanRefinementCrew:
    """
    Организует "мозговой штурм" команды из 4 ИИ-агентов для улучшения плана.
    """

    def __init__(self, model_name: str = "ollama/llama3"):
        """
        Инициализирует CrewAI для улучшения плана.
        
        Args:
            model_name: Название модели для использования в агентах.
                        По умолчанию "ollama/llama3".
        """
        # TODO: Заменить на langchain_litellm.ChatLiteLLM
        self.model = ChatLiteLLM(model=model_name)
        self.memory = MemoryManager()
        logger.info(f"[PlanRefinementCrew] Initialized with model: {model_name}")

    def _create_agents(self):
        """
        Создает "Совет Четырех Мыслителей" - агентов с разными ролями.
        """
        logger.debug("[PlanRefinementCrew._create_agents] Создание агентов...")
        
        # --- Создание инструмента поиска в памяти ---
        # Передаем метод поиска из MemoryManager
        memory_tool = MemorySearchTool(search_function=self.memory.search_memory)
        logger.debug(f"[PlanRefinementCrew._create_agents] Создан инструмент: {memory_tool}")
        logger.debug(f"[PlanRefinementCrew._create_agents] Схема аргументов: {memory_tool.args_schema}")

        # --- Создание агентов ---
        self.scientist = Agent(
            role='Ученый-исследователь',
            goal=(
                'Обеспечить, чтобы план был основан на проверенных данных '
                'и лучших практиках, а не на догадках.'
            ),
            backstory=(
                'Ты — ведущий научный сотрудник. Ты мыслишь фактами, исследованиями '
                'и объективной истиной. Ты всегда сначала ищешь информацию '
                'в долговременной памяти, прежде чем делать выводы.'
            ),
            llm=self.model,
            tools=[memory_tool], # Только у Ученого есть доступ к памяти
            verbose=True,
            allow_delegation=False # Отключаем делегирование внутри Crew
        )
        logger.debug("[PlanRefinementCrew._create_agents] Создан агент: Ученый-исследователь")

        self.mentor = Agent(
            role='Наставник-эмпат',
            goal=(
                'Убедиться, что решение будет полезным, понятным '
                'и этичным для конечного пользователя.'
            ),
            backstory=(
                'Ты — психолог и UX-эксперт. Ты мыслишь людьми, их эмоциями '
                'и мотивацией. Ты ставишь во главу угла человечность и удобство.'
            ),
            llm=self.model,
            verbose=True,
            allow_delegation=False
        )
        logger.debug("[PlanRefinementCrew._create_agents] Создан агент: Наставник-эмпат")

        self.artist = Agent(
            role='Художник-творец',
            goal=(
                'Найти инновационный, нестандартный подход к решению задачи, '
                'бросив вызов очевидным вариантам.'
            ),
            backstory=(
                'Ты — креативный директор и инноватор. Ты мыслишь "вне коробки", '
                'ищешь прорывные идеи и оригинальные решения. Твоя задача — '
                'сделать план не просто рабочим, а гениальным.'
            ),
            llm=self.model,
            verbose=True,
            allow_delegation=False
        )
        logger.debug("[PlanRefinementCrew._create_agents] Создан агент: Художник-творец")

        self.engineer = Agent(
            role='Инженер-прагматик',
            goal=(
                'Превратить любую идею в конкретный, работающий '
                'и эффективный пошаговый план.'
            ),
            backstory=(
                'Ты — системный архитектор с 20-летним опытом. Ты мыслишь структурами, '
                'логикой и системами. Твоя задача — обеспечить техническую '
                'осуществимость и надежность плана.'
            ),
            llm=self.model,
            verbose=True,
            allow_delegation=False
        )
        logger.debug("[PlanRefinementCrew._create_agents] Создан агент: Инженер-прагматик")
        logger.info("[PlanRefinementCrew._create_agents] Все агенты успешно созданы.")

    def run(self, initial_plan: str, goal: str) -> str:
        """
        Запускает последовательное обсуждение плана командой агентов.
        
        Args:
            initial_plan: Первоначальный план в формате JSON-строки.
            goal: Основная цель, для которой создавался план.
            
        Returns:
            Улучшенный план в формате JSON-строки.
        """
        logger.info("[PlanRefinementCrew.run] Начало улучшения плана...")
        
        # --- Создание агентов ---
        self._create_agents()

        # --- Создание задач для агентов ---
        logger.debug("[PlanRefinementCrew.run] Создание задач...")
        
        task_scientist = Task(
            description=(
                f"Проанализируй этот первоначальный план для достижения цели '{goal}'.\n"
                f"Твоя задача — проверить его на фактическую корректность и соответствие "
                f"лучшим практикам. Используй инструмент 'Search Long-Term Memory' для "
                f"поиска релевантной информации. Для поиска задавай конкретные вопросы, "
                f"например: 'лучшие практики для систем предсказания цен' или "
                f"'модели машинного обучения для анализа криптовалют'.\n\n"
                f"План:\n{initial_plan}"
            ),
            expected_output=(
                "Текст с анализом и предложениями по улучшению плана "
                "с точки зрения фактов и данных."
            ),
            agent=self.scientist
        )
        logger.debug("[PlanRefinementCrew.run] Создана задача для Ученого")

        task_mentor = Task(
            description=(
                f"Проанализируй план для цели '{goal}' с точки зрения пользователя и этики.\n"
                f"Насколько он будет полезен и понятен? Есть ли потенциальные "
                f"негативные последствия? Предложи улучшения, делающие план более человечным."
            ),
            expected_output=(
                "Текст с анализом и предложениями по улучшению плана "
                "с точки зрения эмпатии и UX."
            ),
            agent=self.mentor,
            context=[task_scientist] # Зависит от результата Ученого
        )
        logger.debug("[PlanRefinementCrew.run] Создана задача для Наставника")

        task_artist = Task(
            description=(
                f"Проанализируй план для цели '{goal}' на оригинальность.\n"
                f"Можно ли решить эту задачу более креативным или инновационным способом? "
                f"Предложи как минимум одну идею 'вне коробки'."
            ),
            expected_output=(
                "Текст с анализом и предложениями по улучшению плана "
                "с точки зрения креативности."
            ),
            agent=self.artist,
            context=[task_mentor] # Зависит от результата Наставника
        )
        logger.debug("[PlanRefinementCrew.run] Создана задача для Художника")

        task_engineer = Task(
            description=(
                "Ты — финальный интегратор. Собери первоначальный план и все "
                "предложения от Ученого, Наставника и Художника. Твоя задача — "
                "создать финальную, улучшенную версию плана в том же формате JSON, "
                "что и первоначальный. Устрани конфликты и выбери лучшие идеи.\n"
                "ВАЖНО: Ответ должен быть валидным JSON-объектом, начинающимся с '{' "
                "и заканчивающимся '}'. Не используй markdown или другие форматы."
            ),
            expected_output="Финальный, улучшенный план в формате JSON.",
            agent=self.engineer,
            context=[task_artist] # Зависит от результата Художника
        )
        logger.debug("[PlanRefinementCrew.run] Создана задача для Инженера")

        # --- Создание и запуск команды ---
        logger.info("[PlanRefinementCrew.run] Создание и запуск CrewAI...")
        crew = Crew(
            agents=[self.scientist, self.mentor, self.artist, self.engineer],
            tasks=[task_scientist, task_mentor, task_artist, task_engineer],
            process=Process.sequential, # Выполняем задачи по порядку
            verbose=True # Включаем подробный вывод
        )

        # --- Запуск команды ---
        logger.info("🚀 Запуск 'Совета Мыслителей' для улучшения плана...")
        crew_output = crew.kickoff() # Запуск и получение результата
        logger.info("✅ 'Совет Мыслителей' завершил работу.")

        # --- Обработка результата ---
        logger.debug(f"[PlanRefinementCrew.run] Тип результата: {type(crew_output)}")
        
        # Проверяем, является ли результат строкой JSON
        if isinstance(crew_output, str):
            result_str = crew_output.strip()
            # Если похоже на JSON-объект или массив
            if (result_str.startswith(('{', '[')) and 
                result_str.endswith(('}', ']'))):
                try:
                    # Пробуем распарсить для проверки валидности
                    json.loads(result_str)
                    logger.debug("[PlanRefinementCrew.run] Результат уже является валидным JSON")
                    return result_str
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"[PlanRefinementCrew.run] Результат похож на JSON, но не прошел парсинг: {e}"
                    )
                    # Возвращаем как есть
                    return result_str
            else:
                # Просто строка, не похожая на JSON
                logger.debug("[PlanRefinementCrew.run] Результат - обычная строка")
                return result_str
        
        # Если это объект CrewOutput (новые версии CrewAI)
        elif hasattr(crew_output, 'raw') and isinstance(crew_output.raw, str):
            logger.debug("[PlanRefinementCrew.run] Используется crew_output.raw")
            raw_str = crew_output.raw.strip()
            if (raw_str.startswith(('{', '[')) and 
                raw_str.endswith(('}', ']'))):
                try:
                    json.loads(raw_str)
                    logger.debug("[PlanRefinementCrew.run] crew_output.raw - валидный JSON")
                    return raw_str
                except json.JSONDecodeError:
                    logger.warning("[PlanRefinementCrew.run] crew_output.raw не является валидным JSON")
                    return raw_str
            else:
                return raw_str
                
        elif hasattr(crew_output, 'json_dict') and isinstance(crew_output.json_dict, dict):
            logger.debug("[PlanRefinementCrew.run] Используется crew_output.json_dict")
            return json.dumps(crew_output.json_dict, ensure_ascii=False, indent=2)

        elif hasattr(crew_output, 'pydantic') and crew_output.pydantic is not None:
            logger.debug("[PlanRefinementCrew.run] Используется crew_output.pydantic")
            return json.dumps(crew_output.pydantic.dict(), ensure_ascii=False, indent=2)

        else:
            # Последний рубеж: преобразуем в строку
            logger.debug("[PlanRefinementCrew.run] Преобразование результата в строку")
            result_str = str(crew_output)
            return result_str

# ==============================================================================
# Конец файла
# ==============================================================================

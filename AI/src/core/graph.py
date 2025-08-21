import logging
import asyncio
import json
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from src.core.agents import AGENT_MAPPING
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """Определяет состояние графа, которое передается между узлами."""
    plan: Dict[str, Any]
    completed_tasks: Annotated[List[int], lambda x, y: x + y]
    results: Annotated[Dict[int, str], lambda x, y: {**x, **y}]
    next_tasks: List[Dict[str, Any]]


class GraphExecutor:
    """Определяет и выполняет граф задач с помощью LangGraph."""
    def __init__(self):
        self.workflow = StateGraph(GraphState)
        self._define_graph()
        self.app = self.workflow.compile()

    def _define_graph(self):
        """Определяет структуру графа: узлы и ребра."""
        self.workflow.add_node("planner", self.planner_node)
        self.workflow.add_node("executor", self.executor_node)
        self.workflow.set_entry_point("planner")
        self.workflow.add_conditional_edges(
            "executor",
            self.router_node,
            {"continue": "planner", "end": END}
        )
        self.workflow.add_edge("planner", "executor")

    def planner_node(self, state: GraphState) -> Dict[str, Any]:
        """Узел-планировщик: определяет, какие задачи можно выполнить на следующем шаге."""
        completed = set(state.get("completed_tasks", []))
        all_tasks = state["plan"]["tasks"]
        ready_tasks = []
        for task in all_tasks:
            task_id = task["id"]
            if task_id not in completed:
                dependencies = set(task.get("dependencies", []))
                if dependencies.issubset(completed):
                    ready_tasks.append(task)
        logger.info(f"[Graph Planner] Найдены готовые к выполнению задачи: {[t['id'] for t in ready_tasks]}")
        return {"next_tasks": ready_tasks}

    async def executor_node(self, state: GraphState) -> Dict[str, Any]:
        """Узел-исполнитель: параллельно запускает все готовые задачи."""
        tasks_to_run = state.get("next_tasks", [])
        coroutines = []
        for task in tasks_to_run:
            agent_name = task.get("agent", "CodeGenerator")
            agent_func = AGENT_MAPPING.get(agent_name)
            if agent_func:
                coroutines.append(self._safe_execute_agent(agent_func, state, task))
        
        # Обрабатываем исключения в gather
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        completed_ids = []
        new_results = {}
        
        for i, result in enumerate(results):
            task_id = tasks_to_run[i]["id"]
            if isinstance(result, Exception):
                logger.error(f"Ошибка выполнения задачи {task_id}: {result}")
                new_results[task_id] = f"Ошибка: {str(result)}"
            else:
                completed_ids.append(result["task_id"])
                new_results[result["task_id"]] = result["result"]
        
        return {"completed_tasks": completed_ids, "results": new_results}

    async def _safe_execute_agent(self, agent_func, state, task):
        """Безопасное выполнение агента с обработкой исключений."""
        try:
            return await agent_func(state, task)
        except Exception as e:
            logger.error(f"Ошибка в агенте {task.get('agent')} для задачи {task['id']}: {e}")
            raise e

    def router_node(self, state: GraphState) -> str:
        """Узел-маршрутизатор: решает, продолжать выполнение или закончить."""
        completed_count = len(state.get("completed_tasks", []))
        total_count = len(state["plan"]["tasks"])
        if completed_count >= total_count:
            logger.info("[Graph Router] ✅ Все задачи выполнены. Завершение.")
            return "end"
        else:
            logger.info("[Graph Router] ➡️ Есть незавершенные задачи. Продолжаем.")
            return "continue"

    async def run(self, plan: Dict[str, Any]):
        """Запускает выполнение плана в графе."""
        initial_state = {
            "plan": plan,
            "completed_tasks": [],
            "results": {},
            "next_tasks": []
        }
        final_state = None
        async for s in self.app.astream(initial_state):
            final_state = s
        
        print("\n--- Финальный результат выполнения графа ---")
        
        # Безопасная сериализация результатов
        try:
            serializable_results = {}
            for task_id, result in final_state.get("results", {}).items():
                # Преобразуем в строку, если результат не сериализуем
                try:
                    json.dumps(result)
                    serializable_results[task_id] = result
                except (TypeError, ValueError):
                    serializable_results[task_id] = str(result)
            
            print(json.dumps(serializable_results, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Ошибка при выводе результатов: {e}")
            print("Результаты:", final_state.get("results", {}))
        
        print("------------------------------------------")
        return final_state
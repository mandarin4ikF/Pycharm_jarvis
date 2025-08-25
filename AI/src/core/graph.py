import logging
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from src.core.agents import AGENT_MAPPING
from src.core.memory import WorkingMemory # <-- Новый импорт
import asyncio
import json

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
   """
   Определяет состояние графа. Теперь включает рабочую память.
   """
   plan: Dict[str, Any]
   working_memory: WorkingMemory # <-- НОВОЕ ПОЛЕ
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
       self.workflow.add_node("planner", self.planner_node)
       self.workflow.add_node("executor", self.executor_node)
       self.workflow.set_entry_point("planner")
       self.workflow.add_conditional_edges("executor", self.router_node, {"continue": "planner", "end": END})
       self.workflow.add_edge("planner", "executor")


   def planner_node(self, state: GraphState) -> Dict[str, Any]:
       completed = set(state.get("completed_tasks", []))
       ready_tasks = [t for t in state["plan"]["tasks"] if t["id"] not in completed and set(t.get("dependencies", [])).issubset(completed)]
       return {"next_tasks": ready_tasks}


   async def executor_node(self, state: GraphState) -> Dict[str, Any]:
       tasks_to_run = state.get("next_tasks", [])
       # Теперь каждый агент будет иметь доступ к состоянию, включая рабочую память
       coroutines = [AGENT_MAPPING[t.get("agent")](state, t) for t in tasks_to_run if AGENT_MAPPING.get(t.get("agent"))]
       results = await asyncio.gather(*coroutines)
      
       # Обновляем рабочую память результатами
       working_memory = state["working_memory"]
       for res in results:
           task_id = res["task_id"]
           agent_name = state["plan"]["tasks"][task_id-1]["agent"]
           working_memory.add_entry(source=agent_name, content=json.dumps(res["result"], ensure_ascii=False, indent=2), data_type="result")


       return {
           "completed_tasks": [r["task_id"] for r in results],
           "results": {r["task_id"]: r["result"] for r in results},
           "working_memory": working_memory
       }


   def router_node(self, state: GraphState) -> str:
       return "end" if len(state.get("completed_tasks", [])) >= len(state["plan"]["tasks"]) else "continue"


   async def run(self, plan: Dict[str, Any], working_memory: WorkingMemory):
       """Запускает выполнение плана, принимая инициализированную рабочую память."""
       initial_state = {
           "plan": plan,
           "working_memory": working_memory,
           "completed_tasks": [],
           "results": {},
           "next_tasks": []
       }
       final_state = None
       async for s in self.app.astream(initial_state):
           final_state = s
      
       print("\n--- Финальный результат выполнения графа ---")
       print(json.dumps(final_state.get("results"), indent=2, ensure_ascii=False))
       print("\n--- Содержимое рабочей памяти в конце ---")
       print(final_state["working_memory"].get_full_context())

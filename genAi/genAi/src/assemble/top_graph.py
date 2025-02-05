from utilities.helper_methods_agent import create_team_supervisor
import json, operator

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph, START
from typing_extensions import TypedDict
from typing import Annotated, List, Union, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from top_state.top_state import TopState
from langgraph.checkpoint.memory import MemorySaver
from common.llm import get_llm,get_bigger_llm
from design_graph.graph_workflow import infer_schema_chain
from rewoo_graph.rewoo_graph_workflow import structuring_chain
import ast,os

#llm = get_bigger_llm()  #--modified
llm=get_llm()
supervisor_node = create_team_supervisor(
    llm,
    "You are a supervisor tasked with managing a conversation between the"
    " following teams: {team_members}. Given the following user request,"
    " respond with the worker to act next. Each worker will perform a"
    " task and respond with their results and status. When finished,"
    " respond with FINISH.",
    ["Infer_Schema_Team", "Structuring_Team"],
)

def run_supervisor(state: TopState):
    # For LLAMA
    agent_outcome = supervisor_node.invoke({"messages":state["messages"]})
    #agent_outcome = supervisor_node.invoke(state)
    agent_outcome = json.loads(agent_outcome.content)
    return {
        "input": state["messages"][0].content,
        "next": agent_outcome["next"],
        "messages": [
            SystemMessage(
                content=f"{agent_outcome['next']} agent execution has been initiated."
            )
        ]
    }

def preprocess_schema_top_state(state: TopState) -> dict:
    # # Create the final string with the desired format

    #data_dict = json.loads(state["schema_info"])
    schema_list=ast.literal_eval(state["schema_info"])
    print(schema_list)
    modified_schema_list=[]
    for i,schema in enumerate(schema_list):
        if isinstance(schema, str):
            schema_for_del = ast.literal_eval(schema)
        else:
            schema_for_del = schema

        del schema_for_del['Dividers']

        string_formatted = f"""
        Schema: {schema_for_del}
        """
        string_formatted = string_formatted.replace("{","{{").replace("}","}}")

        formatted_string = f"""
        {{{{
        {string_formatted},
        Dataframe path: {'{df_path}'}
        }}}}
        """
        df_path = ast.literal_eval(state["file_path"][0]["file_list"])[i]["file_path"]
        sheet_name = ast.literal_eval(state["file_path"][0]["file_list"])[i]["sheet_name"]

        schema = formatted_string.format(df_path= df_path + "$" + sheet_name + "%")
        modified_schema_list.append(schema)

        #new_state={}
    state["input"] = repr(modified_schema_list)
    return state


def infer_schema_join_graph(response: dict):
    return {
        "messages": [response["messages"][-1]],
        "schema_info": response["schema_info"],
        "file_path": response["file_path"]
    }
    #return {"messages": [response["messages"][-1]]}

def structuring_join_graph(response:dict):
    print(response["structured_file_paths"])
    return {
        "messages": [response["messages"][-1]],
        "structured_file_paths": response["structured_file_paths"]
    }

# Define the graph.
super_graph = StateGraph(TopState)
# First add the nodes, which will do the work
super_graph.add_node("Infer_Schema_Team",  infer_schema_chain | infer_schema_join_graph)

super_graph.add_node("Structuring_Team", preprocess_schema_top_state | structuring_chain | structuring_join_graph)


super_graph.add_node("supervisor", run_supervisor)

# Define the graph connections, which controls how the logic
# propagates through the program
super_graph.add_edge("Infer_Schema_Team", "supervisor")
super_graph.add_edge("Structuring_Team", "supervisor")

super_graph.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "Infer_Schema_Team": "Infer_Schema_Team",
        "Structuring_Team": "Structuring_Team",
        "FINISH": END,
    },
)
super_graph.add_edge(START, "supervisor")
memory = MemorySaver()

super_graph = super_graph.compile(checkpointer=memory, interrupt_after = ["Infer_Schema_Team","Structuring_Team"])
current_dir = os.path.dirname(__file__)
graph_path = os.path.join(current_dir, 'graph.png')
super_graph.get_graph().draw_mermaid_png(output_file_path=graph_path)
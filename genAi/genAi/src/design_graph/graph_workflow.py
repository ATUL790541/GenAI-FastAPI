from dotenv import load_dotenv
from langchain_core.agents import AgentFinish
from langgraph.graph import END, StateGraph
from agents.agent_tracker import (
    run_supervisor_agent,
    execute_infer_schema_tools,
    run_infer_schema_engine,

)
from common.state import AgentState
from agents.agent_initializer import members
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, AIMessage,BaseMessage

load_dotenv()

SUPERVISOR = "supervisor"
SCHEMA_NODE = "infer_schema"
SCHEMA_ACT = "update_intermediate_steps_for_infer_schema"
HUMAN_FEEDBACK = "human_feedback"
SET_SCHEMA = "set_schema"

def human_feedback(state):
    print("---human_feedback---")
    pass

def set_schema(state):

    return {"schema_info":state["intermediate_steps"][0][1]}

def should_continue_for_infer_schema_agent(state: AgentState) -> str:
    if isinstance(state["agent_outcome"], AgentFinish):
        return HUMAN_FEEDBACK
    else:
        if state["intermediate_steps"] == []:
            return SCHEMA_ACT
        print("Hallucinations resolved")
        state["schema_info"] = state["intermediate_steps"][0][1]
        return SET_SCHEMA
        # return HUMAN_FEEDBACK


flow = StateGraph(AgentState)

flow.add_node(SUPERVISOR, run_supervisor_agent)
flow.add_node(SCHEMA_NODE, run_infer_schema_engine)
flow.add_node(SCHEMA_ACT, execute_infer_schema_tools)
flow.add_node(HUMAN_FEEDBACK, human_feedback)
flow.add_node(SET_SCHEMA, set_schema)


conditional_map = {k: k for k in members}
conditional_map["FINISH"] = END
flow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)


flow.set_entry_point(SUPERVISOR)
flow.add_conditional_edges(
    SCHEMA_NODE,
    should_continue_for_infer_schema_agent,
)


flow.add_edge(SCHEMA_ACT, SCHEMA_NODE)
flow.add_edge(SET_SCHEMA, HUMAN_FEEDBACK)

flow.add_edge(HUMAN_FEEDBACK, SUPERVISOR)

# Set up memory
memory = MemorySaver()

# Add
graph = flow.compile(checkpointer=memory, interrupt_before=["human_feedback"])

def enter_chain(output: dict):
    print(output)
    #print(message)
    if "schema_info" not in output.keys():
        output["schema_info"] = ""

    results = {
        "messages": output['messages'],
        "schema_info": output["schema_info"],
        "file_path": output["file_path"]
    }
    return results

infer_schema_chain = (
    graph | enter_chain
)



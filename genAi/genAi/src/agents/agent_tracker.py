from dotenv import load_dotenv
from langgraph.prebuilt.tool_executor import ToolExecutor
from langchain_core.messages import SystemMessage, BaseMessage
from agents.agent_initializer import (
    supervisor_chain,
    infer_schema_tool_list,
    infer_schema_agent

)
from common.state import AgentState
from langchain_core.agents import AgentFinish
import json
import asyncio

from langchain_core.exceptions import OutputParserException
load_dotenv()

infer_schema_tool_executor = ToolExecutor(infer_schema_tool_list)

def run_supervisor_agent(state: AgentState):

    agent_outcome = supervisor_chain.invoke({"messages":state["messages"]})
    #agent_outcome = supervisor_node.invoke(state)
    agent_outcome = json.loads(agent_outcome.content)

    return {
        "input": state["messages"][0].content,
        "next": agent_outcome["next"],
        "messages": [
            SystemMessage(
                content=f"{agent_outcome['next']} agent execution has been initiated."
            )
        ],
    }


def run_infer_schema_engine(state: AgentState):

    try:
        agent_outcome = infer_schema_agent.invoke(state)
    except OutputParserException as e:
        try:
            schema_info = infer_schema_agent.invoke(state)
        except:
            schema_info = infer_schema_agent.invoke(state)


    # print(state)
    schema_info=""
    if isinstance(agent_outcome, AgentFinish):
        msg = SystemMessage(
            content=f"{state['next']} agent execution has been completed."
        )
        schema_info = agent_outcome.return_values["output"]
        # schema_info = json.dumps(schema_info.dict())
    else:
        if state["intermediate_steps"] == []:
            msg = SystemMessage(
                content=f"{state['next']} : {agent_outcome.tool} tool execution has been initiated."
            )

        else:
            msg = SystemMessage(
            content=f"{state['next']} agent execution has been completed."
            )
    return {
        "agent_outcome": agent_outcome,
        "messages": [msg],
        "schema_info": schema_info,
    }

def execute_infer_schema_tools(state: AgentState):
    agent_action = state["agent_outcome"]
    print(state)
    output = asyncio.run(infer_schema_tool_executor.ainvoke(agent_action))
    return {
        "intermediate_steps": [(agent_action, str(output))],
        "messages": [
            SystemMessage(
                content=f"{state['next']} : {agent_action.tool} tool execution has been completed."
            )
        ],
    }


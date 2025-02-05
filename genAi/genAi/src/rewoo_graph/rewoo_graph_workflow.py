from dotenv import load_dotenv
from langchain_core.agents import AgentFinish
from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, AIMessage,BaseMessage
from common.llm import get_llm
from rewoo_graph.runnables import *
from rewoo_graph.rewoo_state import ReWOO
from rewoo_graph.rewoo_tool import header_identification_tool,multi_table_handling_tool,anchors_handling_tool,multi_indices_handling
from rewoo_graph.prompt import solve_prompt, planner_prompt
import ast,time
load_dotenv()

def _get_current_schema(state:ReWOO):
    input_schema_list = ast.literal_eval(state["input"])
    if state["results"] is None:
        return 1
    if len(input_schema_list) == state["count"]:
        return None
    else:
        return state["count"] + 1

def get_plan(state: ReWOO):

    input_schema_list = ast.literal_eval(state["input"])
    _schema_number = _get_current_schema(state)
    input=input_schema_list[_schema_number-1]

    #result = planner.invoke({"input": input})
    result = get_llm().invoke(planner_prompt.format(input=input))
    # Find all matches in the sample text
    final_plan = get_llm().invoke(f"""
    <|begin_of_text|><|start_header_id|>user<|end_header_id|>

    You are an expert in correcting a plan based on **Consolidated Explanation** provided. For example it may contain whether a particular tool needs to be included or excluded. **Remove** the tool from the plan if it has to be excluded. Modify the plan based on the **Consolidated Explanation** provided in this output:-
    {result.content}. Note: Remove any explantions and Plan number present following the word `Plan` but preserve the format in the final output. for example change `Plan 1` to `Plan`.
    Output Plan Format to be followed if Tool Name-1 and Tool Name-2 are the tools which needs to be included:

    Plan: "details related to Tool Name-1"
    #E(number) = <Tool Name-1>[inputs]
    Plan: "details related to Tool Name-2"
    #E(number) = <Tool Name-2>[inputs]

    Critical Note: Do not provide any extra information.Just follow the given Output Plan Format.
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>

    """).content
    print(final_plan)
    matches = re.findall(regex_pattern, final_plan)
    if len(matches) == 0:
        final_plan = get_llm().invoke(f"Given {result.content}. Plan number present following the word `Plan` should be removed for example change `Plan 1` to `Plan`. DO NOT change anything else and preserve the format in the final output.").content
    print(final_plan)
    matches = re.findall(regex_pattern, final_plan)
    print(f"steps: {matches}")
    print(f"plan_string: {result.content}")

    if state["count"] is None:
        count = 1
    else:
        count = state["count"] + 1

    return {"steps": matches, "plan_string": result.content, "count":count}
def _get_current_task(state: ReWOO):

    inputs = ast.literal_eval(state["input"])[state["count"]-1]
    #input_list = inputs.rsplit(",",1)
    #print(inputs)
    pattern = r"Dataframe path:\s*(.+)"

    # Search for the pattern in the string
    match = re.search(pattern, inputs)
    if match:
        dataframe_path = match.group(1).strip()
    #input_list = inputs.rsplit(",",1)
    #print(f"dataframe_path: {dataframe_path}")
    dataframe_path = dataframe_path.rsplit("%",1)[0]
    df_info_list = dataframe_path.split("$")
    #print(f"df_info_list: {df_info_list}")

    path= df_info_list[0]
    sheet_name= df_info_list[1]

    if state["results"] is not None:
        not_found = not any(sheet_name in item for item in state["results"].keys())
        count=0
        for item in state["results"].keys():

            if sheet_name in item:
                count+=1

    if state["results"] is None or not_found:
        return 1
    if count == len(state["steps"]):
        return None
    else:
        return count+1

def run_with_retry(tool, *args, max_retries=3, **kwargs):
    """Attempts to run a tool until it succeeds or until max_retries is reached."""
    retries = 0
    while retries < max_retries:
        try:
            return tool.invoke(*args, **kwargs)
        except Exception as e:
            retries += 1
            print("Error: {str{e})} - Retrying ({retries}/{max_retries})...")
            #st.warning(f"Error: {str(e)} - Retrying ({retries}/{max_retries})...")
    #st.error("Max retries reached. Please check the function or input data.")
    return None  # Return None if all retries failed

def tool_execution(state: ReWOO):
    """Worker node that executes the tools of a given plan."""

    inputs = ast.literal_eval(state["input"])[state["count"]-1]
    #input_list = inputs.rsplit(",",1)
    print(inputs)
    pattern = r"Dataframe path:\s*(.+)"

    # Search for the pattern in the string
    match = re.search(pattern, inputs)
    if match:
        dataframe_path = match.group(1).strip()
    #input_list = inputs.rsplit(",",1)
    print(f"dataframe_path: {dataframe_path}")
    dataframe_path = dataframe_path.rsplit("%",1)[0]
    df_info_list = dataframe_path.split("$")
    print(f"df_info_list: {df_info_list}")

    path= df_info_list[0]
    sheet_name= df_info_list[1]

    for i in range(len(state["steps"])):
        if "Multi_Table_Handling" in state["steps"][i]:

            # state["steps"][0][0] = state["steps"][i][0] # Tool definition

            step_as_list = list(state["steps"][0])

            step_as_list[0] = state["steps"][i][0]

            step_as_list[2] = state["steps"][i][2] # Tool Name

            state["steps"][0] = tuple(step_as_list)

            del state["steps"][i]
            # state["steps"][0][1] = state["steps"][i][1]
            # state["steps"][0][3] = state["steps"][i][3]


    _step = _get_current_task(state)
    print(f"current task: {_step}")
    _, step_name, tool, tool_input = state["steps"][_step - 1]
    #_results = state["results"] or {}
    try:
        _results = {k: v for k, v in state["results"].items() if sheet_name in k}
    except:
        _results = {}
    try:
        _historical_results = {k: v for k, v in state["results"].items() if sheet_name not in k}
    except:
        _historical_results = {}
    for k, v in _results.items():
        tool_input_with_sheet = tool_input + f"_{sheet_name}"
        tool_input = tool_input_with_sheet.replace(k, v)
    if tool == "Header_Handling":
        print(tool_input)
        result = run_with_retry(header_identification_tool, tool_input)

    elif tool == "Anchor_Handling":
        # result = anchors_handling_tool.invoke(tool_input)
        result = run_with_retry(anchors_handling_tool, tool_input)
    elif tool == "Multi_Table_Handling":
        print(tool_input)
        # result = multi_table_handling_tool.invoke(tool_input)
        result = run_with_retry(multi_table_handling_tool, tool_input)

    elif tool == "Multi_Indices_Handling":
        # result = multi_indices_handling.invoke(tool_input)
        result = run_with_retry(multi_indices_handling, tool_input)

    else:
        raise ValueError

    _results[f"{step_name}_{sheet_name}"] = str(result)

    # Combining historical and latest results (to avoid overwriting of outputs of previous sheets)
    _final_results = _results | _historical_results
    return {"results": _final_results}

def solve(state: ReWOO):
    plan = ""
    for _plan, step_name, tool, tool_input in state["steps"]:
        _results = state["results"] or {}
        for k, v in _results.items():
            tool_input = tool_input.replace(k, v)
            step_name = step_name.replace(k, v)
        plan += f"Plan: {_plan}\n{step_name} = {tool}[{tool_input}]"
    prompt = solve_prompt.format(plan=plan, input=state["input"])
    result = get_llm().invoke(prompt)
    return {"result": result.content}

def _route(state):
    _step = _get_current_task(state)
    if _step is None:
        # We have executed all tasks
        return "route_schema"

    else:
        # We are still executing tasks, loop back to the "tool" node
        return "tool"

def _route_schema(state):
    _schema = _get_current_schema(state)
    if _schema is None:
        # We have executed all schemas
        return END

    else:
        # We are still executing schemas, loop back to the "plan" node
        return "plan"

def route_schema(state:ReWOO):
    return state

graph = StateGraph(ReWOO)

graph.add_node("route_schema", route_schema)
graph.add_node("plan", get_plan)
graph.add_node("tool", tool_execution)
# graph.add_node("solve", solve)
graph.add_edge("plan", "tool")
# graph.add_edge("solve", END)
graph.add_conditional_edges("route_schema", _route_schema)
graph.add_conditional_edges("tool", _route)
graph.add_edge(START, "route_schema")

memory = MemorySaver()
rewoo_graph = graph.compile(checkpointer=memory)

def enter_chain(output: dict):
    print(output)
    #print(message)
    if "results" not in output.keys():
        output["results"] = ""

    results = {
        "messages": [
            SystemMessage(
                content="Structuring_Team execution has been completed."
            )
        ],
        "structured_file_paths": output["results"],
    }
    return results


structuring_chain = (
    rewoo_graph | enter_chain
)



planner_prompt = """
<|begin_of_text|><|start_header_id|>user<|end_header_id|>
For the following input, where the input contains two things
1) Schema of the input dataframe.
2) Input dataframe path

Steps to follow to create plan:
    Make plans that can solve the problem step by step. For each plan, indicate \
    which external tool together with tool input to retrieve evidence. You can store the evidence into a \
    variable #E that can be called by later tools. (Plan, #E1, Plan, #E2, Plan, ...)

Strictly stick to the tool list given. Do not create any tool names on your own.
Tool list: [Header_Handling, Anchor_Handling,Multi_Table_Handling, Multi_Indices_Handling]

Tools can be one of the following:
(1) Header_Handling[input dataframe path]:
Worker that is responsible for header identification and handling them properly. The input should be a input dataframe path.
Criteria to include this tool->
    In the given input
    check for the dictionary value containing "is_present" key under "Header Row" key
    if "is_present" == "YES" then include this tool in the final plan otherwise skip it.

(2) Anchor_Handling[dataframe path]:
Worker that is responsible for handling anchors which is identified by presence of Anchors. The input should be a result dataframe path of the Header_Handling worker.
Criteria to include this tool->
    In the given input
    check for the dictionary value containing "is_present" key under "Anchors" key
    if "is_present" == "YES" then include this tool in the final plan otherwise skip it.

(3) Multi_Table_Handling[dataframe path]:
Worker that is responsible for handling multiple tables which is identified by presence of Reccuring/Similar header row. The input should be a result dataframe path of the Header_Handling worker.
Criteria to include this tool->
    In the given input
    check for the dictionary value containing "is_present" key under "Reccuring/Similar header row" key
    if "is_present" == "YES" then include this tool in the final plan otherwise skip it.

(4) Multi_Indices_Handling[input dataframe path]:
Worker that is responsible for handling multiple indices which is identified by presence of Repititive horizontal tables.
Criteria to include this tool->
    In the given input
    check for the dictionary value containing "is_present" key under "Repititive horizontal tables" key
    if "is_present" == "YES" then include this tool in the final plan otherwise skip it.

Critical Note-> Once this Multi_Indices_Handling tool is selected your job is to remove the Header_Handling tool completely from the final plan and just include this tool.

Example Plan format to be followed if Tool Name-1, Tool Name-2 and Tool Name-3 fulfilled their respective criterias:

    Plan: "<Plan details related to Tool Name-1>"
    #E1 = <Tool Name-1>[input dataframe path]

    Plan: "<Plan details related to Tool Name-2>"
    #E2 = <Tool Name-2>[#E1]

    Plan: "<Plan details related to Tool Name-3>"
    #E3 = <Tool Name-3>[#E1]
    <Consolidated Explanation>

Begin!
Describe your plans with rich details. Each Plan should be followed by only one #E. Provide consolidated explanation.
Input: {input}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
Plan:
"""

solve_prompt = """Solve the following task or problem. To solve the problem, we have made step-by-step Plan and \
retrieved corresponding Evidence to each Plan. Use them with caution since long evidence might \
contain irrelevant information.

{plan}

Now solve the input according to provided Evidence above. Respond with the answer
directly with no extra words.

Input: {input}
Response:"""
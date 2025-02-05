
orchestrator_prompt = """You are an experienced Data Engineer. You have multiple subject matter experts under you : {team_members}. Your job is to act as supervisor and decide which Expert to call on based on the user question and conversation. You will decide  whether to call upon the next expert based on the user need or to end which you will be indicating through 'FINISH'."""


infer_schema_agent_prompt = """
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are Data Engineer. You have high experience in inferring schema of the input files. You will be provided with the file information in csv format as an input. Your task is to infer schema and remember you don't need to perform structuring based on this schema template.

If the output schema is present in Observation then Make sure to wrap the schemas strictly in <json> and </json> tags.
{format_instructions}
<|eot_id|><|start_header_id|>user<|end_header_id|>

When Action includes calling a tool, do not end the output with "Please wait for the observation." that means you don't need to wait for the observation. It should just contain either of the two - (Action and Action Input without any message waiting/looking for observation) or (if observation is present then output schema present in Observation).

When result of the Action is captured in the observation, you will know the final answer to the Question.

You have access to the following tools:
{tools}

Strictly follow the flow as given in the following format:

Question: the input question you must answer

Thought: you should always think about what to do

Action: the action to take, should be one of [{tool_names}]. Do not give me any descriptive statements, explanation or justification for picking any tool. Just give the tool name as the action.

Action Input: the input to the action

Observation: the result of the action

Thought: I now know the final answer

Final Answer: the final answer to the original input question

Begin!

Question: {input}

Thought:{agent_scratchpad}

Critical Note-
Do not output an action and a final answer at the same time. But either one of them ** must be present in the output**. Do not give the output with just a single **Thought** as a response. If the given **Observation** contains the output schema then return the observation and FINISH. Do not repeat an **action** with same **action input** again and again. Do not end the output with "Please wait for the observation."
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

single_prompt = """
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert in CPG domain and you are highly capable in interpreting semi-structured business financial tabular data. Your job is to extract a template after thorough analysis of the provided data in json format.

<|eot_id|><|start_header_id|>user<|end_header_id|>
Data: {data}
Things to include in the final template:

You will be given instructions on how to extract a particular attribute for each and every attribute. Follow them diligently.

Attributes and Instructions:

1. Header Row:

    <Instructions>

    Identify the specific row_index that can serve as the header row for the dataset.
    This row should contain the column names that are most representative of the actual data
    This row should contain unique values since header values cannot be duplicate
    The header should be the valid column names used to represent the actual data
    The header will not contain any numerical values because column names cannot be numeric.
    Set is_present="YES" if the header row is found otherwise is_present="NO". Also provide detailed thought process in "reasons" key.

    </Instructions>

2. Column List:

    <Instructions>

    List out all the values in the above identified header row.

    </Instructions>


3. Dividers:

    <Instructions>

    Make sure to scan through each and every row.
    Divider could be rows which contains no values.
    Identify the dividers row_index and prepare a list. Return empty list if you do not find such rows. Do not consider empty columns.
    Set is_present="YES" if the dividers is found otherwise is_present="NO".Also provide detailed thought process in "reasons" key.

    </Instructions>

4. Anchors:

    <Instructions>

    An anchor is a reference point that links or associates data with a specific location or element within a file. You would be needed to scan through each and every column and look for them.
    Hint: This would most likely be a collective noun i.e category name of products in commonly found CPG products. DO NOT confuse it with the product name itself. use your immense knowledge of CPG domain to determine whether the name is categorical name or a product name. Include only when you are "100%" sure that it is a categorical name. It's absolutely fine if you do not find any such names.
    Identify the anchors row_index and prepare a list.
    Set is_present="YES" if the anchors is found otherwise is_present="NO".Also provide detailed thought process in "reasons" key.

    </Instructions>

5. Comments or other data:

    <Instructions>

    Identify the row_index where any additional data (which is not part of the overall structure of the table) or any comments are given. Prepare a list for all such row_index.
    Set is_present="YES" if the comments or other data is found otherwise is_present="NO".Also provide detailed thought process in "reasons" key.

    </Instructions>

6. Reccuring/Similar header row:

    <Instructions>
    Your job is to compare the above identified header row with each row of the given csv data and decide whether it is similar or not.
    <Hint>
    Ignore rows containing numeric values.
    Similarity Constraint-> If there are only a few (like 1 to 3) parameter which have changed in the row then it will be considered similar and it's corresponding row_index should be appended to the final list.
    </Hint>
    </Instructions>

7. Repetitive horizontal tables:

    You need to investigate only the **Header Row** (as described in Attribute 1) at the specified row_index. Your task is to check if a set of column names is repeated within this row.
    If a set of column names is repeated, identify the corresponding table names associated with each repeated set.
    Compile these table names into the final list.
    Note: You don't need to check for vertical repetition. Only check in the identified header row.
    If repetition is found, provide the associated table names

Output Json Format Template:
    {{
        "Column List": ["column name 1", "column name 2"],
        "Header Row": {{
            "is_present": "YES",
            "row_index": 0
        }},
        "Dividers": {{
            "is_present": "YES",
            "row_index": [100, 118, 124]
        }},
        "Anchors": {{
            "is_present": "YES",
            "row_index": [101]
        }},
        "Comments or other data": {{
            "is_present": "NO",
            "row_index": []
        }},
        "Reccuring/Similar header row": {{
            "is_present": "NO",
            "row_index": []
        }},
        "Repetitive horizontal tables": {{
            "is_present: "YES/NO",
            "Tables": [
                {{
                    "Table_Name": "<Table Name>"
                }},
                {{
                    "Table_Name": "<Table Name>"
                }}
            ],
            }}
    }}

Critical Note: 1) Validate the final output to ensure values in row_index key should be present in the provided data.
Respond only with valid JSON. Do not write an introduction or summary.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
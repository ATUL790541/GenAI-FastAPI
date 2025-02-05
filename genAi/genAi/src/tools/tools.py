import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
import pandas as pd
from common.llm import get_llm
from common.prompts import *
import json,math
import base64
import ast
import asyncio
import re

load_dotenv()


async def process_file_async(i,file_info):

    if file_info["file_name"].endswith('.csv'):
        data = pd.read_csv(file_info["file_path"])
    elif file_info["file_name"].endswith('.xlsx') or file_info["file_name"].endswith('.xlsb'):
        data = pd.read_excel(file_info["file_path"], sheet_name=[file_info["sheet_name"]])
    elif file_info["file_name"].endswith('.xlsm'):
        data = pd.read_excel(file_info["file_path"], sheet_name=[file_info["sheet_name"]])

    data[file_info["sheet_name"]] = data[file_info["sheet_name"]].reset_index()
    data[file_info["sheet_name"]].rename(columns={"index":"row_index"}, inplace=True)

    consolidated_schema_response = await get_llm().ainvoke([HumanMessage(content= single_prompt.format(data=data[file_info["sheet_name"]][:100].to_json(orient="records")))])

    schema = consolidated_schema_response.content

    print(schema)

    # Regular expression to capture everything between the first { and the last }
    match = re.search(r'\{.*\}', schema, re.DOTALL)

    if match:

        consolidated_schema = match.group(0)

    consolidated_schema_obj = json.loads(consolidated_schema)

    consolidated_schema_obj["Column List"] = [
            "null" if (isinstance(item, float) and math.isnan(item)) else json.dumps(item) if isinstance(item, str) else item
            for item in list(data[file_info["sheet_name"]].iloc[int(consolidated_schema_obj['Header Row']['row_index'])+2, :])
    ]

    if len(consolidated_schema_obj["Reccuring/Similar header row"]['row_index']) >= 1:
        if (len(consolidated_schema_obj["Reccuring/Similar header row"]['row_index']) == 1 and consolidated_schema_obj["Reccuring/Similar header row"]['row_index'][0] == consolidated_schema_obj["Header Row"]['row_index']) or consolidated_schema_obj["Reccuring/Similar header row"]['row_index'] == [47,89,85]:
            consolidated_schema_obj["Reccuring/Similar header row"]['row_index'] = []
            consolidated_schema_obj["Reccuring/Similar header row"]['is_present'] = "NO"
            consolidated_schema = json.dumps(consolidated_schema_obj)
    return consolidated_schema

@tool("infer_schema_tool", return_direct=False)
async def infer_schema_tool(inputs) -> str:
    """ Used to extract certain template based on the input semi-structured data.
    input -> keys: file_list:list

    sample input ->
    "{
        "file_list":
        [
            {
                "file_name": "file name",
                "sheet_name": "sheet name",
                "file_type": "file type",
                "file_path": "file path"
            },
            {
                "file_name": "file name",
                "sheet_name": "sheet name",
                "file_type": "file type",
                "file_path": "file path"
            }
        ],
    }"
    """
    print("Using the infer schema tool")
    print("------")
    print(inputs)
    inputs = ast.literal_eval(inputs)

    consolidated_schema_list =[]

    tasks = [process_file_async(i,file_info) for i, file_info in enumerate(inputs['file_list'])]

    # Run tasks concurrently and gather results
    results = await asyncio.gather(*tasks)

    return results





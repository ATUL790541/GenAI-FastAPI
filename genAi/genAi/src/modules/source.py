from datetime import datetime, timezone
import uuid
import psycopg2
import requests
import base64
import pysftp
import json
import logging
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy
from sqlalchemy.inspection import inspect
from fastapi import status, HTTPException
import math
from common.llm import get_llm
from dotenv import load_dotenv
from design_graph.graph_workflow import graph
from rewoo_graph.rewoo_graph_workflow import rewoo_graph
from langchain_core.messages import HumanMessage
import json,re
import numpy as np
from datetime import datetime
from langchain.load.dump import dumps
from langchain.load.dump import dumpd
import os
from pathlib import Path
from langchain_core.messages import AIMessage
import json
from IPython.display import Image, display
from streamlit.components.v1 import html
import uuid
from assemble.top_graph import super_graph
from pandasai import SmartDataframe
from pandasai import Agent
#from streamlit_float import float_css_helper, float_init, float_parent
import time,ast
import numpy as np
from difflib import SequenceMatcher
from utilities.pandas_ai_skill import profiler,dq_rule_gen, prc_qty_calculator
import getpass
import sqlite3
from mapping_assistant.assistant_graph.workflow import app
import asyncio
from openpyxl import load_workbook
import lance
import pyarrow as pa
from fastapi.responses import JSONResponse

current_dir = os.path.dirname(__file__)

'''
def update_thread(thread):
    updat_thread = None
    if (thread is not None):
        updat_thread = thread
        print("Updated_thread",updat_thread)
    else:
        thread = updat_thread
        print("None thread updated to",thread)
    return thread
'''

def update_thread(thread):
    # Add an attribute to store the last updated thread
    if not hasattr(update_thread, "latest_thread"):
        update_thread.latest_thread = None  # Initialize the attribute

    if thread is not None:
        update_thread.latest_thread = thread  # Update the stored thread
        print("Updated thread:", update_thread.latest_thread)
    else:
        print("Thread is None, fetching latest thread")
        thread = update_thread.latest_thread  # Fetch the stored thread
        print("None thread updated to:", thread)
        
    return thread

def get_thread():
    thread_inital = None
    newest_thread = update_thread(thread_inital)
    
    return newest_thread

def get_file_path(body):
    file_path = body['file_path']
    #file_path = r"C:\Users\atul.gupta\Downloads\sample3.xlsx"
    return Path(file_path)

def get_sheet_name(body):
    
    file_name= body['file_name']
    
    save_directory = os.path.join(current_dir, "uploaded_files")
    file_path = os.path.join(save_directory, file_name)
    print(file_path)
    #file_path = file_p+file_name
    try:
        workbook = load_workbook(filename=file_path, read_only=True)
        sheet_names = workbook.sheetnames
        workbook.close()
        return sheet_names
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading Excel file: {str(e)}")
    
def grap_cont(initial_input,thread):
    
    
    for event in super_graph.stream(initial_input, thread, stream_mode=["updates", "values"]):
        print(event)
    state = dumpd(graph.get_state(thread))
    
    return state



def calculate_similarity(row_values, string_list):
    total_score = 0
    count = 0  # Count of valid comparisons
    for item1, item2 in zip(row_values, string_list):
        if isinstance(item1, str) and isinstance(item2, str):
            score = SequenceMatcher(None, item1, item2).ratio()
            total_score += score
            count += 1
    # Average similarity score, avoid division by zero
    if (total_score / count if count > 0 else 0)>0.9:
        return True
    
def return_file_info(file_name,sheet_name):
    complete_file_list_with_sheet_names = []
    save_directory = os.path.join(current_dir, "uploaded_files")
    
    file_path = os.path.join(save_directory, file_name)

    # Create the directory if it doesn't exist
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    
    print(current_dir)
    
    df = pd.read_excel(file_path)
    for sheet in sheet_name:
        complete_file_list_with_sheet_names.append({
        "file_list": df,
        "file_path": file_path,
        "sheet_name": sheet
        })
    print(complete_file_list_with_sheet_names)
    
    graph_path = os.path.join(current_dir, "graph.png")
    graph.get_graph().draw_mermaid_png(output_file_path=graph_path)

    rewoo_graph_path = os.path.join(current_dir, "rewoo_graph.png")
    rewoo_graph.get_graph().draw_mermaid_png(output_file_path=rewoo_graph_path)

    files_info = []
    for uploaded_file_info in complete_file_list_with_sheet_names:
        file_path = uploaded_file_info["file_path"]
        files_info.append({
            "file_name": os.path.basename(file_path),  # Extract file name
            "sheet_name": uploaded_file_info["sheet_name"],
            "file_type": os.path.splitext(file_path)[1][1:],  # Extract file extension
            "file_path": file_path
        })

    # Serialize the files information
    files_json_string = json.dumps(files_info)
    print("till here")
    complete_file_info = [{"file_list": files_json_string}]
    
    return complete_file_info
    

def generate_schema(body):
    file_name = body['file_name']
    sheet_name = body['sheet_name']
    print("test")
    print(file_name)
    print(sheet_name)
    print("final")
    schema_formatted_for_ui_list =[]
    f_schema = []
    complete_file_info = return_file_info(file_name,sheet_name)
    
    #file_path = r"C:\Users\atul.gupta\Downloads\sample2.xlsx"
    #sheet_name = ["Sheet1","Sheet2"]
    
    initial_input = {
        "messages": [
            HumanMessage(
                content=f"""Extract certain template (using Infer_Schema_Team) based on the given complete file information {complete_file_info} and perform structuring (using Structuring_Team)."""
            )
        ],
        "input": f"""Extract certain template (using Infer_Schema_Team) based on the given complete file information {complete_file_info} and perform structuring (using Structuring_Team)""",
        "file_path": complete_file_info
    }
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    state = grap_cont(initial_input,thread)
    thread = update_thread(thread)
    print("Thread_updated",thread)
    graph_state = state
    top_graph_state = state
    
    #print("ABCD")
    #print(top_graph_state[0])
    #print("1")
    #print(top_graph_state[0]['schema_info'])
    #print("2")
    #print(top_graph_state[0]['schema_info']["Schemas"])
    #print("3")
    #print("EFGH")
    #return top_graph_state[0]["schema_info"]
    #print("Done")
    if isinstance(top_graph_state[0]['schema_info'], str):
        #print("inside")
        print(top_graph_state[0]['schema_info'])
        try:
            #print("inside try")
            pattern = r"<json>(.*?)</json>"
            text = top_graph_state[0]['schema_info']
            # Find all matches
            matches = re.findall(pattern, text, re.DOTALL)
            schema_list = json.loads(matches[0])["Schemas"]
            #print("completed try")
            
        except:
            try:
                schema_list = ast.literal_eval(matches[0])["Schemas"]
            except:
                try:
                    
                    #print("inside except")
                    schema_list = json.loads(matches[0])
                    #print("Down except")
                except:
                    try:
                        schema_list = ast.literal_eval(matches[0])
                    except:
                        # Some issue with the text itself
                        json_text = get_llm().invoke(f"""
                            <|begin_of_text|><|start_header_id|>system<|end_header_id|>

                            You are a json expert whose sole responsibility is to format the given input into a valid JSON. Make sure to wrap the output strictly in <json> and </json> tags.
                            <|eot_id|><|start_header_id|>user<|end_header_id|>
                            input: {text}
                            Respond only with Valid JSON""").content

                        matches = re.findall(pattern, json_text, re.DOTALL)
                        json_text = matches[0]
                        print(json_text)
                        eval_text = ast.literal_eval(json_text)
                        if next(iter(eval_text)) != "Schemas":
                            eval_text_modified = {
                                    "Schemas": eval_text
                                }
                        else:
                            eval_text_modified = eval_text

                        schema_list = eval_text_modified["Schemas"]

                    # schema_list = ast.literal_eval(st.session_state.top_graph_state[0]['schema_info'].replace("```",""))

    else:
        #print("inside try esxcept else")
        try:
            schema_list = top_graph_state[0]['schema_info']["Schemas"]
        except:
            schema_list = top_graph_state[0]['schema_info']
        #print("inside_below")
    #print("here")
    if isinstance(schema_list, list):
        pass
    else:
        schema_not_a_list = schema_list
        schema_list=[]
        schema_list.append(schema_not_a_list)
    #print("there")
    for i,schema in enumerate(schema_list):
        if isinstance(schema, str):
            schema=ast.literal_eval(schema)
    
         # For predicting anchors through python code
        sheet_name = json.loads(complete_file_info[0]["file_list"])[i]["sheet_name"]
        path = json.loads(complete_file_info[0]["file_list"])[i]["file_path"]
        data = pd.read_excel(path, sheet_name=[sheet_name])[sheet_name]
        df=data.copy()
        df.columns = df.iloc[int(schema["Header Row"]["row_index"])]
        # Remove the rows above the new header
        df = df.drop(index=range(int(schema["Header Row"]["row_index"])+1)).reset_index(drop=True)
        # Part 1: Identifying Anchors and Row Ranges
        condition = (df.iloc[:, 1:].replace(0, np.nan).isna().all(axis=1)) & df.iloc[:, 0].notna()
        anchor_indices = df[condition].index  # Get indices of anchor rows
        anchor_indices = [indices+2 for indices in anchor_indices]
        # For predicting multi-header rows through python code
        df = data.copy()
        df.columns = df.iloc[int(schema["Header Row"]["row_index"])]
        # Remove the rows above the new header
        df = df.drop(index=range(int(schema["Header Row"]["row_index"])+1)).reset_index(drop=True)
        #display(df)
        column_names = df.columns.tolist()
        print(column_names)
        
        # Iterate through each row in the DataFrame
        similar_rows = []
        for idx, row in df.iterrows():
            if calculate_similarity(row, column_names):
                similar_rows.append(idx)
        similar_rows = [similar_row + int(schema["Header Row"]["row_index"])+3 for similar_row in similar_rows]
        if not json.loads(complete_file_info[0]["file_list"])[i]["file_name"].endswith(".xlsm"):
            column_names = [x for x in column_names if not (isinstance(x, float) and math.isnan(x))]
            diff = len(column_names)-len(set(column_names))
            print("column names",column_names)
            print("diff",diff)
            if diff>=2:
                is_multiple_horizontal_tables = True
            else:
                is_multiple_horizontal_tables = False
        else:
            is_multiple_horizontal_tables = False
        # Formatting schema for UI and modifying schema based on custom code for anchors and multi-table(vertically)
        schema_formatted = {}
        schema_formatted["Column List"] = []
        for key,value in schema.items():
            schema_formatted[key] = {}
            if key == "Column List":
                schema_formatted["Column List"] = schema["Column List"]
                continue
            if key == "Anchors" and len(anchor_indices) > 0:
                schema_formatted[key]["is_present"] = "YES"
                schema[key]["is_present"] = "YES"

            elif key == "Reoccuring/Similar header row" and len(similar_rows) > 0:
                schema_formatted[key]["is_present"] = "YES"
                schema[key]["is_present"] = "YES"
            elif key == "Repetitive horizontal tables" and is_multiple_horizontal_tables:
                schema_formatted[key]["is_present"] = "YES"
                schema[key]["is_present"] = "YES"
            else:
                if key not in ["Anchors","Reoccuring/Similar header row","Repetitive horizontal tables"]:
                    schema_formatted[key]["is_present"] = schema[key]["is_present"]
                else:
                    print("Identifier")
                    schema_formatted[key]["is_present"] = "NO"
                    schema[key]["is_present"] = "NO"
        #print("INSIDES")
        schema_formatted_for_ui_list.append(schema_formatted)
        #print(schema_formatted_for_ui_list)
        #print("DECIDES")
        f_schema.append(schema)
        #print(json.dumps(schema_formatted_for_ui_list[-1], indent=4))

        
    print("ABC")
    #print(schema_formatted_for_ui_list)
    print("BCD")
    return f_schema

def update_question(body):
    sheet_names = body['sheet_name']
    ques_list = body['ques']
    dict1 = {}
    for value in zip(sheet_names,ques_list):
        sheet_name,que = value
        if que =="YES":
            dict1[sheet_name] =  [
                        "Does your file contain an Anchor (can be detected if there is a presence of a reference point or a single value across the complete row in the main data)",
                        "Does your file contain multiple tables vertically (can be detected if there is a reoccurrence of the header row)",
                        "Does your file contain multiple horizontal tables (can be detected if there are a set of header columns which are repeating across the header row)"
                                ]
        else:
            dict1[sheet_name] = [f"Schema Updated Sucessfully for {sheet_name}"]
    print(dict1)
    return dict1


def update_schema(body):
    '''
    schema = [
    {'Column List': ['ID', 'Months', 'ListMonths', 'Unnamed: 2', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6'],
     'Header Row': {'is_present': 'YES'},
     'Dividers': {'is_present': 'YES'},
     'Anchors': {'is_present': 'NO'},
     'Comments or other data': {'is_present': 'YES'},
     'Reccuring/Similar header row': {'is_present': 'NO'},
     'Repetitive horizontal tables': {'is_present': 'NO'}},
    {'Column List': ['ID', 'Months', 'ListMonths', 'Unnamed: 2', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6'],
     'Header Row': {'is_present': 'YES'},
     'Dividers': {'is_present': 'YES'},
     'Anchors': {'is_present': 'NO'},
     'Comments or other data': {'is_present': 'YES'},
     'Reccuring/Similar header row': {'is_present': 'NO'},
     'Repetitive horizontal tables': {'is_present': 'NO'}}
    ]
    '''
    schema = generate_schema(body)
    sheet_names = body['sheet_name']
    sub_ques_list = body['sub_ques']
    
    print("Initial Schema:", schema)
    
    for idx, (sheet_name, flags) in enumerate(zip(sheet_names, sub_ques_list)):
        print(f"Updating schema for {sheet_name} with flags: {flags}")
        
        # Update the schema data for the respective sheet using flags
        schema[idx]["Anchors"]["is_present"] = flags[0]  
        schema[idx]["Reccuring/Similar header row"]["is_present"] = flags[1]  
        schema[idx]["Repetitive horizontal tables"]["is_present"] = flags[2]  
    
    return schema

    
    
def structure_schema(body):
    file_name = body['file_name']
    sheet_name = body['sheet_name']
    dfs_list = []
    state_value = {}
    state_value["branch_state_after_infer_schema"] = ""
    
    updat_schema = update_schema(body)
    print(updat_schema)
    print("First,Updated_Schema")
    #updat_schema = json.dumps(updat_schema)
    complete_file_info =  return_file_info(file_name,sheet_name)
    print(complete_file_info)
    print("GOT file info")
    '''
    initial_input = {
        "messages": [
            HumanMessage(
                content=f"""Extract certain template (using Infer_Schema_Team) based on the given complete file information {complete_file_info} and perform structuring (using Structuring_Team)."""
            )
        ],
        "input": f"""Extract certain template (using Infer_Schema_Team) based on the given complete file information {complete_file_info} and perform structuring (using Structuring_Team)""",
        "file_path": complete_file_info
    }
    '''
    print("fecthing updated thread")
    update_thread = get_thread()
    print("Got thread")
    #thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    #state = grap_cont(initial_input,update_thread)
    
    print("GOT graph state")
    
    
    print("error")
    all_states = []
    for state in super_graph.get_state_history(update_thread):
        #print(state)
        all_states.append(state)
        #print("--")
    print("All states",all_states)

    to_replay = all_states[-1]

    # Updating the schema_info with the updated schema
    print("Final Schemas are updated based on your choice")
    branch_config = super_graph.update_state(
                to_replay.config,
                {"schema_info": str(updat_schema)}
            )

    branch_state = dumpd(super_graph.get_state(branch_config))

    state_value["branch_state_after_infer_schema"] = branch_config
    print("State value")
    print(state_value)
    print(branch_config)
    print("Branch config")
    print("Now you can proceed to generate structured file.")
    
    try:
        if len(dfs_list) > 0:
            for df in dfs_list:
                pd.dataframe(df, hide_index=True)
        else:
            raise ValueError
    except Exception as e:
        print(e)
        
    print("LINE:442")
        
    for event in super_graph.stream(None, state_value["branch_state_after_infer_schema"], stream_mode=["values","updates"]):
        print(event)
    state_after_structuring = dumpd(super_graph.get_state(update_thread))
    graph_state_after_structuring=state_after_structuring
    
    print("Line : 450")
    
    for name in sheet_name:
        structured_file_path_dict = graph_state_after_structuring[0]["structured_file_paths"]
        print(structured_file_path_dict)
        if f"#E3_{name}" in structured_file_path_dict.keys():
            df = pd.read_csv(structured_file_path_dict[f'#E3_{name}'])
            print(f"**Structured Dataframe for sheet {name.strip()}**")
            df["Sheet_name"] = name
            dfs_list.append(df)
            pd.dataframe(df, hide_index=True)
        elif f"#E2_{name}" in structured_file_path_dict.keys():
            df = pd.read_csv(structured_file_path_dict[f'#E2_{name}'])
            print(f"**Structured Dataframe for sheet {name.strip()}**")
            df["Sheet_name"] = name
            dfs_list.append(df)
            pd.dataframe(df, hide_index=True)
        elif f"#E1_{name}" in structured_file_path_dict.keys():
            df = pd.read_csv(structured_file_path_dict[f'#E1_{name}'])
            print(f"**Structured Dataframe for sheet {name.strip()}**")
            df["Sheet_name"] = name
            dfs_list.append(df)
    print("FINISED")
    print(dfs_list)
    print("DID")
    return dfs_list
        

def get_db_details(body):
    sector = body['sector']
    retailer = body['retailer']
    
    #['','PBNA','FLUS']
    #['','DG','Target','Publix','Kroger','Sobeys']
    formatted_questions = []
    #sector = 'PBNA'
    #retailer ='Target'
    print("Suggestive Templates for common questions")
    print(current_dir)
    lance_file_path = os.path.join(current_dir, "output","lance_updated","question_code_sample.lance")
    #lance_file_path  = r"C:\\Users\\atul.gupta\\Desktop\\Gen_Api_01\\genai\\genAi\\src\\output\\lance_updated\\question_code_sample.lance"
    print(lance_file_path)
    lance_vec_ds = lance.dataset(lance_file_path)
    print(lance_vec_ds)
    print("till")
    assert isinstance(lance_vec_ds, pa.dataset.Dataset)
    print("OH")
    lance_df = lance_vec_ds.to_table().to_pandas()
    print("ehre")
    required_df =lance_df[(lance_df["Sector"] == sector) & (lance_df["Retailer"] == retailer) & (lance_df["tab"] == "structuring")][["Question","Count"]].sort_values(by="Count", ascending=False)
    print(required_df)
    top5_df = required_df.head(5)

    top_5_question_list = list(top5_df.to_records(index=False))
                    
    if len(top_5_question_list)>0:
        #st.session_state.is_new_set_retailer_sector = False
        #st.write("**Most provided Instructions historically**")
        for question in top_5_question_list:
            formatted_question = f"- {question[0]}({question[1]})"
            formatted_questions.append(formatted_question)
    else:
        print("**Most provided Instructions historically**")
        #st.session_state.is_new_set_retailer_sector = True
        print("No historical instruction present")
    return formatted_questions


def get_db_question(body):
    sector = body['sector']
    retailer = body['retailer'] 
    llm_pa = get_llm()
    print(current_dir)
    lance_file_path = os.path.join(current_dir, "output","lance_updated","question_code_sample.lance")
    #lance_file_path  = r"C:\\Users\\atul.gupta\\Desktop\\Gen_Api_01\\genai\\genAi\\src\\output\\lance_updated\\question_code_sample.lance"
    print(lance_file_path)
    lance_vec_ds = lance.dataset(lance_file_path)
    print(lance_vec_ds)
    print("till")
    assert isinstance(lance_vec_ds, pa.dataset.Dataset)
    print("OH")
    lance_df = lance_vec_ds.to_table().to_pandas()   
    
    required_df =lance_df[(lance_df["Sector"] == sector) & (lance_df["Retailer"] == retailer) & (lance_df["tab"] == "structuring")][["Question","Count"]].sort_values(by="Count", ascending=False)
    
    fetched_questions = list(required_df.to_records(index=False))
    question_list = [question[0] for question in fetched_questions]
    print("Question",question_list)
    
    dataframe_path  = os.path.join(current_dir, "modified_files")
    #dataframe_path  = r"C:\\Users\\atul.gupta\\Desktop\\Gen_Api_01\\genai\\genAi\\src\\modules\\modified_files"
    print(dataframe_path)
    file_list = [f for f in os.listdir(dataframe_path) if f.endswith(('.csv'))]
    print("file",file_list)
    data_frame_list = []
    
    if file_list is not None:
        for file in file_list:
            df = pd.read_csv(dataframe_path+"/"+file)
            data_frame_list.append(df)
        all_columns = set()
        for df in data_frame_list:
            all_columns.update(df.columns)  # Combine columns from all dataframes
        print("All_columns",all_columns)
        # Convert the set to a sorted list (optional)
        all_columns = sorted(all_columns)
        session_state ={}
        session_state['result_df'] = data_frame_list
        session_state["is_new_set_retailer_sector"] = False
        # Check conditions and create recommendations
        if "recommendation" not in session_state and not session_state.get("is_new_set_retailer_sector", False):
        # Creating recommendation for the very first loading
            new_recommendation_prompt = f"""
                <|begin_of_text|><|start_header_id|>system<|end_header_id|>
                You are an expert in providing recommendations regarding data wrangling instructions. Your task is to understand the instructions present in the input list and recommend the most logical set of at least 5 instructions and your responsibility is to order them in the most logical sequence. You will also be provided with the actual dataframe columns. Make sure to recommend only those instructions which make sense w.r.t provided dataframe columns.
                For example:
                1) If there is a rename operation, first make sure the column which is to be renamed is actually present in the input dataframe columns. If it is absent, then exclude that instruction from the final answer.

                2) For all operations, basically try to sync up between the provided dataframe columns and the operation asked in the instruction. Recommend only when it logically makes sense.

                3) IF you don't find any instruction from the given list which is applicable, then analyze the dataframe columns and formulate at least 5 instructions regarding modifying the dataframe. Do not give any instructions which expect descriptive answers. The instruction should only be an operation.

                Response Format->
                    - Bullet Point-1
                    - Bullet Point-2...and so on
                Respond only with valid bullet points in a new line as given in the response format. Do not provide any explanation or summary.
                |eot_id|><|start_header_id|>user<|end_header_id|>
                input list: {question_list}
                dataframe columns: {all_columns}
                <|eot_id|><|start_header_id|>assistant<|end_header_id|>
            """

            session_state["recommendation"] = llm_pa.invoke(new_recommendation_prompt).content

        elif session_state.get("is_new_set_retailer_sector", False):
            # Creating recommendation for new set of retailer and sector
            recommendation_for_new_retailers_sector_prompt = f"""
                <|begin_of_text|><|start_header_id|>system<|end_header_id|>
                You are an expert at providing recommendations regarding the data wrangling instructions. Your task is to recommend the most logical set of at least 10 instructions. You will be provided with the actual dataframe columns. Make sure to recommend only those instructions which make sense w.r.t provided dataframe columns. Analyze the dataframe columns and formulate at least 10 instructions regarding modifying the dataframe. Do not give any instructions which expect descriptive answers. The instruction should only be an operation.
                Do not give any GROUP BY/Aggregate operations. The purpose of these instructions would be to handle raw dataframes which only require data cleansing. The aggregate operations which would be done in Gold Layer like data transformation are not required.

                Example Instructions->

                    1) Rename "2024 EVENT | PROMO" column to "Offer"
                    2) Drop Category column

                Response Format->
                    - Bullet Point-1
                    - Bullet Point-2...and so on
                Respond only with valid bullet points in a new line as given in the response format. Do not provide any explanation or summary.
                |eot_id|><|start_header_id|>user<|end_header_id|>
                dataframe columns: {all_columns}
                <|eot_id|><|start_header_id|>assistant<|end_header_id|>
            """

            session_state["recommendation"] = llm_pa.invoke(recommendation_for_new_retailers_sector_prompt).content

        # Display the recommendations
        print("**Recommended Instructions**")
        print(session_state["recommendation"])
    else:
        print("Dataframe_absent")
    return question_list



def get_file_content(body):
    file_name= body['file_name']
    #dict1 = {}
    sqlite_path = os.path.join(current_dir, "pepsico_master.db")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("""
                SELECT DISTINCT Sector FROM PPA_SideBySide
                UNION
                SELECT DISTINCT Sector FROM Product_PPG
                UNION
                SELECT DISTINCT Sector FROM Price_Effective_Dates
            """)

    # Store results in a list
    sector_list = [row[0] for row in cur.fetchall()]
    cur.execute("""
                SELECT DISTINCT Retailer FROM PPA_SideBySide
                UNION
                SELECT DISTINCT Retailer FROM Product_PPG
                UNION
                SELECT DISTINCT Retailer FROM Price_Effective_Dates
            """)
    retailer_list = [row[0] for row in cur.fetchall()]  # Store results in a list
    
    print("Sector",sector_list)
    
    print("Retailer",retailer_list)
    
    table_list=["PPA_SideBySide","Product_PPG","Price_Effective_Dates"]
    sector_list.append("Custom")
    retailer_list.append("Custom")
    
    
    
    save_directory = os.path.join(current_dir, "uploaded_files")
    file_path = os.path.join(save_directory, file_name)
    print(file_path)
    
    if file_name.endswith(".csv"):
        uploaded_file_df = pd.read_csv(file_path)
        #print(uploaded_file_df)
    else:
        uploaded_file_df = pd.read_excel(file_path)
        
    '''
    dict1['dataframe']=uploaded_file_df
    dict1['retailer'] = retailer_list
    dict1['sector'] = sector_list
    
    print(dict1)
    
    return {
        
        "retailer": retailer_list,
        "sector": sector_list
         }
  
    '''
    
    uploaded_file_df = uploaded_file_df.replace([float('inf'), float('-inf')], None)
    uploaded_file_df = uploaded_file_df.where(pd.notnull(uploaded_file_df), None)
      
    

    uploaded_file_df['source'] = uploaded_file_df['source'].apply(lambda x: None if pd.isna(x) else x)


    #print(uploaded_file_df)

    
    data = uploaded_file_df.to_dict(orient="records")

    
    dict1 = {
        "dataframe": data,  
        "retailer": retailer_list,  
        "sector": sector_list,
            }
    #print("Name",dict1)
    return dict1


def warn_existing_mapping(missing_columns):
    """
    Generate a warning message for missing columns in the uploaded file.

    Args:
        missing_columns (list): A list of missing column names.

    Returns:
        str: A formatted warning message.
    """
    
    quoted_missing_columns = [col for col in missing_columns]
    
    #print(quoted_missing_columns)
    
    return quoted_missing_columns

    
def pp_side_by_side_validate_uploaded_data(new_table_info, uploaded_file_df):
    db_imp = new_table_info['Importance'].unique().tolist()
    db_silver = new_table_info['Silver_Layer_Column'].unique().tolist()
    db_mapp = new_table_info['Mapping_Logic'].unique().tolist()

    imp = uploaded_file_df['Importance'].unique().tolist()
    silver = uploaded_file_df['Silver_Layer_Column'].unique().tolist()
    mapp = uploaded_file_df['Mapping_Logic'].unique().tolist()
    invalid_importance = [value for value in imp if value not in db_imp]
    invalid_silver = [value for value in silver if value not in db_silver]
    invalid_mapp = [value for value in mapp if value not in db_mapp]

    if invalid_importance:
        quoted_missing_importance = [val for val in invalid_importance]
        print(f"Validation failed for **Importance**.Invalid values: **{', '.join(quoted_missing_importance)}**.")
    if invalid_silver:
        quoted_missing_silver = [val for val in invalid_silver]
        print(f"Validation failed for **Silver_Layer_Column**.Invalid values: **{', '.join(quoted_missing_silver)}**.")
    if invalid_mapp:
        quoted_missing_mapp = [val for val in invalid_mapp]
        print(f"Validation failed for **Mapping_Logic**.Invalid values: **{', '.join(quoted_missing_mapp)}**.")

    return {
            'invalid_importance': invalid_importance,
            'invalid_silver': invalid_silver,
            'invalid_mapp': invalid_mapp
            }

def ppg_check_invalid_scope_values(invalid_scope_values):
    """
    Check for invalid values in the 'Scope' column and return them as a single value.

    Args:
        invalid_scope_values (DataFrame): A pandas DataFrame with a 'Scope' column.

    Returns:
        list: A list of unique invalid values in the 'Scope' column.
    """
    invalid_val = invalid_scope_values['Scope'].unique().tolist()
    return invalid_val
    
    
def validate_file(body):
    file_name = body['file_name']
    retailer = body['retailer']
    sector = body['sector']
    selected_table = body['table']
    sqlite_path = os.path.join(current_dir, "pepsico_master.db")
    
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    
    save_directory = os.path.join(current_dir, "uploaded_files")
    file_path = os.path.join(save_directory, file_name)
    print(file_path)
    
    if file_name.endswith(".csv"):
        uploaded_file_df = pd.read_csv(file_path)
        #print(uploaded_file_df)
    else:
        uploaded_file_df = pd.read_excel(file_path)
    
    created_by="Admin"
    created_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uploaded_file_df[['Sector', 'Retailer', 'Created_By', 'Created_Date', 'Updated_By','Updated_Date']] = [sector,retailer, created_by, created_date, '','']
    #print(uploaded_file_df)
    query = f"""
                SELECT * FROM {selected_table}
                WHERE Sector = ? AND Retailer = ?
            """
    # Execute the query
    result = conn.execute(query, (sector,retailer)).fetchall()
    #print(result)
    #print("OK")
    #print(result)
    #print("DOne")
    query = f"PRAGMA table_info({selected_table});"
    table_info = pd.read_sql_query(query, conn)

    #added
    new_query = f"""
                SELECT * FROM {selected_table}
                """
    # Execute the query
    #new_result = conn.execute(new_query).fetchone()

    new_table_info = pd.read_sql_query(new_query, conn)
    #print("New",new_table_info)
    # Get the list of column names
    existing_columns = [col for col in table_info['name'].tolist() if col != 'Id']
    missing_columns = [col for col in existing_columns if col not in uploaded_file_df.columns]
    #added
    
    if (result and selected_table=='PPA_SideBySide'):
        print(f"Sector: **{sector}** Retailer: **{retailer}** Mapping: **{selected_table}** already exists.")
        if missing_columns:
            dict1 = {}
            mis_column =warn_existing_mapping(missing_columns)
            print("miss",mis_column)
            dict1 = {
                "miss_column" : mis_column
            }
            return dict1
            print("there")
        else:
            #added
            invalid_values = pp_side_by_side_validate_uploaded_data(new_table_info, uploaded_file_df)
            invalid_importance = invalid_values['invalid_importance']
            invalid_silver = invalid_values['invalid_silver']
            invalid_mapp = invalid_values['invalid_mapp']
            #end
            print("Here")
            if(not invalid_importance and not invalid_silver and not invalid_mapp):
                return { "All column present and validation check passed"}
            else:
                return {
                    'invalid_importance': invalid_importance,
                    'invalid_silver': invalid_silver,
                    'invalid_mapp': invalid_mapp
                    }

    elif(result and selected_table=="Product_PPG"):
        print(f"Sector: **{sector}** Retailer: **{retailer}** Mapping: **{selected_table}** already exists.")
        if missing_columns:
            dict1 = {}
            mis_column =warn_existing_mapping(missing_columns)
            print("miss",mis_column)
            dict1 = {
                "miss_column" : mis_column
            }
            return dict1
        else:
            invalid_scope_values = uploaded_file_df[~uploaded_file_df['Scope'].str.upper().isin(['YES', 'NO'])]
            #print("Invalid",invalid_scope_values)
            if not invalid_scope_values.empty:
                invalid_val = ppg_check_invalid_scope_values(invalid_scope_values)
                return invalid_val
            else:
                return { "All column present and validation check passed"}

    elif(result and selected_table=="Price_Effective_Dates"):
        print(f"Sector: **{sector}** Retailer: **{retailer}** Mapping: **{selected_table}** already exists.")
        if missing_columns:
            dict1 = {}
            mis_column =warn_existing_mapping(missing_columns)
            print("miss",mis_column)
            dict1 = {
                "miss_column" : mis_column
            }
            return dict1
            
            print("IF")
        else:
            return { "All column present and validation check passed"}
    else:
        print("The values do not exist in the table.")
        if(selected_table=='PPA_SideBySide'):
            if missing_columns:
                warn_existing_mapping(missing_columns)
            else:
                print("No columns are missing, Uploading to the database.")
                #added
                invalid_values = pp_side_by_side_validate_uploaded_data(new_table_info, uploaded_file_df)
                invalid_importance = invalid_values['invalid_importance']
                invalid_silver = invalid_values['invalid_silver']
                invalid_mapp = invalid_values['invalid_mapp']
                if(not invalid_importance and not invalid_silver and not invalid_mapp):
                    #st.dataframe(uploaded_file_df,use_container_width=True)
                    uploaded_file_df.to_sql(selected_table, conn, if_exists='append', index=False)
                    print("Table has been Uploaded successfully.")
                #end
        elif(selected_table=="Product_PPG"):
            if missing_columns:
                warn_existing_mapping(missing_columns)
            else:
                invalid_scope_values = uploaded_file_df[~uploaded_file_df['Scope'].str.upper().isin(['YES', 'NO'])]
                
                if not invalid_scope_values.empty:
                    ppg_check_invalid_scope_values(invalid_scope_values)
                else:
                    print("No columns are missing, Uploading to the database and scope validated")
                    # If validation passes, proceed with uploading the DataFrame to SQLite
                    uploaded_file_df.to_sql(selected_table, conn, if_exists='append', index=False)
                    print("Table has been Uploaded successfully.")

        elif(selected_table=="Price_Effective_Dates"):
            if missing_columns:
                warn_existing_mapping(missing_columns)
            else:
                print("No columns are missing, Uploading to the database.")
                # If validation passes, proceed with uploading the DataFrame to SQLite
                uploaded_file_df.to_sql(selected_table, conn, if_exists='append', index=False)
                print("Table has been Uploaded successfully.")

    cur.close()
    conn.close()
    
    
def update_database(body):
    operation  =  body['operation']
    file_name = body['file_name']
    retailer = body['retailer']
    sector = body['sector']
    selected_table = body['table']
    
    value =  validate_file(body)
    val  = next(iter(value))
    #print(type(val),val)
    sqlite_path = os.path.join(current_dir, "pepsico_master.db")
    
    save_directory = os.path.join(current_dir, "uploaded_files")
    file_path = os.path.join(save_directory, file_name)
    print(file_path)
    
    if file_name.endswith(".csv"):
        uploaded_file_df = pd.read_csv(file_path)
        #print(uploaded_file_df)
    else:
        uploaded_file_df = pd.read_excel(file_path)
    
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    if(val == "All column present and validation check passed"):
        if (operation == 'Overwrite/Replace'):
            print(" Replacing the Old Data...")
            delete_query = f"""
                        DELETE FROM {selected_table}
                        WHERE Sector = ? AND Retailer = ?;
                        """
            conn.execute(delete_query, (sector,retailer))
            conn.commit()

            # Step 2: Append the new data to the table
            uploaded_file_df.to_sql(selected_table, conn, if_exists='append', index=False)
            #uploaded_file_df.to_sql(selected_table, conn, if_exists='replace', index=False)
            return { "Table has been replaced successfully." }
        elif (operation == 'Skip'):
            return { "Operation skipped, the table remains unchanged."}
        else:
            return {"else"}
    else:
        return {"Content validation failed"}
    
def view_database(body):
    retailer = body['retailer']
    sector = body['sector']
    selected_table = body['table']
    dict1 = {}
    sqlite_path = os.path.join(current_dir, "pepsico_master.db")
    
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    table_names = [t[0] for t in tables]
    print("table_names",table_names)
    if selected_table=="PPA_SideBySide":
        start_idx,end_idx=1,7
    elif selected_table=="Product_PPG":
        start_idx,end_idx=1,5
    elif selected_table=="Price_Effective_Dates":
        start_idx,end_idx=1,6
    sql_df = pd.read_sql_query(f"SELECT * FROM {selected_table} where Sector='{sector}'and Retailer='{retailer}'", conn)
    if not sql_df.empty:
        # Fetch the data from the table
        dict1["mapping_final_df"]=sql_df
    else:
        print(f"Sector: **{sector}** Retailer: **{retailer}** Mapping: **{selected_table}** is absent.")
    
    print(f"#### {selected_table} Mappings:")
    #print(dict1["mapping_final_df"].iloc[:,start_idx:end_idx])

    sliced_df = dict1["mapping_final_df"].iloc[:, start_idx:end_idx]
    
    # Convert to list of dictionaries
    result = sliced_df.to_dict(orient='records')
    
    # Return as JSON response
    return result
    #return dict1
    
def edit_database(body):
    edit_data = view_database(body)
    selected_table  =  body['table']
    
    if selected_table=="PPA_SideBySide":
        start_idx,end_idx=1,7
        disabled_columns = ['Importance', 'Silver_Layer_Column']
    elif selected_table=="Product_PPG":
        start_idx,end_idx=1,5
        disabled_columns=[]
    elif selected_table=="Price_Effective_Dates":
        start_idx,end_idx=1,5
        disabled_columns = ['PROD_ATRBT_1_VAL','SRP_COST_AMT']
    #print(type(edit_data))
    #print(edit_data)
    #edit_data.append(disabled_columns)
    
    return {
        "dataframe": edit_data,
        "disabled_columns": disabled_columns,
        "index" : [start_idx,end_idx]
        }


def save_database(body):
    
    final = edit_database(body)
    original_df = view_database(body)
    #print("ORO",original_df)
    save_dataframe = final
    #print(save_dataframe)
    modified_dataframe = save_dataframe['dataframe']
    
    original_df = modified_dataframe.copy()
    return original_df



async def column_processing_consolidator(df, file_name, app, final_consolidated_dict, acceptions):


    source_columns_to_map = df.columns.to_list()

    if file_name not in final_consolidated_dict:

        final_consolidated_dict[file_name] = []

    accepted_list_exploded = []
    # Checking whether the accepted list contains any column from the input file
    if not acceptions.empty:

        accepted_list = acceptions["accepted_match"].to_list()
        accepted_list_exploded=[]
        for i in [x.split(", ") for x in accepted_list]:
            accepted_list_exploded.extend(i)

        accepted_list_exploded = list(set(accepted_list_exploded))

        # Capturing the matches from the accepted list first

        common_list = list(set(source_columns_to_map).intersection(set(accepted_list_exploded)))

        result = []

        # Iterate over each row in the acceptions dataframe
        for _, row in acceptions.iterrows():
            # Split the accepted_match column into a set
            match_values = set(row["accepted_match"].split(", "))

            # Check for matches in the input list
            for value in common_list:
                if value in match_values:
                    result.append({
                        "Bronze Layer Column": row["Bronze Layer Column"],
                        "best_match": value,
                        "potential_match": ""
                    })

        # add the result from the accepted list for matched columns in the dictionary
        final_consolidated_dict[file_name].extend(result)

    # here we will process all the filtered columns in one go
    # Framework

    # Filtering the input columns based on the accepted list
    filtered_list = list(set(source_columns_to_map).difference(accepted_list_exploded))

    print(filtered_list)
    # Prepare the input for the framework
    # inputs = {"question": filtered_list, "accepted_list_version":selected_accepted_version,"rejected_list_version":selected_rejected_version}

    # inputs = {"question": filtered_list, "source_type": source_type, "source_desc": source_desc}
    inputs = {"question": filtered_list}
    # status_text = st.empty()
    #progress_placeholder = st.empty()
    # Process asynchronously
    async for output in app.astream(inputs, stream_mode="updates"):
        # Handle the output
        print("isnside_loop")
        for key, value in output.items():
            
            print(f"Output from node '{key}':")
            print("---")
            # print(value["messages"][-1].pretty_print())
            if key == "query_expander":

                progress_percentage = 33
                #progress_placeholder.progress(progress_percentage)
            if key == "create_and_retrieve":

                progress_percentage = 66
                #progress_placeholder.progress(progress_percentage)

            if key == "reranker":

                progress_percentage = 100
                #progress_placeholder.progress(progress_percentage)
                # status_text.write(f"Completion percentage {progress_percentage:.2f}%", unsafe_allow_html=True)
            print("between_loop")
            # Safely add results to final_consolidated_dict if keys exist
            if "ranked_records" in value:

                # final_consolidated_dict[file_name] = value["ranked_records"]
                final_consolidated_dict[file_name].extend(value["ranked_records"])
            print("outside_loop")
    print("Final",final_consolidated_dict)
    print("Sucesss")
    return final_consolidated_dict


async def multiple_file_processing_consolidator(df_list, app, acceptions):

    final_consolidated_dict = {}
    # Gather all tasks to process each column concurrently
    # final_consolidated_dict = await column_processing_consolidator(filtered_list, app)

    # await asyncio.gather(
    # *[column_processing_consolidator(df, file_name, app, final_consolidated_dict, acceptions, selected_accepted_version, selected_rejected_version) for df,file_name in df_list]
    # )
    print("there")
    #for df, file_name in df_list:
        #column_processing_consolidator(df, file_name, app, final_consolidated_dict, acceptions)
    results = await asyncio.gather(
    *[column_processing_consolidator(df, file_name, app, final_consolidated_dict, acceptions) for df,file_name in df_list]
    )
    for result in results:
        final_consolidated_dict.update(result)
    print("here")
    print("FINAL",final_consolidated_dict)
    
    for key,value in final_consolidated_dict.items():
        # st.info(f"For file **{key}**")
        df = pd.DataFrame(value)
    df[['accept_list', 'reject_list', 'your_match']] = None
    #print("DATA",df)
    
    return df
    #return final_consolidated_dict

async def generate_mapping_schema(body):
    file_name= body['file_name']
    save_directory = os.path.join(current_dir, "uploaded_files")
    file_path = os.path.join(save_directory, file_name)
    print(file_path)
    
    accepted_list_lance_path = os.path.join(current_dir,"lists","output","lance","acception_list.lance")

    accepted_lance_vec_ds = lance.dataset(accepted_list_lance_path)

    assert isinstance(accepted_lance_vec_ds, pa.dataset.Dataset)
    
    # Rejected Lists Version

    
    
    accepted_lance_df = accepted_lance_vec_ds.to_table().to_pandas()

    # cols[0].dataframe(accepted_lance_df)
    accepted_session_state = {}  # Simulating session state with a dictionary

    if "accepted_lance_df" not in accepted_session_state:
        accepted_session_state["accepted_lance_df"] = accepted_lance_df

    # selected_rejected_version = cols[1].selectbox("Select the rejected list version",[""]+rejected_lance_vec_ds.versions())
    rejected_list_lance_path = os.path.join(current_dir,"lists","output","lance","rejection_list.lance")

    rejected_lance_vec_ds = lance.dataset(rejected_list_lance_path)

    assert isinstance(rejected_lance_vec_ds, pa.dataset.Dataset)
    # if isinstance(selected_rejected_version,dict):
    # rejected_lance_vec_ds = lance.dataset(rejected_list_lance_path, version = selected_rejected_version["version"])
    rejected_lance_df = rejected_lance_vec_ds.to_table().to_pandas()
    #  cols[1].dataframe(rejected_lance_df)
    rejected_session_state = {}  # Simulating session state with a dictionary

    if "rejected_lance_df" not in rejected_session_state:
        rejected_session_state["rejected_lance_df"] = rejected_lance_df
    # accepted_lance_df = accepted_lance_vec_ds.to_table().to_pandas()
    # st.session_state.accepted_lance_df = accepted_lance_df

    # selected_accepted_version = cols[0].selectbox("Select the accepted list version",[""]+accepted_lance_vec_ds.versions())

    # if isinstance(selected_accepted_version,dict):
    # accepted_lance_vec_ds = lance.dataset(accepted_list_lance_path, version = selected_accepted_version["version"])
    


    if file_name.endswith(".csv"):
        uploaded_file_df = pd.read_csv(file_path)
        #print(uploaded_file_df)
    else:
        uploaded_file_df = pd.read_excel(file_path)
    print(uploaded_file_df)
    df_list = []
    df_list.append((uploaded_file_df, file_name.split(".")[0]))
    print("RUN")
    #final_consolidated_dict = asyncio.run(multiple_file_processing_consolidator(df_list, app, accepted_lance_df))
    '''
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If an event loop is already running, use `asyncio.create_task()`
        future = asyncio.ensure_future(multiple_file_processing_consolidator(df_list, app, accepted_lance_df))
        final_consolidated_dict = loop.run_until_complete(future)
    else:
        final_consolidated_dict = asyncio.run(multiple_file_processing_consolidator(df_list, app, accepted_lance_df))
    print("FINALLLL",final_consolidated_dict)
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        final_consolidated_dict = await multiple_file_processing_consolidator(df_list, app, accepted_lance_df)
    else:
        final_consolidated_dict = asyncio.run(multiple_file_processing_consolidator(df_list, app, accepted_lance_df))
    '''
    final_consolidated_dict = await multiple_file_processing_consolidator(df_list, app, accepted_lance_df)
    response = final_consolidated_dict.to_dict(orient="records")  # Assign DataFrame to JSON variable
    #response = JSONResponse(content=json_data)  # Assign JSON response to variable
    # Return the variable
    print("FINISHED PROCESSING:", response)
    print(f"Source columns mapped")
    return response
   
'''
def get_calculate(body):
    num1 = body['num1']
    num2 = body['num2']
    op = body['operation']
    
    if (op=='add'):
        result = num1+num2
    if (op=='sub'):
        result = num1-num2
    if (op=='mul'):
        result = num1*num2
    if (op=='div'):
        result = num1/num2
    return result
'''
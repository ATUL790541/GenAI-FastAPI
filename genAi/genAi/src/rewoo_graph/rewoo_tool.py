import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
import pandas as pd
import json
import base64
import ast
import numpy as np
load_dotenv()
from common.llm import get_llm, get_bigger_llm
import openpyxl

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, model_validator

@tool("header_identification_tool", return_direct=False)
def header_identification_tool(inputs) -> str:

    """ Used to handle headers in the given input dataframe path."""
    # st.write("saving")
    #df.to_csv("/home/ec2-user/text2sql/Pepsico_Mapping_Wrangling/intermediate_files/before_header_identification.csv",index=False)
    #print(inputs)
    input_list = inputs.rsplit("%",1)
    #print(f"input_list: {input_list}")
    df_path_sheet_info = input_list[0]
    #print(f"df_path_sheet_info: {df_path_sheet_info}")

    df_info_list = df_path_sheet_info.split("$")
    #print(f"df_info_list: {df_info_list}")

    path= df_info_list[0]
    sheet_name= df_info_list[1]

    print(sheet_name)

    # df= pd.read_excel(path, sheet_name=[sheet_name])

    # df = df[sheet_name]

    # Modification
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[sheet_name]

    # Create a dictionary to store merged cell information
    merged_cells = {}

    # Loop through merged cell ranges
    for merged_range in sheet.merged_cells.ranges:
        # Get the top-left cell's value
        start_cell = sheet.cell(merged_range.min_row, merged_range.min_col)
        value = start_cell.value

        # Extract coordinates of merged cells
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_cells[(row, col)] = value


    # Create a list of rows
    data = []
    for row in sheet.iter_rows(values_only=True):
        data.append(list(row))

    # Fill merged cells using the dictionary
    for (row, col), value in merged_cells.items():
        data[row - 1][col - 1] = value  # Adjusting for zero-based indexing

    # Convert to a DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])

    # # Giving unique columns to avoid errors when passing it's json format in the prompt
    # df.columns = [
    #     col if col is not None else f"Unnamed {idx+1}"
    #     for idx, col in enumerate(df.columns)
    # ]

    # Giving unique column names in case of merged cells in the first row
    unique_columns=[]
    seen = {}
    for col in df.columns:
        if col not in seen:
            unique_columns.append(col)
            seen[col]=1
        else:
            unique_columns.append(f"{col}_{seen[col]}")
            seen[col]+=1
    df = pd.DataFrame(data[1:], columns=unique_columns)

    header_identification_template= '''
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are an expert in CPG domain and you are highly capable in interpreting semi-structured tabular data. Your job is to extract a template after thorough analysis of the provided data in csv format. The first character in your response should be {{.

    {format_instructions}

    <|eot_id|><|start_header_id|>user<|end_header_id|>

    DataFrame:{dataframe}

    1. Header Row Number:
    <Instructions>
    Ignore the row as an header if it is a merged index,look for others rows to find the header.For example if the whole row contains only 1 meaningful value and other values are null or "Unnamed" then ignore that row.
    Identify the specific row number that can serve as the header row for the dataset.
    This header row should contain the column names that are most representative of the actual data.
    This header row should contain unique values since header values cannot be duplicate.

    </Instructions>

    2. Data Start Row Number:
    <Instructions Note>:
        Identify the row number immediately following the header row where the actual data entries begin.
        This row should be the first row containing valid data under the identified header.

    3. Data End Row Number:
    <Instructions Note>:
        Identify the row number wherever the valid data entries ends.
        This row should be the last row containing valid data entries under identified header.

    The output should be provided as step-by-step instructions in the following format, don't give extra information:
        {{
        "Header_Row_Number":"<Row number where the header is located>",
        "Data_Start_Row_Number": "<Row number where valid data starts>",
        "Data_End_Row_Number": "<Row number where valid data ends>"
    }}
    Respond only with valid JSON. Do not write an introduction or summary.
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    {{
    '''

    model = get_llm()

    # Define your desired data structure.
    class Header(BaseModel):
        Header_Row_Number: int = Field(description="Row number where the header is located")
        Data_Start_Row_Number: int = Field(description="Row number where valid data starts")
        Data_End_Row_Number: int = Field(description="Row number where valid data ends")

        # You can add custom validation logic easily with Pydantic.
        @model_validator(mode="before")
        @classmethod
        def header_row_less_than_data_start_row(cls, values: dict) -> dict:
            Header_Row_Number = values.get("Header_Row_Number")
            Data_Start_Row_Number = values.get("Data_Start_Row_Number")
            if Header_Row_Number and Data_Start_Row_Number and Header_Row_Number > Data_Start_Row_Number:
                raise ValueError("Invalid header row number")
            return values


    # Set up a parser + inject instructions into the prompt template.
    parser = PydanticOutputParser(pydantic_object=Header)

    prompt = PromptTemplate(
        template=header_identification_template,
        input_variables=["dataframe"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # And a query intended to prompt a language model to populate the data structure.
    prompt_and_model = prompt | model
    output = prompt_and_model.invoke({"dataframe": df.iloc[:15,:].to_json()})
    result = parser.invoke(output)

    steps_dict = result.dict()

    # JSON Response Schema
    # response_schemas = [
    #     ResponseSchema(name="Header_Row_Number", description="Row number where the header is located"),
    #     ResponseSchema(name="Data_Start_Row_Number", description="Row number where valid data starts"),
    #     ResponseSchema(name="Data_End_Row_Number", description="Row number where valid data ends")
    # ]
    # output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

    # format_instructions = output_parser.get_format_instructions()

    # prompt = PromptTemplate(
    #     template=header_identification_template,
    #     input_variables=["dataframe"],
    #     partial_variables={"format_instructions": format_instructions},
    # )

    # model = get_llm()
    # chain = prompt | model | output_parser
    # steps_dict = chain.invoke({"dataframe": df.iloc[:15,:].to_json()})

    # header_identification_prompt = header_identification_prompt.format(dataframe=df.iloc[:15,:].to_json())
    # steps = get_llm().predict(header_identification_prompt)
    # st.write(steps)
    # steps_dict = json.loads(steps)
    # Assuming steps_dict is your dictionary
    header_row = int(steps_dict["Header_Row_Number"])
    data_start_row = int(steps_dict["Data_Start_Row_Number"])
    #data_end_row = int(steps_dict["Data_End_Row_Number"])

    # Restoring the original column names after giving the prompt with unique column names (using .to_json())

    base_name_columns = []
    for col in df.columns:
        print(col)
        if col is not None:
            base_name_columns.append(col.rsplit("_")[0] if '_' in col and col.rsplit("_")[-1].isdigit() else col)
        else:
            base_name_columns.append(col)
    new_df = pd.DataFrame(data[1:], columns=base_name_columns)

    # if (int(input_list[1].strip())+1) != len(df):
    data_end_row = len(new_df)

    # Instead of just directly assigning the header_row as the columns, check whether it is completely blank
    # If blank then assign the first non-null row starting at the identified header row number in reverse.
    if all(col is None for col in new_df.iloc[header_row].to_list()):
        if header_row > 0:
            for i in reversed(range(header_row)):
                if not all(col is None for col in new_df.iloc[i].to_list()):
                    new_df.columns = new_df.iloc[i]
                    break
                else:
                    new_df.columns = new_df.iloc[header_row]
        else:
            new_df.columns = new_df.iloc[header_row]
    else:
        new_df.columns = new_df.iloc[header_row]  # Set header row as column names

    # Adjust df for header and data rows
    # new_df.columns = new_df.iloc[header_row]  # Set header row as column names
    new_df = new_df[data_start_row:data_end_row].reset_index(drop=True)
    new_df.index = new_df.index + 1
    # df=df.loc[:, df.columns.notna()]
    new_df = new_df.loc[:, (new_df.notna().any() | new_df.columns.notna())] # Retain columns with any non-NaN values and also those columns which has some name but contains no values

    # df["Sheet_name"] = sheet_name
    new_df=new_df.dropna(how='all')

    # New condition added
    # To check whether the existing header columns are completely blank or not
    # kept on hold
    # if all(col is None for col in new_df.columns):
    #     new_df.columns = new_df.iloc[0]
    #     new_df = new_df[1:].reset_index(drop=True)
    header_file_path = path.replace("uploaded_files","modified_files").replace(".xlsx",f"{sheet_name}_header.csv").replace(".xlsm",f"{sheet_name}_header.csv")
    new_df.to_csv(header_file_path, index=False)
    return header_file_path

@tool("multi_table_handling_tool", return_direct=False)
def multi_table_handling_tool(df_path: str) -> str:

    """ Used to handle multiple tables in the given input dataframe path."""
    try:
        df= pd.read_csv(df_path)

    except:

        input_list = df_path.rsplit("%",1)
        #print(f"input_list: {input_list}")
        df_path_sheet_info = input_list[0]
        #print(f"df_path_sheet_info: {df_path_sheet_info}")

        df_info_list = df_path_sheet_info.split("$")
        #print(f"df_info_list: {df_info_list}")

        path= df_info_list[0]
        sheet_name= df_info_list[1]

        print(sheet_name)

        df= pd.read_excel(path, sheet_name=[sheet_name])

        df = df[sheet_name]

        header_identification_template= '''
        <|begin_of_text|><|start_header_id|>system<|end_header_id|>

        You are an expert in CPG domain and you are highly capable in interpreting semi-structured tabular data. Your job is to extract a template after thorough analysis of the provided data in csv format. The first character in your response should be {{.

        {format_instructions}

        <|eot_id|><|start_header_id|>user<|end_header_id|>

        DataFrame:{dataframe}

        1. Header Row Number:
        <Instructions>
        Ignore the row as an header if it is a merged index,look for others rows to find the header.For example if the whole row contains only 1 meaningful value and other values are null or "Unnamed" then ignore that row.
        Identify the specific row number that can serve as the header row for the dataset.
        This header row should contain the column names that are most representative of the actual data.
        This header row should contain unique values since header values cannot be duplicate.

        </Instructions>

        2. Data Start Row Number:
        <Instructions Note>:
            Identify the row number immediately following the header row where the actual data entries begin.
            This row should be the first row containing valid data under the identified header.

        3. Data End Row Number:
        <Instructions Note>:
            Identify the row number wherever the valid data entries ends.
            This row should be the last row containing valid data entries under identified header.

        The output should be provided as step-by-step instructions in the following format, don't give extra information:
            {{
            "Header_Row_Number":"<Row number where the header is located>",
            "Data_Start_Row_Number": "<Row number where valid data starts>",
            "Data_End_Row_Number": "<Row number where valid data ends>"
        }}
        Respond only with valid JSON. Do not write an introduction or summary.
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>
        {{
        '''

        model = get_llm()

        # Define your desired data structure.
        class Header(BaseModel):
            Header_Row_Number: int = Field(description="Row number where the header is located")
            Data_Start_Row_Number: int = Field(description="Row number where valid data starts")
            Data_End_Row_Number: int = Field(description="Row number where valid data ends")

            # You can add custom validation logic easily with Pydantic.
            @model_validator(mode="before")
            @classmethod
            def header_row_less_than_data_start_row(cls, values: dict) -> dict:
                Header_Row_Number = values.get("Header_Row_Number")
                Data_Start_Row_Number = values.get("Data_Start_Row_Number")
                if Header_Row_Number and Data_Start_Row_Number and Header_Row_Number > Data_Start_Row_Number:
                    raise ValueError("Invalid header row number")
                return values


        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=Header)

        prompt = PromptTemplate(
            template=header_identification_template,
            input_variables=["dataframe"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        # And a query intended to prompt a language model to populate the data structure.
        prompt_and_model = prompt | model
        output = prompt_and_model.invoke({"dataframe": df.iloc[:15,:].to_json()})
        # try:
        result = parser.invoke(output)
        # except ValueError:
        #     output = prompt_and_model.invoke({"dataframe": df.iloc[:15,:].to_json()})
        #     result = parser.invoke(output)

        steps_dict = result.dict()

        # JSON Response Schema
        # response_schemas = [
        #     ResponseSchema(name="Header_Row_Number", description="Row number where the header is located"),
        #     ResponseSchema(name="Data_Start_Row_Number", description="Row number where valid data starts"),
        #     ResponseSchema(name="Data_End_Row_Number", description="Row number where valid data ends")
        # ]
        # output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

        # format_instructions = output_parser.get_format_instructions()

        # prompt = PromptTemplate(
        #     template=header_identification_template,
        #     input_variables=["dataframe"],
        #     partial_variables={"format_instructions": format_instructions},
        # )

        # model = get_llm()
        # chain = prompt | model | output_parser
        # steps_dict = chain.invoke({"dataframe": df.iloc[:15,:].to_json()})

        # header_identification_prompt = header_identification_prompt.format(dataframe=df.iloc[:15,:].to_json())
        # steps = get_llm().predict(header_identification_prompt)
        # st.write(steps)
        # steps_dict = json.loads(steps)
        # Assuming steps_dict is your dictionary
        header_row = int(steps_dict["Header_Row_Number"])
        data_start_row = int(steps_dict["Data_Start_Row_Number"])
        #data_end_row = int(steps_dict["Data_End_Row_Number"])

        # if (int(input_list[1].strip())+1) != len(df):
        data_end_row = len(df)

        # Adjust df for header and data rows
        df.columns = df.iloc[header_row]  # Set header row as column names
        df = df[data_start_row:data_end_row].reset_index(drop=True)
        # df.index = df.index + 1
        df=df.loc[:, df.columns.notna()]
        df.index += 1

    # df.index += 1


    #df.to_csv("/home/ec2-user/text2sql/Pepsico_Mapping_Wrangling/intermediate_files/before_multi_tables.csv",index=False)
    multi_table_template='''
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are an expert in analyzing and have an immense knowledge of identifying the multiple tables present in the given dataFrame in the json format which is related to the promotion and financial data. The DataFrame you are provided with contains multiple tables with almost similar schema but they are repetitive. The first character in your response should be {{.

    {format_instructions}

    <|eot_id|><|start_header_id|>user<|end_header_id|>

    Your task is to identify these repetitive tables and provide structured information on the following aspects:
        1)Identify the header row number where the schema (column names) starts.
            Identify the specific row number(starting from 0) that can serve as the header row for the dataset.
            This row would be ideally be just after a blank row except for the very first header row. THat means each unique table would be separated by a blank divider and your responsibility is to identify the row number following the blank divider row.

        2)Identify the row number where valid data starts for each table.
            Identify the row number for each sub table immediately following the header row where the actual data entries begin.
            This row should be the first row containing valid data under the identified header.

        3)Identify the row number where valid data ends for each table.
            For each table:
                row numbers will be the first value in each data row.
                Identify the row number of the first completely blank row, which signifies the end of the data for that table.
                This row should have no valid data entries in any column.

        4)Identify the category of each table:
            Examine each header to determine if it contains categorical or metadata information that differentiates it from the other headers.
            Identify any patterns or anomalies in the header content that indicate a category or metadata is present.
            Return the detected category or metadata for each table.


        Provide the output as step-by-step instructions in the following JSON format:
            {{
                "Tables":
                {{
                    "Table 1": {{
                        "Header_Row_Number": "<Row number where the header is located>",
                        "Data_Start_Row_Number": "<Row number where valid data starts>",
                        "Data_End_Row_Number": "<Row number of blank divider>",
                        "Category": "<unique Category for Table 1>"
                    }},
                    "Table 2": {{
                        "Header_Row_Number": "<Row number where the header is located>",
                        "Data_Start_Row_Number": "<Row number where valid data starts>",
                        "Data_End_Row_Number": "<Row number of blank divider>",
                        "Category": "<unique Category for Table 2>"
                    }}
                }}
            }}

        Data:
        {dataframe}
        Critical Notes:
        (1) Only create tables with distinct category.
        (2) Do not split one table with same category into multiple tables. For example if Category "A" belongs to "Table 1" then Category "A" **should not** belong to "Table 2". Table to Category should be one-to-one only.
        (3) Do not skip any rows. Make sure to assign each and every row to a certain table.
        (4) Do not provide python code or any solution steps.
        Respond only with valid JSON .Do not write an introduction or summary or an explanation.
        (5) Do not provide any duplicate keys.
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>
        '''

    # model = get_llm()

    model = get_bigger_llm()
    # Define your desired data structure.
    class MultiTableItem(BaseModel):
        Header_Row_Number: int = Field(description="Row number where the header is located")
        Data_Start_Row_Number: int = Field(description="Row number where valid data starts")
        Data_End_Row_Number: int = Field(description="Row number where valid data ends")
        Category: str =  Field(description="Category")
        # You can add custom validation logic easily with Pydantic.
        @model_validator(mode="before")
        @classmethod
        def header_row_less_than_data_start_row(cls, values: dict) -> dict:
            Header_Row_Number = values.get("Header_Row_Number")
            Data_Start_Row_Number = values.get("Data_Start_Row_Number")
            Data_End_Row_Number = values.get("Data_End_Row_Number")
            if Header_Row_Number and Data_Start_Row_Number and Data_End_Row_Number and (Header_Row_Number >= Data_Start_Row_Number or Data_Start_Row_Number > Data_End_Row_Number):
                raise ValueError("Invalid row numbers")
            return values

    from typing import Dict
    class MultiTable(BaseModel):
        Tables: Dict[str,MultiTableItem]

        # @model_validator(mode="before")
        # @classmethod
        # def header_row_less_than_data_start_row(cls, values: dict) -> dict:
        #     table_1_values = values.get("Table 1")
        #     table_2_values = values.get("Table 2")
        #     table_3_values = values.get("Table 3")
        #     table_4_values = values.get("Table 4")


        #     Data_Start_Row_Number = table_1_values.get("Data_Start_Row_Number")
        #     Data_End_Row_Number = values.get("Data_End_Row_Number")
        #     if Header_Row_Number and Data_Start_Row_Number and Data_End_Row_Number and (Header_Row_Number >= Data_Start_Row_Number or Data_Start_Row_Number > Data_End_Row_Number):
        #         raise ValueError("Invalid row numbers")
        #     return values

    # Set up a parser + inject instructions into the prompt template.
    parser = PydanticOutputParser(pydantic_object=MultiTable)

    # Add the format instructions based on the Schema provided to the parser in template and create the final prompt
    prompt = PromptTemplate(
        template=multi_table_template,
        input_variables=["dataframe"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create chain
    prompt_and_model = prompt | model

    # Execute the chain with the csv data
    output = prompt_and_model.invoke({"dataframe": df.to_csv()})
    # print(output.content)

    # Pass the output to the parser to get the structured output
    result = parser.invoke(output)

    # Convert the response to a dict
    json_data = result.dict()["Tables"]

    result_df=pd.DataFrame()
    last_table = next(reversed(json_data.keys()))
    # df.index+=1
    for table_name, table_info in json_data.items():
        header_row = int(table_info["Header_Row_Number"])
        data_start_row = int(table_info["Data_Start_Row_Number"])
        data_end_row = int(table_info["Data_End_Row_Number"])
        category = table_info["Category"]


        table_df = df.iloc[data_start_row-1:data_end_row-1].copy()# Copy to avoid SettingWithCopyWarning

        if table_df.empty or last_table == table_name:
            table_df = df.iloc[data_start_row-1:data_end_row]

        table_df['Category'] = category

        if not table_df.empty:
            last_col = table_df.columns[-1]
            table_df = table_df[[last_col] + [col for col in table_df.columns if col != last_col]]
            # if table_df.iloc[-1:,:].values[-1][-1] == table_df.columns[-1]:
            #     table_df = table_df.iloc[:-1]
        # display(table_df)
        result_df = pd.concat([result_df, table_df], ignore_index=True)

        result_df = result_df.dropna(thresh=2)
    #result_df

    multi_table_file_path = path.replace("uploaded_files","modified_files").replace(".csv","_multi_table.csv").replace(".xlsx",f"{sheet_name}_multi_table.csv")
    result_df.to_csv(multi_table_file_path, index=False)
    return multi_table_file_path
    #return result_df.to_dict(orient="records")


@tool("anchors_handling_tool", return_direct=False)
def anchors_handling_tool(df_path: str) -> str:

    """ Used to handle anchors in the given input dataframe path."""

    df= pd.read_csv(df_path)
    df.index += 1

    #df.to_csv("/home/ec2-user/Pepsico_Hackathon/Pepsico_Main_Hackathon/Pepsico_Mapping_Wrangling/intermediate_files/before_anchor.csv",index=False)
    # st.write("Anchors Handling Input")
    #Hard Coding
    df = df.replace([''], np.nan).dropna(how='all').reset_index(drop=True)
    # st.dataframe(df,use_container_width=True)
    condition = (df.iloc[:, 1:].isna().all(axis=1)) & df.iloc[:, 0].notna()
    row_numbers = [{'Row': idx, 'Anchor': df.iloc[idx, 0]} for idx in df[condition].index]
    # st.write("Anchors",row_numbers)
    #Hard Coding

    anchor_template='''
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are an expert in CPG domain and you are highly capable in interpreting semi-structured tabular data of PPA processing files. Your job is to extract a template after thorough analysis of the provided data in csv format. The first character in your response should be {{.

    {format_instructions}

    <|eot_id|><|start_header_id|>user<|end_header_id|>

    Data={dataframe}

    You are also provided with a list of dictionaries containg the Row value and the Anchor Tag values.

    Anchors row and values={row_numbers}
    Start Row:
        Identify the row number immediately following the anchor row where the actual data entries begin.
        This row should be the first row containing valid data under the identified anchor.

    End Row:
        Identify the row number where valid data ends for each Anchor. The end row should be the row immediately above the next anchor row.
        If no additional Anchor row appears in the coming data, consider the last row of the data as the end row for this anchor.
        Anchors information is being provided above.

    Please provide the output in the below format for Anchor(Don't give extra information):
    {{
        "Anchors":
        {{
            "Anchor1":{{
                "Start_Row":"<valid data starting row number for the Anchor 1>",
                "End_Row":<Valid data ending row number for the Anchor 1>"
            }},
            "Anchor2":{{
                "Start_Row":"<valid data starting row number for the Anchor 2>",
                "End_Row":<Valid data ending row number for the Anchor 2>"
            }}
        }}
    }}

    Respond only with valid JSON. Do not write an introduction or summary.
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    {{
    '''

    model = get_llm()
    # Define your desired data structure.
    class AnchorItem(BaseModel):
        Start_Row: int = Field(description="valid data starting row number for the Anchor")
        End_Row: int = Field(description="Valid data ending row number for the Anchor")
        # You can add custom validation logic easily with Pydantic.
        @model_validator(mode="before")
        @classmethod
        def header_row_less_than_data_start_row(cls, values: dict) -> dict:
            Start_Row = values.get("Start_Row")
            End_Row = values.get("End_Row")
            if Start_Row and End_Row and Start_Row > End_Row:
                raise ValueError("Invalid header row number")
            return values

    from typing import Dict
    class Anchor(BaseModel):
        Anchors: Dict[str,AnchorItem]

    # Set up a parser + inject instructions into the prompt template.
    parser = PydanticOutputParser(pydantic_object=Anchor)

    # Add the format instructions based on the Schema provided to the parser in template and create the final prompt
    prompt = PromptTemplate(
        template=anchor_template,
        input_variables=["dataframe", "row_numbers"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create chain
    prompt_and_model = prompt | model

    # Execute the chain with the csv data
    output = prompt_and_model.invoke({"dataframe": df.to_csv(), "row_numbers": row_numbers})
    # print(output.content)

    # Pass the output to the parser to get the structured output
    result = parser.invoke(output)

    # Convert the response to a dict
    json_data = result.dict()["Anchors"]
    result_df=pd.DataFrame()
    df['Category'] = None
    df = df.drop(index=[row['Row'] for row in row_numbers])
    # Reset the index
    df.reset_index(drop=True, inplace=True)
    # Iterate over the JSON object and store the values in variables
    for anchor_name, anchor_info in json_data.items():
        data_start_row = int(anchor_info["Start_Row"])
        data_end_row = int(anchor_info["End_Row"])
        # st.write(f"- Anchor Name: {anchor_name}, Data Start Row: {data_start_row}, Data End Row: {data_end_row}")
        df.loc[data_start_row:data_end_row+1, 'Category'] = anchor_name
        # Move the 'anchor' column to the start
        df = df[['Category'] + [col for col in df.columns if col != 'Category']]

    anchor_file_path = df_path.replace("uploaded_files","modified_files").replace(".csv","_anchor.csv")
    df.to_csv(anchor_file_path, index=False)
    return anchor_file_path
    #return df.to_dict(orient="records")

@tool("multi_indices_handling_tool", return_direct=False)
def multi_indices_handling(inputs) -> str:
    """ Used to handle multiple horizontal indices in the given input dataframe path."""

    print(inputs)
    input_list = inputs.rsplit("%",1)
    print(f"input_list: {input_list}")
    df_path_sheet_info = input_list[0]
    print(f"df_path_sheet_info: {df_path_sheet_info}")

    df_info_list = df_path_sheet_info.split("$")
    print(f"df_info_list: {df_info_list}")

    path= df_info_list[0]
    sheet_name= df_info_list[1]

    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[sheet_name]
    data = pd.DataFrame(sheet.values)
    for merged_range in sheet.merged_cells.ranges:
        # Get the top-left cell of the merged range
        top_left_cell = merged_range.start_cell
        merged_value = sheet[top_left_cell.coordinate].value

        # Fill the merged value across the entire merged range
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                data.iat[row - 1, col - 1] = merged_value

    df = data[:10].copy()

    multi_table_template='''
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are an expert in CPG domain and you are highly capable in interpreting semi-structured tabular data of PPA processing files. The dataframe you are provided with contains the data in the form of segments horizontally with repetitive schema under these segments. The first character in your response should be {{.

    {format_instructions}

    <|eot_id|><|start_header_id|>user<|end_header_id|>
    Your task is to identify these repetitive tables and provide structured information on the following aspects:

    1)Identify the header row number where the schema (column names) starts.
        Identify the specific row number(starting from 0) that can serve as the header row for the segment.
        This row should contain the column names that are most representative of the actual data.
        This row may contain the duplicate values as the schema is being repeated.So please add the numbering to the duplicate column names to differentiate.
        The header should be the  valid column names used to represent the actual data.
        The header will not contain any numerical values because column names cannot be **numeric**.

    2)Identify the Header Row Values.
        Identify the **Non repetitive Header Row** values from the above identified **header row number** in the given data.
        Headers values should be unique. Don't add the repetitive set of values in the output. Don't give any modified header names, just ignore the repititive header columns.

    3)Identify all the different table names present in the data:

        1) Identify crucial column names that needs to be identified as a separate table name that could be in any row till the identified header row. Use your own CPG domain knowldege to assess the column values and decide whether it deserves a separate table or not. You need to investigate till the **Header Row** (as described in Attribute 1) at the specified row_index.


    Provide the output as step-by-step instructions in the following format,Don't give extra information:
    {{
        "Tables": [
            {{
                "Table_Name": "<Table Name>"
            }},
            {{
                "Table_Name": "<Table Name>"
            }}
        ],
        "Header_Row_Number": "<Row number where the header is located>",
        "Headers":"<Header Row Values>"
    }}

    Data:
    {dataframe}
    Notes:
    Ensure that you handle cases where the schema repeats after an empty column.
    The output should be concise, clear, and in the specified format.Don't give extra information
    Respond only with valid JSON. Do not write an introduction or summary.
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    '''

    # model = get_llm()
    model = get_bigger_llm()
    # Define your desired data structure.
    class MultiTableItem(BaseModel):
        Table_Name: str = Field(description="Table Name")
        # End_Row: int = Field(description="Valid data ending row number for the Anchor")
        # You can add custom validation logic easily with Pydantic.
        # @model_validator(mode="before")
        # @classmethod
        # def header_row_less_than_data_start_row(cls, values: dict) -> dict:
        #     Start_Row = values.get("Start_Row")
        #     End_Row = values.get("End_Row")
        #     if Start_Row and End_Row and Start_Row > End_Row:
        #         raise ValueError("Invalid header row number")
        #     return values

    from typing import List
    class MultiTable(BaseModel):
        Tables: List[MultiTableItem]
        Header_Row_Number: int = Field(description="Row number where the header is located")
        Headers: str = Field(description="Header Row Values")

    # Set up a parser + inject instructions into the prompt template.
    parser = PydanticOutputParser(pydantic_object=MultiTable)

    # Add the format instructions based on the Schema provided to the parser in template and create the final prompt
    prompt = PromptTemplate(
        template=multi_table_template,
        input_variables=["dataframe"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create chain
    prompt_and_model = prompt | model

    # Execute the chain with the csv data
    output = prompt_and_model.invoke({"dataframe": df.to_csv()})
    # print(output.content)

    # Pass the output to the parser to get the structured output
    result = parser.invoke(output)

    # Convert the response to a dict
    dict = result.dict()



    # steps = get_llm().predict(multi_table_prompt.format(dataframe=df.to_csv(index=True)))
    # #st.write(" multi table prompt steps",steps)

    # dict = json.loads(steps)
    # Extract all Table_Name values into a list
    table_names = [table['Table_Name'] for table in dict['Tables']]
    print(table_names)

    # column_indexes = pd.DataFrame([list(range(len(data.columns)))], columns=data.columns)
    # data_with_indexes = pd.concat([column_indexes, data], ignore_index=True)
    df=data[:10].copy()
    row_index = int(dict["Header_Row_Number"])
    above_header = df.iloc[:row_index+1]


    category_identifier_json_template='''
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are an expert in CPG domain and you are highly capable in interpreting semi-structured tabular data of PPA processing files. The first character in your response should be {{.

    {format_instructions}

    <|eot_id|><|start_header_id|>user<|end_header_id|>

    Your task is to identify the column numbers in which the table names are present and provide structured information on the following aspects:

    Note: Column indexing and row indexing starts from '0'.
        - The Table names are spread across the multiple columns, so identify the column numbers for each table name.
        list of Table names are given below:

        Table Names:{table_names}

        1)Identify the column numbers of Table name:
            Identify the column numbers in which the given table names are present. Include only column numbers in which the given name is present.
            The end column number for each table will be until you encounter a column with *all* the null values or else until you encounter another table name.
            So please Don't involve the empty column numbers in this range.

        Provide the output as step-by-step instructions in the following format,Don't give extra information:

        {{
            "Tables":
            {{
                "Table 1": {{
                    "Table_Name": "<Table Name>",
                    "Columns_Range": "<start_index - end_index>"
                }},
                "Table 2": {{
                    "Table_Name": "<Table Name>",
                    "Columns_Range": "<start_index - end_index>"
                }}
            }}
        }}
        The data in JSON format:

        {dataframe}

        Note: Please give the output in the given format only, no extra information.
        Respond only with valid JSON. Do not write an introduction or summary.
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>
        {{'''

    model = get_llm()
    # Define your desired data structure.
    class CategoryIdentifierItem(BaseModel):
        Table_Name: str = Field(description="Table Name")
        Columns_Range: str = Field(description="start_index and end_index expressed as <start_index - end_index> that means start index and end index should be separated by '-'.")
        # You can add custom validation logic easily with Pydantic.
        # @model_validator(mode="before")
        # @classmethod
        # def header_row_less_than_data_start_row(cls, values: dict) -> dict:
        #     Start_Row = values.get("Start_Row")
        #     End_Row = values.get("End_Row")
        #     if Start_Row and End_Row and Start_Row > End_Row:
        #         raise ValueError("Invalid header row number")
        #     return values

    from typing import Dict
    class CategoryIdentifier(BaseModel):
        Tables: Dict[str,CategoryIdentifierItem]

    # Set up a parser + inject instructions into the prompt template.
    parser = PydanticOutputParser(pydantic_object=CategoryIdentifier)

    # Add the format instructions based on the Schema provided to the parser in template and create the final prompt
    prompt = PromptTemplate(
        template=category_identifier_json_template,
        input_variables=["dataframe", "table_names"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create chain
    prompt_and_model = prompt | model

    # Execute the chain with the csv data
    output = prompt_and_model.invoke({"dataframe": above_header.to_json(orient='records'), "table_names": table_names})
    # print(output.content)

    # Pass the output to the parser to get the structured output
    result = parser.invoke(output)

    # Convert the response to a dict
    table_dict = result.dict()["Tables"]



    # steps1 = get_llm().predict(category_identifier_json_prompt.format(dataframe=above_header.to_json(orient='records'), table_names=table_names))
    # #print(category_identifier_json_prompt)
    # #st.write(steps1)
    # #0-0,1-3,5-9,11-15,17-21,23-27
    # #1-1,2-4,6-10,12-16,18-22,24-28

    # dict = json.loads(steps)
    # table_dict=json.loads(steps1)
    # # Extract all Table_Name values into a list
    header_row=int(dict['Header_Row_Number'])
    for table, details in table_dict.items():
        # Extract the column range
        start_col, end_col = map(int, details['Columns_Range'].split('-'))

        # Extract the headers from the DataFrame
        headers = df.iloc[header_row, start_col:end_col+1].tolist()

        # Add the header information to the JSON
        table_dict[table]['Headers'] = headers
    final_dict=json.dumps(table_dict, indent=2)
    # Output the updated JSON with headers
    # st.write("final_dict",final_dict)

    # Input dictionary
    input_dict =json.loads(final_dict)
    # Group tables by "Columns_Range"
    columns_range_dict = {}
    for table, info in input_dict.items():
        columns_range = info["Columns_Range"]
        if columns_range in columns_range_dict:
            # Append table name and headers to existing entry
            columns_range_dict[columns_range]["Table_Names"].append(info["Table_Name"])
            columns_range_dict[columns_range]["Headers"].extend(info["Headers"])
        else:
            # Create a new entry for the column range
            columns_range_dict[columns_range] = {
                "Table_Names": [info["Table_Name"]],
                "Headers": info["Headers"].copy()  # Copy headers to avoid modification issues
            }

    # Create the output dictionary
    output_dict = {}
    counter = 1
    for columns_range, info in columns_range_dict.items():
        # Combine the table names and use the unique headers
        combined_table_name = "_".join(info["Table_Names"])
        unique_headers = list(dict.fromkeys(info["Headers"]))  # Remove duplicate headers

        output_dict[f"Table {counter}"] = {
            "Table_Name": combined_table_name,
            "Columns_Range": columns_range,
            "Headers": unique_headers
        }

        counter += 1

    # Print the output dictionary
    # st.write("output_dict",output_dict)
    def replace_none_with_unnamed(lst):
        unnamed_count = 1  # Counter for unnamed values
        for i in range(len(lst)):
            if lst[i] is None:
                lst[i] = f'Unnamed_{unnamed_count}'  # Replace None with 'Unnamed x'
                unnamed_count += 1  # Increment the counter
        return lst

    def rename_none_columns(df):
        # Create a list to hold new column names
        new_columns = []

        for i, col in enumerate(df.columns):
            if col is None:
                new_columns.append(f'Unnamed_{i + 1}')  # Rename to Unnamed 1, Unnamed 2, etc.
            else:
                new_columns.append(col)

        # Assign new column names back to the DataFrame
        df.columns = new_columns

    Headers=dict["Headers"]
    Headers_list = [item.strip() for item in Headers.split(',') if item.strip()]
    original_df=data
    new_header = original_df.iloc[row_index]
    original_df = original_df[row_index + 1:]  # Keep rows below the header row
    original_df.columns = new_header  # Set the new header
    original_df.reset_index(drop=True, inplace=True)
    original_df.columns = original_df.columns.str.strip().str.replace("\n", "")
    rename_none_columns(original_df)
    #display(original_df)
    for table, details in output_dict.items():
        table_name = details["Table_Name"]
        columns_to_include = details['Headers']
        columns_range = details['Columns_Range']
        range_str = details['Columns_Range'].replace(' ', '')
        # Split the range and map to integers
        start_idx, end_idx = map(int, range_str.split('-'))
        current_idx = start_idx
        for col in columns_to_include:
            if col is not None:
                col = col.strip().replace("\n", "")
            if col not in Headers_list:
                Headers_list.insert(current_idx, col)
            current_idx += 1
    #print(output_dict)
    Headers_list = replace_none_with_unnamed(Headers_list)
    #print("##Headers##\n",Headers_list)
    final_df = pd.DataFrame(columns=Headers_list)
    #display(final_df)
    for table, details in output_dict.items():
        table_name = details["Table_Name"]
        #print('table_name',table_name)
        # Create a new DataFrame with the specified headers
        new_df = pd.DataFrame(columns=Headers_list)
        columns_to_include = details['Headers']
        columns_to_include = [None if col == '' else col for col in columns_to_include]
        columns_range = details['Columns_Range']
        range_str = details['Columns_Range'].replace(' ', '')
        # Split the range and map to integers
        start_idx, end_idx = map(int, range_str.split('-'))

        # Strip spaces from each item in the list, ignoring None values
        columns_stripped = [col.strip().replace("\n", "") if col is not None else None for col in columns_to_include]
        #print("columns:", columns_stripped, "start:", start_idx, 'end:', end_idx)

        # Extract the range of columns from original_df
        range_df = original_df.iloc[:, start_idx:end_idx+1]
        #display(range_df)

        # Get the columns that are in new_df but not in columns_to_include
        missing_columns = [col for col in new_df.columns if col not in columns_stripped]
        #print("missing columns:", missing_columns)

        # Check columns only in the next two indexes after end_idx
        next_two_columns_df = original_df.iloc[:, end_idx+1:end_idx+3]
        next_two_columns_df = next_two_columns_df.dropna(axis=1, how='all')
        next_two_columns = next_two_columns_df.columns.tolist()
        #print("next_two_columns_df")
        #display(next_two_columns_df)
        # Determine which missing columns are present in the next two indexes
        missing_columns_present = [col for col in missing_columns if col in next_two_columns]
        missing_columns_absent = [col for col in missing_columns if col not in next_two_columns]
        # print("missing_columns_present",missing_columns_present)
        # print("missing_columns_absent",missing_columns_absent)
        # Create DataFrame for columns present in the next two indexes
        if missing_columns_present:
            # Extract data for the columns present in the next two indexes from next_two_columns_df
            data_present = next_two_columns_df[missing_columns_present]
            data_present = data_present.loc[:, ~data_present.columns.duplicated()]
        else:
            data_present = pd.DataFrame()  # Empty DataFrame if no columns are present in the next two indexes
        # print("data_present")
        # display(data_present)
        # Handle columns not present in the next two indexes
        if missing_columns_absent:
            # Extract data for these columns, but only the first occurrence
            data_absent = original_df[missing_columns_absent]
            data_absent = data_absent.loc[:, ~data_absent.columns.duplicated()]
        else:
            data_absent = pd.DataFrame()  # Empty DataFrame if no columns are absent
        #print("data_absent")
        #display(data_absent)
        # # Concatenate range_df, data_present, and data_absent

        result_df = pd.concat([range_df, data_present, data_absent], axis=1)

        # Ensure no duplicate columns in result_df
        result_df = result_df.loc[:, ~result_df.columns.duplicated()]
        result_df = result_df.replace('', np.nan).dropna(how='all')
        result_df = result_df[Headers_list]
        # subset_columns = result_df.columns.difference([None]).tolist()

        # # Merge based on the existing columns without None
        # is_subset = final_df.merge(result_df[subset_columns], on=subset_columns, how='left', indicator=True).shape[0] == result_df.shape[0]
        # print("result_df")
        # display(result_df)
        # print("final_df")
        # display(final_df)
        is_subset = result_df.isin(final_df.to_dict(orient='list')).all().all()
        #is_subset = final_df.merge(result_df).shape[0] == result_df.shape[0]
        print("###############")
        print(is_subset)
        print("###############")

        if is_subset:
            common_columns = final_df.columns.intersection(result_df.columns)
            # Merge to find matching rows
            merged_df = final_df.merge(result_df, on=list(common_columns), how='left', indicator=True)
            #display(merged_df)
            # Update the 'subset' column in final_df
            final_df['Category'] = merged_df['_merge'].replace({'both': table_name, 'left_only': '', 'right_only': ''})
            print("""#####subset case##########""")
            #display(final_df)
        else:
            result_df['Category'] = table_name
            final_df = final_df.reset_index(drop=True)
            result_df = result_df.reset_index(drop=True)
            final_df = pd.concat([final_df, result_df], ignore_index=True)

    if "Category" in final_df.columns:
        columns_order = ["Category"] + [col for col in final_df.columns if col != "Category"]
        final_df = final_df[columns_order]
    print("final_df")
    #display(final_df)
    #st.write(final_df)
    final_combined_df=final_df.copy()
    new_df=final_df.copy()
            #new_df=new_df.loc[:, new_df.columns.notna()]
            # st.session_state["final_df"] = final_df
            # st.session_state["mapping_df"]=final_df
    multiple_indices_file_path = path.replace("uploaded_files","modified_files").replace(".xlsx",f"{sheet_name}_multiple_indices.csv")
    final_combined_df.to_csv(multiple_indices_file_path, index=False)
    return multiple_indices_file_path



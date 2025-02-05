from pandasai.skills import skill
from common.llm import get_llm
import pandas as pd
from ydata_profiling import ProfileReport
import json
import re
@skill
def profiler(df: pd.DataFrame):
    """
    Write the generated insights based on the profile report using streamlit
    Args:
        df (pd.DataFrame) : a Pandas DataFrame that requires profiling for insights generation.
    """

    all_dataset_full_profile_report = []
    all_dataset_subset_profile_report = []
    summary_list = []
    alert_list = []
    table_column_list = []

    ## For each file in the directory get profile report
    # for idx in range(len(data)):
    #     # Read the file into a pandas dataframe
    #     if upload_type == "Browse from Local":
    #         file_name = file_list["file_name"]
    #     elif upload_type == "GCP GCS":
    #         file_name = file_list.split("/")[-1]
    #     print(file_name)
    #     if file_type == "csv":
    #         if functionality == "Generate":
    #             df = data[idx]

        # Initialize dict variable to store the profile report for each file

    dataset_profiling_dict = {}
        # Generate profile report
    profile = ProfileReport(df, title="Profiling Report")
    profiling_json = profile.to_json()
    profile_json_obj = json.loads(profiling_json)

    # Store the profile report in the python dict
    #dataset_profiling_dict["dataset_name"] = file_name
    dataset_profiling_dict["profiling"] = profile_json_obj

    # Store the profile report for each file in the consolidated dict
    all_dataset_full_profile_report.append(dataset_profiling_dict)

        # Get only the attribute name and type of the attribute
    profile_subset = []
    col_dict = {}
    for key, value in profile_json_obj["variables"].items():
        inner_dict = {}
        col_dict[key] = profile_json_obj["variables"][key]["type"]
        inner_dict["name"] = key
        inner_dict["type"] = profile_json_obj["variables"][key]["type"]
        if inner_dict["type"] != "Unsupported":
            inner_dict["distinct_percentage"] = (
                profile_json_obj["variables"][key]["p_distinct"] * 100
            )
            inner_dict["missing_percentage"] = (
                profile_json_obj["variables"][key]["p_missing"] * 100
            )
            if inner_dict["type"] == "Categorical":
                inner_dict["distinct_count"] = profile_json_obj["variables"][key][
                    "n_distinct"
                ]
            if inner_dict["type"] == "Text":
                inner_dict["distinct_count"] = profile_json_obj["variables"][key][
                    "n_distinct"
                ]
            if inner_dict["type"] == "Numeric":
                inner_dict["min"] = profile_json_obj["variables"][key]["min"]
                inner_dict["max"] = profile_json_obj["variables"][key]["max"]

        profile_subset.append(inner_dict)
        # file_name_list.append(file_name)
        # print(type(df))
        # df_list.append(df)
    summary_list.append(profile_json_obj["table"])
    alert_list.append(profile_json_obj["alerts"])

    summary_details = summary_list[0]
    insights = alert_list[0]

    insights = "\n".join(insights).replace("[", "").replace("]", "")


    summarize_insights_prompt = f"""
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    I have a Data file which has below insights and summary generated as part of pandas data profiling:
    insights: {insights}
    summary: {summary_details}
    Please summarize the insights and produce brief text insights about the given data. Also summarize the given summary in brief highlighting important points. Give output in number bullets
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """

    insights_gen = get_llm().invoke(summarize_insights_prompt).content

    #st.write(summary)
    combined= insights_gen
    #st.write(combined)
    return combined

@skill
def dq_rule_gen(df: pd.DataFrame):
    """
    Write the generated DQ rules based on the profile report using streamlit.
    Args:
        df (pd.DataFrame) : a Pandas DataFrame that requires profiling for DQ rules generation.
    """

    all_dataset_full_profile_report = []
    all_dataset_subset_profile_report = []
    summary_list = []
    alert_list = []
    table_column_list = []


    dataset_profiling_dict = {}
        # Generate profile report
    profile = ProfileReport(df, title="Profiling Report")
    profiling_json = profile.to_json()
    profile_json_obj = json.loads(profiling_json)

    # Store the profile report in the python dict
    #dataset_profiling_dict["dataset_name"] = file_name
    dataset_profiling_dict["profiling"] = profile_json_obj

    # Store the profile report for each file in the consolidated dict
    all_dataset_full_profile_report.append(dataset_profiling_dict)

        # Get only the attribute name and type of the attribute
    profile_subset = []
    col_dict = {}
    for key, value in profile_json_obj["variables"].items():
        inner_dict = {}
        col_dict[key] = profile_json_obj["variables"][key]["type"]
        inner_dict["name"] = key
        inner_dict["type"] = profile_json_obj["variables"][key]["type"]
        if inner_dict["type"] != "Unsupported":
            inner_dict["distinct_percentage"] = (
                profile_json_obj["variables"][key]["p_distinct"] * 100
            )
            inner_dict["missing_percentage"] = (
                profile_json_obj["variables"][key]["p_missing"] * 100
            )
            if inner_dict["type"] == "Categorical":
                inner_dict["distinct_count"] = profile_json_obj["variables"][key][
                    "n_distinct"
                ]
            if inner_dict["type"] == "Text":
                inner_dict["distinct_count"] = profile_json_obj["variables"][key][
                    "n_distinct"
                ]
            if inner_dict["type"] == "Numeric":
                inner_dict["min"] = profile_json_obj["variables"][key]["min"]
                inner_dict["max"] = profile_json_obj["variables"][key]["max"]

        profile_subset.append(inner_dict)
        # file_name_list.append(file_name)
        # print(type(df))
        # df_list.append(df)
    summary_list.append(profile_json_obj["table"])
    alert_list.append(profile_json_obj["alerts"])
    all_dataset_subset_profile_report.append(profile_subset)
    temp = {}
    # temp["table_name"] = file_name
    temp["attributes"] = col_dict
    table_column_list.append(temp)

    temp_dict = all_dataset_full_profile_report[0]["profiling"].copy()
    attrs = temp_dict["variables"].keys()

    #print(len(summary_list), len(alert_list), len(all_dataset_subset_profile_report))

    metadata_gen_prompt_template_part1 = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an expert in data modelling and business domain concepts and you are generating the business meaning or context of database Attribute and Entity.
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    Context: you will be provided a list of JSON as an input. Each JSON object is list of attributes of an Entity.
    Try your best to generate description for each attribute by inferring the business context of the attribute from its name and additional details provided. Analyze the list of attributes in an entity and try best to generate a valid name for the entity (which best explains all the attributes) based on your domain knowledge. The entity name should be compatible for any database following ANSI standard, each entity should have valid description generated based on the attribute details provided. Use underscore(_) as a separator for entity name.
    Generate output in the below format:
    [{"entity": entity_name, "description":"entity_description", "attributes": [{"attribute_name": column_name, "type":column_type, "description": column_description, "missing_percentage": missing_percentage, "distinct_percentage": distinct_percentage, .. other columns}, ....] }, ...]

    Make sure to follow the given output format above.
    """
    metadata_gen_prompt_template_part2 = f"""
    Input: {all_dataset_subset_profile_report}
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    Respond only with valid JSON. Do not write an introduction or summary.
    """

    message = metadata_gen_prompt_template_part1 + metadata_gen_prompt_template_part2
    response = get_llm().invoke(message).content

    print(response)

    res_match = re.search(r'\[.*\]', response, re.DOTALL)

    if res_match:

        response_parsed = res_match.group(0)

    entity_details_formatted = json.loads(response_parsed)

    for i in range(len(entity_details_formatted)):
        entity_details_formatted[i]["summary"] = summary_list[i]
        entity_details_formatted[i]["Insights"] = alert_list[i]

    entity_details = entity_details_formatted[0]

    generate_data_quality_rules_prompt = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Given the following details of an attribute in a particular entity, Give the proper valid objective and actionable data quality rules that should be checked when the data is flowing into the downstream system in a valid csv format with fields rule name and rule description

    <|begin_of_text|><|start_header_id|>user<|end_header_id|>
    Table name:{tbl_name}
    Table description:{tbl_description}
    Attribute name:{col_name}
    Attribute description:{col_desc}
    Attribute data profile report:{report}

    JSON formatted output:

    Example:
    ["Attribute": Attribute_name, "description":Attribute_description, "rules": [{{"rule_name": rule_name, "rule_description": rule_description}}, ....]]

    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    Respond only with valid JSON. Do not write an introduction or summary.
    """

    rules_list = []
    for attribute in entity_details["attributes"]:

        temp = attribute
        temp["entity_name"] = entity_details["entity"]
        temp["entity_description"] = entity_details["description"]
        #attribute_str = json.dumps(attribute)
        generated_rule = get_llm().invoke(
            generate_data_quality_rules_prompt.format(
                tbl_name=entity_details["entity"],
                tbl_description=entity_details["description"],
                col_name=attribute["attribute_name"],
                col_desc=attribute["description"],
                report= attribute,
            )
        ).content
        print(generated_rule)

        match = re.search(r'\[.*\]', generated_rule, re.DOTALL)

        if match:

            generated_rule_parsed = match.group(0)

        generated_rule_obj = json.loads(generated_rule_parsed)
        print(generated_rule_obj)

        rules_list.extend(generated_rule_obj)
    # Flatten the nested structure
    flattened_data = []
    for item in rules_list:
        attribute = item["Attribute"]
        description = item["description"]

        for rule in item["rules"]:
            rule_name = rule["rule_name"]
            rule_description = rule["rule_description"]
            flattened_data.append({
                "Attribute": attribute,
                "Description": description,
                "Rule Name": rule_name,
                "Rule Description": rule_description
            })

    # Convert the flattened data to a DataFrame
    rules_df = pd.DataFrame(flattened_data)
    return rules_df

@skill
def prc_qty_calculator(df: pd.DataFrame):
    """
    Extract insights based on specific patterns from the 'Deal' column in the DataFrame.
    The task involves updating the 'MCHNC_PRC_QTY' column with the following logic:

    1. Extract the number that follows 'MB' in the 'Deal' column.
    2. If 'MB' does not exist, extract the character immediately preceding the '/'.
    3. If neither condition is met, set the value in 'MCHNC_PRC_QTY' to 1.

    Args:
        df (pd.DataFrame): A Pandas DataFrame that contains a 'Deal' column for processing and
                           will have its 'MCHNC_PRC_QTY' column updated accordingly.
    """

    import re

    df['MCHNC_PRC_QTY'] = df["Deal"].apply(
            lambda x: (
                re.search(r'MB(\d+)', x).group(1) if isinstance(x, str) and 'MB' in x and re.search(r'MB(\d+)', x) else
                (x[x.index('/') - 1] if isinstance(x, str) and '/' in x and x.index('/') > 0 else '1')
            ) if isinstance(x, str) else '1'
        )
    return df

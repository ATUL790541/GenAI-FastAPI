import streamlit as st
import pandas as pd
import json
import extra_streamlit_components as stx
from st_on_hover_tabs import on_hover_tabs
# from agents.orchestrator import handle_internal_request_generate_descriptions, handle_internal_request_analyze_internal_sheet, handle_external_request, get_external_context_data,external_dataset_general,external_dataset_prompt,external_dataset_general_data,external_dataset_short_name_creation
# from config.config import encoding
import numpy as np
# from config.config import llm
from langchain_databricks import ChatDatabricks
import os, json
import pickle
from langchain_core.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool, StructuredTool
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
import asyncio


current_dir = os.path.dirname(__file__)


logo_path = os.path.join(os.path.dirname(current_dir), 'pepsico_logo.png')

st.set_page_config(
    "Data Catalog Enrichment",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon=logo_path,
)
#st.write(encoding)

title_container = st.container()
page_container = st.container()
source_container = st.container()
#target_container = st.container(height=800, border=False)

app_title, _, app_logo = title_container.columns([5, 3, 1])
app_title.title("Data Catalog Enrichment")
app_logo.image(
    logo_path
)

style_path = os.path.join(current_dir, 'style.css')

st.markdown('<style>' + open(style_path).read() + '</style>', unsafe_allow_html=True)

data = st.file_uploader("Insert the main catalog sheet", type='csv',key="main file")
results = []
# with st.sidebar.container():
        # tabs = on_hover_tabs(tabName=['Internal Dataset','External Dataset'],
        #                      iconName=['📊', '🌐'],
        #                      styles = {'navtab': {'background-color':'#111',
        #                                           'color': '#818181',
        #                                           'font-size': '18px',
        #                                           'transition': '.3s',
        #                                           'white-space': 'nowrap',
        #                                           'text-transform': 'capitalize'},
        #                                'tabOptionsStyle': {':hover :hover': {'color': 'white',
        #                                                               'cursor': 'pointer'}},
        #                                'iconStyle':{'position':'fixed',
        #                                             'left':'7.5px',
        #                                             'text-align': 'left'},
        #                                'tabStyle' : {'list-style-type': 'none',
        #                                              'margin-bottom': '30px',
        #                                              'padding-left': '30px'}},
        #                      key="1")
def get_llm():
    # os.environ["DATABRICKS_HOST"] = "https://adb-6926527074777965.5.azuredatabricks.net"
    # os.environ["DATABRICKS_TOKEN"] = "dapi477662799536f4c6227fc9ba317d49f8-3"

    # llm_pa= ChatDatabricks(
    #         endpoint = "databricks-meta-llama-3-1-70b-instruct",
    #         max_tokens=8192,
    #         temperature=0,
    #     )

    llm_pa = AzureChatOpenAI(
        api_version="2023-03-15-preview",
        api_key="ede9daf6a5424bc181860e02ed75b492",
        azure_endpoint="https://sanjoy-llm-accelerator.openai.azure.com/",
        azure_deployment="llm-accelerator-new",
        model="GPT-4o-mini",
        openai_api_type="azure",
        temperature=0,
    )
    return llm_pa



async def query_expander_async(query_generalized_template, definition_set, source_column, table):

    # for i in definition_set:
    #     if source_column in i.keys():
    #         table = i[source_column]["Table"]

    # Adding Table Context
    context_prompt = '''You have immense knowledge in the {source_type} systems.
    You are given an input table named {entity} used in the {source_type} systems.
    Give a brief context of the table.
    '''
    entity_context_retrieved = await get_llm().ainvoke(context_prompt.format(source_type = "Retail", entity = table))

    entity_context_response = entity_context_retrieved.content

    entity_context_obj = {
        table: entity_context_response
    }

    filtered_definition_set = []
    for i in definition_set:
        values = list(i.values())
        # print(values)
        if values[0]["Table"] == table:
            filtered_definition_set.append(i)

    # print(filtered_definition_set)
    query_expander_prompt = PromptTemplate(
        input_variables=["original_query"],
        partial_variables={"definitions": filtered_definition_set,"source_type":"Retail","source_desc": "sales data", "entity_context": json.dumps(entity_context_obj), "entity":list(entity_context_obj.keys())[0]},
        template=query_generalized_template
    )

    st.write(query_expander_prompt.pretty_repr())
    query_expander_chain = query_expander_prompt | get_llm()

    expanded_response = await query_expander_chain.ainvoke(source_column)

    expanded_source_column = expanded_response.content

    return {source_column : expanded_source_column}

async def create_definition_through_llama(column_table_list, source_type, source_desc):

    # query_generalized_template = """
    # <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    # You are an AI assistant expert specializing in understanding of the {source_type} data and {source_desc}, particularly for a CPG (Consumer Packaged Goods) company and you will be provided with a set of definitions for some {source_type} terms and the common table definition to which these terms are associated with. Your task is to use your immense knowledge and these set of definitions to create an eloborative description by adding a clear and concise context around the {source_type} related term mentioned in the input.
    # |eot_id|><|start_header_id|>user<|end_header_id|>

    # Definitions for some {source_type} terms: {definitions}
    # Table Definition: {entity_context}
    # Input: {original_query}

    # Make sure that the description is concise and to the point.
    # Do not write an introduction, summary or explanation. Just provide the final context-enriched input.
    # Note: DO not include statements such as "in the context of the {source_type} data for a Consumer Packaged Goods (CPG) company" and "is not defined in the provided definitions, however, based on the table context".
    # <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    query_generalized_template = """
    You are an AI assistant expert specializing in understanding of the {source_type} data and {source_desc}, particularly for a CPG (Consumer Packaged Goods) company and you will be provided with a set of definitions for some {source_type} terms and the common table definition to which these terms are associated with. Your task is to use your immense knowledge and these set of definitions i.e. {source_type} terms and table definitions (only if applicable) to create an eloborative description by adding a clear and concise context around the {source_type} related term mentioned in the input.

    Definitions for some {source_type} terms: {definitions}

    Table Definition: {entity_context}

    Input: {original_query}

    Note:

    1) Make sure that the description is concise and to the point.

    2) DO not include statements such as "in the context of the {source_type} data for a Consumer Packaged Goods (CPG) company" and "is not defined in the provided definitions, however, based on the table context".

    3) Do not include the above provided Table definition of {entity} as it is in the final description.

    Description:
    """




    with open("/home/ec2-user/Pepsico_Hackathon/Pepsico_Main_Hackathon/Pepsico_demo_new_gen_mapping_approach/mapping_assistant/mosaic_context.pkl", "rb") as file:

        definition_set = pickle.load(file)



    tasks = [query_expander_async(query_generalized_template, definition_set, source_column, table) for item in column_table_list for source_column, table in item.items()]

    # Run tasks concurrently and gather results
    source_column_expanded_list = await asyncio.gather(*tasks)
    return source_column_expanded_list

if data is not None:
    df = pd.read_csv(data,encoding='unicode_escape')

    table_options = list(df["Table"].unique())
    table_options.append("ALL")
    table_selected = st.multiselect("Select the tables", table_options)

    if "ALL" in table_selected:
        table_selected = df["Table"].unique()

    filter_df = df[df["Table"].isin(table_selected)]

    df_without_desc = filter_df[filter_df["Description"].isnull()]

    column_options = list(df_without_desc["Column"].unique())
    column_options.append("ALL")
    column_list_selected = st.multiselect("Select the columns you want to generate defintions", column_options)

    if "ALL" in column_list_selected:

        column_list_selected = df_without_desc["Column"].unique()

    filtered_df = df_without_desc[df_without_desc["Column"].isin(column_list_selected)]

    column_table_list = [{row["Column"]: row["Table"]} for _, row in filtered_df.iterrows()]


    if st.button("Submit"):
        with st.spinner("Processing..."):
            final_output = asyncio.run(create_definition_through_llama(column_table_list, "Retail", "sales data"))

            # st.write(final_output)

            data = []
            for item in final_output:

                for source_column, definition in item.items():

                    data.append({"column": source_column, "definition": definition})
                    st.write(source_column+"\n")

                    st.write(definition)

            final_df = pd.DataFrame(data, columns=["column","definition"])
            final_df.to_csv("/home/ec2-user/Pepsico_Hackathon/Pepsico_Main_Hackathon/Pepsico_demo_new_gen_mapping_approach/mapping_assistant/generated_mosaic_app_definition.csv",index=False)





    # if tabs == "Internal Dataset":
    #     chosen_tab=stx.tab_bar(
    #     data=[
    #     stx.TabBarItemData(id="Build Knowledge", title="Build Knowledge", description=""),
    #     stx.TabBarItemData(id="Generate Descriptions", title="Generate Descriptions", description=""),
    #     stx.TabBarItemData(id="Build Description", title='Build Description',description=""),
    #     ])

    #     if chosen_tab=="Build Knowledge":
    #         data = st.file_uploader("Insert the internal attribute file", type='csv',key="input attribute file")
    #         if data is not None:
    #             df = pd.read_csv(data)
    #             if st.button("Add to Knowledge",key="Generate descriptions"):
    #                 with st.spinner(text="processing..."):
    #                     handle_internal_request_analyze_internal_sheet(df)


    #     if chosen_tab=="Generate Descriptions":
    #         token=0
    #         #st.write(df)

    #         internal_df = df[df['Source Domain Type'] == 'Internal']
    #         if not internal_df.empty:
    #             domains = internal_df['System Short Name'].unique()
    #             selected_domain = st.selectbox("Select Domain", domains)

    #             domain_df = internal_df[internal_df['System Short Name'] == selected_domain]
    #             attributes = domain_df['Attributes'].str.cat(sep=',').split(',')
    #             selected_attributes = st.multiselect("Select Attributes", attributes)
    #             selected_col,entire_col=st.columns((5,5))
    #             with selected_col:
    #                 if st.button("Generate selected definitions"):

    #             #st.dataframe(domain_df["Attributes"])
    #                     for attribute in selected_attributes:
    #                             user = f'Give the most similar attribute to {attribute} within the {selected_domain} domain'
    #                             attribute, similar_attribute, bus_def,token = handle_internal_request_generate_descriptions(attribute, user, selected_domain)

    #                             st.markdown(f"""
    #                             **{attribute}**
    #                             * **Similar Attribute Name:** {similar_attribute}
    #                             * **Business Definition:** {bus_def}
    #                             """)
    #         with entire_col:
    #             if st.button("Generate All Definitions", key="Internal Dataset"):

    #                 progress_text = "Operation in progress. Please wait. ⏳"
    #                 status_text = st.empty()

    #                 # Initialize DataFrame to store results
    #                 result_df = pd.DataFrame(columns=['attribute_name', 'similar_attribute', 'business_definition'])
    #                 dfs=[]

    #                 # Show progress bar
    #                 progress_placeholder = st.empty()
    #                 progress_placeholder.write(progress_text)
    #                 progress_placeholder.progress(0)

    #                 # Loop through attributes and process them
    #                 for index, attribute in enumerate(attributes, 1):
    #                     with st.spinner(f'Processing {attribute}...'):
    #                         user = f'Give the most similar attribute to {attribute} within the {selected_domain} domain'
    #                         attribute, similar_attribute, bus_def,token = handle_internal_request_generate_descriptions(attribute, user, selected_domain)

    #                         # Create DataFrame for current attribute
    #                         df = pd.DataFrame({
    #                             'attribute_name': [attribute],
    #                             'similar_attribute': [similar_attribute],
    #                             'business_definition': [bus_def]
    #                         })
    #                         dfs.append(df)
    #                         progress_percentage = int(index / len(attributes) * 100)
    #                         progress_placeholder.progress(progress_percentage)
    #                         status_text.text(f"{progress_text} {progress_percentage:.2f}%")

    #                 result_df = pd.concat(dfs, ignore_index=True)
    #                 status_text.text("Operation complete! ⌛")

    #                     #st.write(result_df)
    #                 st.write("Definitions Generated")
    #                 st.session_state["data"] = result_df
    #                 data = st.session_state["data"]
    #                 result_csv = data.to_csv(index=False).encode('utf-8')
    #                 st.download_button(
    #                     "Download the file",
    #                     result_csv,
    #                     "file.csv",
    #                     "text/csv",
    #                     key='Internal_data_download'
    #                 )


    #     if chosen_tab=="Build Description":
    #         data = st.file_uploader("Insert the internal attribute file", type='csv',key="input attribute file")
    #         if st.button("Generate Business Description", key="Internal Dataset"):
    #             if data is not None:
    #                 df = pd.read_csv(data)
    #             total_len = len(df)
    #             df['Recommended_Business_Definition'] = None
    #             progress_text = "Operation in progress. Please wait. ⏳"
    #             status_text = st.empty()
    #             progress_placeholder = st.empty()
    #             progress_placeholder.write(progress_text)
    #             progress_placeholder.progress(0)
    #             for index, row in df.iterrows():
    #                 attrib_name = row['attribute_name']
    #                 simi_definition = row['business_definition']
    #                 if(simi_definition is np.nan):
    #                     external_prompt=f'''
    #                         You are a subject matter expert (SME) in the Consumer Packaged Goods (CPG) domain.
    #                         Your expertise and experience enable you to provide accurate and concise descriptions of attributes within the CPG domain
    #                         Task:
    #                             Your task is to generate an accurate and concise technical description of the given attribute.
    #                             The description should be technically precise and up to the point and should be valid in terms of CPG domain.
    #                             Give the most accurate description of the attribute.
    #                             Do not give any generic results.
    #                             Attribute: {attrib_name}
    #                             Based on your expertise, generate 1-2 lines of short decription of the attribute.
    #                             Do not mention the areas where the attribute is used.
    #                             Only mention its technical description of the attribute in the CPG domain
    #                             '''

    #                     val=llm(external_prompt)
    #                     #print("empty definition")
    #                     df.at[index, 'Recommended_Business_Definition'] = val

    #                 elif (attrib_name.replace(" ", "").lower() == simi_definition.replace(" ", "").lower() or attrib_name == simi_definition):
    #                     external_prompt=f'''
    #                         You are a subject matter expert (SME) in the Consumer Packaged Goods (CPG) domain.
    #                         Your expertise and experience enable you to provide accurate and concise descriptions of attributes within the CPG domain
    #                         Task:
    #                             Your task is to generate an accurate and concise technical description of the given attribute.
    #                             The description should be technically precise and up to the point and should be valid in terms of CPG domain.
    #                             Give the most accurate description of the attribute.
    #                             Do not give any generic results.
    #                             Attribute: {simi_definition}
    #                             Based on your expertise, generate 1-2 lines of short decription of the attribute.
    #                             Do not mention the areas where the attribute is used.
    #                             Only mention its technical description of the attribute in the CPG domain
    #                             '''

    #                     val=llm(external_prompt)
    #                     #print(val)
    #                     df.at[index, 'Recommended_Business_Definition'] = val
    #                     #print(index,"Upadted")
    #                 else:
    #                     def_process = simi_definition.split()

    #                     #print(def_process)
    #                     def_leng = len(def_process)
    #                     #print(def_leng)
    #                     if(def_leng<=3):
    #                         external_prompt=f'''
    #                             You are a subject matter expert (SME) in the Consumer Packaged Goods (CPG) domain.
    #                             Your expertise and experience enable you to provide accurate and concise descriptions of attributes within the CPG domain
    #                             Task:
    #                                 Your task is to generate an accurate and concise technical description of the given attribute.
    #                                 The description should be technically precise and up to the point and should be valid in terms of CPG domain.
    #                                 Give the most accurate description of the attribute.
    #                                 Do not give any generic results.
    #                                 Attribute: {simi_definition}
    #                                 Based on your expertise, generate 1-2 lines of short decription of the attribute.
    #                                 Do not mention the areas where the attribute is used.
    #                                 Only mention its technical description of the attribute in the CPG domain
    #                                 '''

    #                         val=llm(external_prompt)
    #                         #print(val)
    #                         df.at[index, 'Recommended_Business_Definition'] = val
    #                         #print(f"Row {index}: different")
    #                     else:
    #                         pass
    #                 progress_percentage = int((index+1)/ total_len * 100)
    #                 progress_placeholder.progress(progress_percentage)
    #                 status_text.text(f"{progress_text} {progress_percentage:.2f}%")

    #             status_text.text("Operation complete! ⌛")
    #             st.write("Definitions value Generated")
    #             #st.session_state["data"] = result_df
    #             #data = st.session_state["data"]
    #             result_df = df.copy()
    #             result_csv = result_df.to_csv(index=False).encode('utf-8')
    #             st.download_button(
    #                     "Download the file",
    #                     result_csv,
    #                     "desc_file.csv",
    #                     "text/csv",
    #                     key='Description_data_download'
    #                 )




    # if tabs == "External Dataset":
        # token=0
        # external_df = df[df['Source Domain Type'] == 'External']

        # domain=external_df["Source Domain"].unique().tolist()
        # selected_domain=st.selectbox("Select the domain",domain)
        # if selected_domain=="SAP":
        #     tables = external_df[external_df["Source Domain"] == "SAP"]["Source Table Name"].unique().tolist()
        #     selected_table = st.selectbox("Select the Table", tables)
        #     external_df = external_df[external_df["Source Table Name"] == selected_table]
        #     attributes = external_df['Attributes'].str.cat(sep=',').split(',')
        #     selected_attributes = st.multiselect("Select Attributes", attributes)

        #     #context_dict = {table: get_external_context_data(table) for table in tables}
        #     # context_dict = {table: {"context": get_external_context_data(table)[0], "token": get_external_context_data(table)[1]} for table in tables}
        #     # entity = selected_table
        #     # token+=context_dict[entity]["token"]
        #     # #st.write(f"token for {entity} context is:{token}")



        #     st.session_state["external_general"]=''
        #     result_df= pd.DataFrame(columns=['attribute_name','short_name','business_definition'])
        #     external_select,external_general=st.columns((5,5))
        #     st.session_state["external_general"]=external_general
        #     with external_select:
        #         if st.button("Generate selected definitions",key="External Dataset_SAP"):
        #             with st.spinner("processing...."):
        #                 context,token=get_external_context_data(selected_table)
        #                 st.session_state["context"]=context
        #                 #st.write(context)
        #                 for attribute in selected_attributes:
        #                     entity = selected_table
        #                     #context = context_dict[entity]["context"]
        #                     #token=context_dict[entity]["token"]
        #                     short_name, business_def,recieved_token = handle_external_request(attribute, entity, context)

        #                     token+=recieved_token
        #                     st.markdown(f"""
        #                     **{attribute}**
        #                     * **Short Description:** {short_name}
        #                     * **Business Definition:** {business_def}
        #                     """)
        #     #st.write(f"total_token:{token}")



        # else:
        #     tables = external_df[external_df["Source Domain"] == selected_domain]["Source Table Name"].unique().tolist()
        #     attribute=''
        #     short_name=''
        #     business_def=''

        #     selected_table = st.selectbox("Select the Table", tables)
        #     external_df = external_df[(external_df["Source Domain"] == selected_domain)&(external_df["Source Table Name"] == selected_table)]
        #     attributes = external_df['Attributes'].str.cat(sep=',').split(',')
        #     selected_attributes = st.multiselect("Select Attributes", attributes)
        #     st.session_state["external_general"]=''
        #     result_df1= pd.DataFrame(columns=['attribute_name','business_definition'])
        #     external_select,external_general=st.columns((5,5))
        #     st.session_state["external_general"]=external_general

        #     with external_select:
        #         if st.button("Generate selected defintions",key="External Dataset"):
        #             with st.spinner("processing...."):
        #                 for attribute in selected_attributes:
        #                     #st.write(attribute)
        #                     short_name,recieved_token=external_dataset_short_name_creation(attribute)
        #                     token+=recieved_token
        #                     business_def,recieved_token = external_dataset_general_data(attribute)
        #                     token+=recieved_token
        #                     #st.write(f"Attribute Name: {attribute} | Business Definition: {business_def}")
        #                     st.markdown(f"""
        #                     **{attribute}**
        #                     * **Short Description:** {short_name}
        #                     * **Business Definition:** {business_def}
        #                     """)
        #     #st.write(f"Total token:{token}")
        # external_general=st.session_state["external_general"]

        # with external_general:
        #     if st.button("Generate all definitions", key="External all Dataset"):
        #         #st.write(selected_domain)
        #         result_df = pd.DataFrame(columns=['attribute_name', 'short_description', 'business_definition'])
        #         if selected_domain == "SAP":


        #             progress_text = "Operation in progress. Please wait. ⏳"
        #             status_text = st.empty()
        #             dfs=[]

        #             # Show progress bar
        #             progress_placeholder = st.empty()
        #             progress_placeholder.write(progress_text)
        #             progress_placeholder.progress(0)

        #             # Loop through attributes and process them
        #             for index, attribute in enumerate(attributes, 1):
        #                 with st.spinner(f'Processing {attribute}...'):
        #                     entity = selected_table
        #                     context=st.session_state["context"]
        #                     #st.write(context)
        #                     #context = context_dict[entity]
        #                     short_name, business_def,token = handle_external_request(attribute, entity, context)
        #                     df = pd.DataFrame({
        #                         'attribute_name': [attribute],
        #                         'short_description': [short_name],
        #                         'business_definition': [business_def]
        #                     })
        #                     dfs.append(df)
        #                     progress_percentage = int(index / len(attributes) * 100)
        #                     progress_placeholder.progress(progress_percentage)
        #                     status_text.text(f"{progress_text} {progress_percentage:.2f}%")

        #             result_df = pd.concat(dfs, ignore_index=True)
        #             status_text.text("Operation complete! ⌛")

        #         else:
        #             progress_text = "Operation in progress. Please wait. ⏳"
        #             status_text = st.empty()
        #             dfs=[]

        #             # Show progress bar
        #             progress_placeholder = st.empty()
        #             progress_placeholder.write(progress_text)
        #             progress_placeholder.progress(0)


        #             for index, attribute in enumerate(attributes, 1):
        #                 with st.spinner(f'Processing {attribute}...'):
        #                     entity = selected_table
        #                     #context = context_dict[entity]
        #                     short_name,token=external_dataset_short_name_creation(attribute)
        #                     business_def,token = external_dataset_general_data(attribute)
        #                     df = pd.DataFrame({
        #                         'attribute_name': [attribute],
        #                         'short_description':[short_name],
        #                         'business_definition': [business_def]
        #                     })
        #                     dfs.append(df)
        #                     progress_percentage = int(index / len(attributes) * 100)
        #                     progress_placeholder.progress(progress_percentage)
        #                     status_text.text(f"{progress_text} {progress_percentage:.2f}%")


        #             result_df = pd.concat(dfs, ignore_index=True)

        #         st.write("Definitions Generated")
        #         st.session_state["data"] = result_df
        #         data = st.session_state["data"]
        #         result_csv = data.to_csv(index=False).encode('utf-8')
        #         st.download_button(
        #             "Download the file",
        #             result_csv,
        #             "file.csv",
        #             "text/csv",
        #             key='External_data_download'
        #         )


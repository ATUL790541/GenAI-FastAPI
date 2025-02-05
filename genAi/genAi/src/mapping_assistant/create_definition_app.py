import streamlit as st
import pandas as pd
import json
import extra_streamlit_components as stx
from st_on_hover_tabs import on_hover_tabs
from agents.orchestrator import handle_internal_request_generate_descriptions, handle_internal_request_analyze_internal_sheet, handle_external_request, get_external_context_data,external_dataset_general,external_dataset_prompt,external_dataset_general_data,external_dataset_short_name_creation
from config.config import encoding
import numpy as np
from config.config import llm

st.set_page_config(
    "Data Catalog Enrichment",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="https://www.tigeranalytics.com/wp-content/uploads/2023/09/TA-Logo-resized-for-website_.png",
)
#st.write(encoding)

title_container = st.container()
page_container = st.container()
source_container = st.container()
#target_container = st.container(height=800, border=False)

app_title, _, app_logo = title_container.columns([5, 3, 1])
app_title.title("Data Catalog Enrichment")
app_logo.image(
    "https://www.tigeranalytics.com/wp-content/uploads/2023/09/TA-Logo-resized-for-website_.png"
)
st.markdown('<style>' + open('./style.css').read() + '</style>', unsafe_allow_html=True)

data = st.file_uploader("Insert the main catalog sheet", type='csv',key="main file")
results = []
with st.sidebar.container():
        tabs = on_hover_tabs(tabName=['Internal Dataset','External Dataset'], 
                             iconName=['📊', '🌐'],
                             styles = {'navtab': {'background-color':'#111',
                                                  'color': '#818181',
                                                  'font-size': '18px',
                                                  'transition': '.3s',
                                                  'white-space': 'nowrap',
                                                  'text-transform': 'capitalize'},
                                       'tabOptionsStyle': {':hover :hover': {'color': 'white',
                                                                      'cursor': 'pointer'}},
                                       'iconStyle':{'position':'fixed',
                                                    'left':'7.5px',
                                                    'text-align': 'left'},
                                       'tabStyle' : {'list-style-type': 'none',
                                                     'margin-bottom': '30px',
                                                     'padding-left': '30px'}},
                             key="1")

if data is not None:
    df = pd.read_csv(data,encoding='unicode_escape')
        

    
        
    

    if tabs == "Internal Dataset":
        chosen_tab=stx.tab_bar(
        data=[
        stx.TabBarItemData(id="Build Knowledge", title="Build Knowledge", description=""),
        stx.TabBarItemData(id="Generate Descriptions", title="Generate Descriptions", description=""),
        stx.TabBarItemData(id="Build Description", title='Build Description',description=""),
        ])
        
        if chosen_tab=="Build Knowledge":
            data = st.file_uploader("Insert the internal attribute file", type='csv',key="input attribute file")
            if data is not None:
                df = pd.read_csv(data)
                if st.button("Add to Knowledge",key="Generate descriptions"):
                    with st.spinner(text="processing..."):
                        handle_internal_request_analyze_internal_sheet(df)


        if chosen_tab=="Generate Descriptions":
            token=0
            #st.write(df)
            
            internal_df = df[df['Source Domain Type'] == 'Internal']
            if not internal_df.empty:
                domains = internal_df['System Short Name'].unique()
                selected_domain = st.selectbox("Select Domain", domains)
                
                domain_df = internal_df[internal_df['System Short Name'] == selected_domain]
                attributes = domain_df['Attributes'].str.cat(sep=',').split(',')
                selected_attributes = st.multiselect("Select Attributes", attributes)
                selected_col,entire_col=st.columns((5,5))
                with selected_col:
                    if st.button("Generate selected definitions"):

                #st.dataframe(domain_df["Attributes"])
                        for attribute in selected_attributes:
                                user = f'Give the most similar attribute to {attribute} within the {selected_domain} domain'
                                attribute, similar_attribute, bus_def,token = handle_internal_request_generate_descriptions(attribute, user, selected_domain)
                                
                                st.markdown(f"""
                                **{attribute}**
                                * **Similar Attribute Name:** {similar_attribute}
                                * **Business Definition:** {bus_def}
                                """)
            with entire_col:
                if st.button("Generate All Definitions", key="Internal Dataset"):
                    
                    progress_text = "Operation in progress. Please wait. ⏳"
                    status_text = st.empty()
                    
                    # Initialize DataFrame to store results
                    result_df = pd.DataFrame(columns=['attribute_name', 'similar_attribute', 'business_definition'])
                    dfs=[]
                    
                    # Show progress bar
                    progress_placeholder = st.empty()
                    progress_placeholder.write(progress_text)
                    progress_placeholder.progress(0)
                    
                    # Loop through attributes and process them
                    for index, attribute in enumerate(attributes, 1):
                        with st.spinner(f'Processing {attribute}...'):
                            user = f'Give the most similar attribute to {attribute} within the {selected_domain} domain'
                            attribute, similar_attribute, bus_def,token = handle_internal_request_generate_descriptions(attribute, user, selected_domain)
                            
                            # Create DataFrame for current attribute
                            df = pd.DataFrame({
                                'attribute_name': [attribute],
                                'similar_attribute': [similar_attribute],
                                'business_definition': [bus_def]
                            })
                            dfs.append(df)
                            progress_percentage = int(index / len(attributes) * 100)
                            progress_placeholder.progress(progress_percentage)
                            status_text.text(f"{progress_text} {progress_percentage:.2f}%")
                    
                    result_df = pd.concat(dfs, ignore_index=True)
                    status_text.text("Operation complete! ⌛")

                        #st.write(result_df)
                    st.write("Definitions Generated")
                    st.session_state["data"] = result_df
                    data = st.session_state["data"]
                    result_csv = data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download the file",
                        result_csv,
                        "file.csv",
                        "text/csv",
                        key='Internal_data_download'
                    )
        
        
        if chosen_tab=="Build Description":
            data = st.file_uploader("Insert the internal attribute file", type='csv',key="input attribute file")
            if st.button("Generate Business Description", key="Internal Dataset"):
                if data is not None:
                    df = pd.read_csv(data)
                total_len = len(df)
                df['Recommended_Business_Definition'] = None
                progress_text = "Operation in progress. Please wait. ⏳"
                status_text = st.empty()
                progress_placeholder = st.empty()
                progress_placeholder.write(progress_text)
                progress_placeholder.progress(0)
                for index, row in df.iterrows():
                    attrib_name = row['attribute_name']  
                    simi_definition = row['business_definition']
                    if(simi_definition is np.nan):
                        external_prompt=f'''
                            You are a subject matter expert (SME) in the Consumer Packaged Goods (CPG) domain.
                            Your expertise and experience enable you to provide accurate and concise descriptions of attributes within the CPG domain
                            Task:
                                Your task is to generate an accurate and concise technical description of the given attribute. 
                                The description should be technically precise and up to the point and should be valid in terms of CPG domain.
                                Give the most accurate description of the attribute.
                                Do not give any generic results.
                                Attribute: {attrib_name}
                                Based on your expertise, generate 1-2 lines of short decription of the attribute.
                                Do not mention the areas where the attribute is used.
                                Only mention its technical description of the attribute in the CPG domain 
                                '''
                    
                        val=llm(external_prompt)
                        #print("empty definition")
                        df.at[index, 'Recommended_Business_Definition'] = val
                        
                    elif (attrib_name.replace(" ", "").lower() == simi_definition.replace(" ", "").lower() or attrib_name == simi_definition):
                        external_prompt=f'''
                            You are a subject matter expert (SME) in the Consumer Packaged Goods (CPG) domain.
                            Your expertise and experience enable you to provide accurate and concise descriptions of attributes within the CPG domain
                            Task:
                                Your task is to generate an accurate and concise technical description of the given attribute. 
                                The description should be technically precise and up to the point and should be valid in terms of CPG domain.
                                Give the most accurate description of the attribute.
                                Do not give any generic results.
                                Attribute: {simi_definition}
                                Based on your expertise, generate 1-2 lines of short decription of the attribute.
                                Do not mention the areas where the attribute is used.
                                Only mention its technical description of the attribute in the CPG domain 
                                '''
                    
                        val=llm(external_prompt)
                        #print(val)
                        df.at[index, 'Recommended_Business_Definition'] = val
                        #print(index,"Upadted")
                    else:
                        def_process = simi_definition.split()
                        
                        #print(def_process)
                        def_leng = len(def_process)
                        #print(def_leng)
                        if(def_leng<=3):
                            external_prompt=f'''
                                You are a subject matter expert (SME) in the Consumer Packaged Goods (CPG) domain.
                                Your expertise and experience enable you to provide accurate and concise descriptions of attributes within the CPG domain
                                Task:
                                    Your task is to generate an accurate and concise technical description of the given attribute. 
                                    The description should be technically precise and up to the point and should be valid in terms of CPG domain.
                                    Give the most accurate description of the attribute.
                                    Do not give any generic results.
                                    Attribute: {simi_definition}
                                    Based on your expertise, generate 1-2 lines of short decription of the attribute.
                                    Do not mention the areas where the attribute is used.
                                    Only mention its technical description of the attribute in the CPG domain 
                                    '''
                        
                            val=llm(external_prompt)
                            #print(val)
                            df.at[index, 'Recommended_Business_Definition'] = val
                            #print(f"Row {index}: different")
                        else:
                            pass
                    progress_percentage = int((index+1)/ total_len * 100)
                    progress_placeholder.progress(progress_percentage)
                    status_text.text(f"{progress_text} {progress_percentage:.2f}%")   
                
                status_text.text("Operation complete! ⌛")
                st.write("Definitions value Generated")
                #st.session_state["data"] = result_df
                #data = st.session_state["data"]
                result_df = df.copy()
                result_csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                        "Download the file",
                        result_csv,
                        "desc_file.csv",
                        "text/csv",
                        key='Description_data_download'
                    )
       

            
            
    if tabs == "External Dataset":
        token=0
        external_df = df[df['Source Domain Type'] == 'External']

        domain=external_df["Source Domain"].unique().tolist()
        selected_domain=st.selectbox("Select the domain",domain)
        if selected_domain=="SAP":
            tables = external_df[external_df["Source Domain"] == "SAP"]["Source Table Name"].unique().tolist()
            selected_table = st.selectbox("Select the Table", tables)
            external_df = external_df[external_df["Source Table Name"] == selected_table]
            attributes = external_df['Attributes'].str.cat(sep=',').split(',')
            selected_attributes = st.multiselect("Select Attributes", attributes)

            #context_dict = {table: get_external_context_data(table) for table in tables}
            # context_dict = {table: {"context": get_external_context_data(table)[0], "token": get_external_context_data(table)[1]} for table in tables}
            # entity = selected_table
            # token+=context_dict[entity]["token"]
            # #st.write(f"token for {entity} context is:{token}")
            
            

            st.session_state["external_general"]=''
            result_df= pd.DataFrame(columns=['attribute_name','short_name','business_definition'])
            external_select,external_general=st.columns((5,5))
            st.session_state["external_general"]=external_general
            with external_select:
                if st.button("Generate selected definitions",key="External Dataset_SAP"):
                    with st.spinner("processing...."):
                        context,token=get_external_context_data(selected_table)
                        st.session_state["context"]=context
                        #st.write(context)
                        for attribute in selected_attributes:
                            entity = selected_table
                            #context = context_dict[entity]["context"]
                            #token=context_dict[entity]["token"]
                            short_name, business_def,recieved_token = handle_external_request(attribute, entity, context)
                            
                            token+=recieved_token
                            st.markdown(f"""
                            **{attribute}**
                            * **Short Description:** {short_name}
                            * **Business Definition:** {business_def}
                            """)  
            #st.write(f"total_token:{token}")         
            
                
        
        else:
            tables = external_df[external_df["Source Domain"] == selected_domain]["Source Table Name"].unique().tolist()
            attribute=''
            short_name=''
            business_def=''
            
            selected_table = st.selectbox("Select the Table", tables)
            external_df = external_df[(external_df["Source Domain"] == selected_domain)&(external_df["Source Table Name"] == selected_table)]
            attributes = external_df['Attributes'].str.cat(sep=',').split(',')
            selected_attributes = st.multiselect("Select Attributes", attributes)
            st.session_state["external_general"]=''
            result_df1= pd.DataFrame(columns=['attribute_name','business_definition'])
            external_select,external_general=st.columns((5,5))
            st.session_state["external_general"]=external_general
            
            with external_select:
                if st.button("Generate selected defintions",key="External Dataset"):
                    with st.spinner("processing...."):
                        for attribute in selected_attributes:
                            #st.write(attribute)
                            short_name,recieved_token=external_dataset_short_name_creation(attribute)
                            token+=recieved_token
                            business_def,recieved_token = external_dataset_general_data(attribute)
                            token+=recieved_token
                            #st.write(f"Attribute Name: {attribute} | Business Definition: {business_def}")
                            st.markdown(f"""
                            **{attribute}**                    
                            * **Short Description:** {short_name}
                            * **Business Definition:** {business_def}
                            """) 
            #st.write(f"Total token:{token}")
        external_general=st.session_state["external_general"]

        with external_general:
            if st.button("Generate all definitions", key="External all Dataset"):
                #st.write(selected_domain)
                result_df = pd.DataFrame(columns=['attribute_name', 'short_description', 'business_definition'])
                if selected_domain == "SAP":
                    

                    progress_text = "Operation in progress. Please wait. ⏳"
                    status_text = st.empty()
                    dfs=[]
                    
                    # Show progress bar
                    progress_placeholder = st.empty()
                    progress_placeholder.write(progress_text)
                    progress_placeholder.progress(0)
                    
                    # Loop through attributes and process them
                    for index, attribute in enumerate(attributes, 1):
                        with st.spinner(f'Processing {attribute}...'):
                            entity = selected_table
                            context=st.session_state["context"]
                            #st.write(context)
                            #context = context_dict[entity]
                            short_name, business_def,token = handle_external_request(attribute, entity, context)
                            df = pd.DataFrame({
                                'attribute_name': [attribute],
                                'short_description': [short_name],
                                'business_definition': [business_def]
                            })
                            dfs.append(df)
                            progress_percentage = int(index / len(attributes) * 100)
                            progress_placeholder.progress(progress_percentage)
                            status_text.text(f"{progress_text} {progress_percentage:.2f}%")
                    
                    result_df = pd.concat(dfs, ignore_index=True)
                    status_text.text("Operation complete! ⌛")
                    
                else:
                    progress_text = "Operation in progress. Please wait. ⏳"
                    status_text = st.empty()
                    dfs=[]
                    
                    # Show progress bar
                    progress_placeholder = st.empty()
                    progress_placeholder.write(progress_text)
                    progress_placeholder.progress(0)
                    

                    for index, attribute in enumerate(attributes, 1):
                        with st.spinner(f'Processing {attribute}...'):
                            entity = selected_table
                            #context = context_dict[entity]
                            short_name,token=external_dataset_short_name_creation(attribute)
                            business_def,token = external_dataset_general_data(attribute)
                            df = pd.DataFrame({
                                'attribute_name': [attribute],
                                'short_description':[short_name],
                                'business_definition': [business_def]
                            })
                            dfs.append(df)
                            progress_percentage = int(index / len(attributes) * 100)
                            progress_placeholder.progress(progress_percentage)
                            status_text.text(f"{progress_text} {progress_percentage:.2f}%")
                    
                        
                    result_df = pd.concat(dfs, ignore_index=True)

                st.write("Definitions Generated")
                st.session_state["data"] = result_df
                data = st.session_state["data"]
                result_csv = data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download the file",
                    result_csv,
                    "file.csv",
                    "text/csv",
                    key='External_data_download'
                )


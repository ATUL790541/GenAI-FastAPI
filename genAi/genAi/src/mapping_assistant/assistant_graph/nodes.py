from langchain.schema import Document
import ast,json
from langchain.prompts import PromptTemplate
from common.llm import get_llm
from mapping_assistant.assistant_common.vector_store import embeddings
from mapping_assistant.assistant_graph.prompts import *
import pickle,os
import lance,asyncio
from langchain_core.vectorstores import InMemoryVectorStore
import pandas as pd
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, model_validator
from langchain_core.exceptions import OutputParserException
import re

llama_llm = get_llm()


async def query_expander_async(query_expander_chain, source_column):

    expanded_response = await query_expander_chain.ainvoke(source_column)

    expanded_source_column = expanded_response.content

    return {source_column : expanded_source_column}

async def rewrite_query(state):
    """
    Rewrite the original query to improve retrieval.

    Args:
    original_query (str): The original user query

    Returns:
    str: The rewritten query
    """

    source_column_list = state["question"]

    # source_type = state["source_type"]

    # source_desc = state["source_desc"]

    # Create a prompt template for query rewriting

    direct_pull_docs_dir = os.path.dirname(os.path.dirname(__file__))

    # Load context for query expander
    # direct_pull_docs_path = os.path.join(direct_pull_docs_dir,"direct_pull_documents.pkl")
    direct_pull_docs_path = os.path.join(direct_pull_docs_dir,"query_expander_context.pkl")


    with open(direct_pull_docs_path, "rb") as file:
        definition_set = pickle.load(file)

    query_expander_prompt = PromptTemplate(
        input_variables=["original_query"],
        partial_variables={"definitions": definition_set},
        template=query_rewrite_template
    )

    query_expander_chain = query_expander_prompt | llama_llm

    # response = await query_rewriter.ainvoke(original_query)

    tasks = [query_expander_async(query_expander_chain, source_column) for source_column in source_column_list]

    # Run tasks concurrently and gather results
    source_column_expanded_list = await asyncio.gather(*tasks)

    return {"expanded_columns": source_column_expanded_list}


    # print(f"Expanded Query -> {response.content}")
    # return {"question":response.content}

async def create_and_retrieve(state):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    # print("---RETRIEVE---")
    # question = state["question"]

    source_column_expanded_list = state["expanded_columns"]


    # Create a vector store on the fly

    source_column_expanded_list = [json.dumps(expanded_source_column) for expanded_source_column in source_column_expanded_list]

    vectorstore = InMemoryVectorStore.from_texts(
        source_column_expanded_list,
        embedding=embeddings,
    )

    # Use the vectorstore as a retriever, 3 records will be fetched
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Load side by side mapping
    cur_dir = os.path.dirname(os.path.dirname(__file__))

    side_by_side_path = os.path.join(cur_dir, "assistant_common","side_by_side_mapping.csv")

    df = pd.read_csv(side_by_side_path)
    #df = pd.read_csv("/home/ec2-user/Pepsico_Hackathon/Pepsico_Main_Hackathon/pepsico_mapping_assistant_newer_approach/common/side_by_side_mapping.csv")

    # direct_pull_records = df[df["Mapping logic"].str.contains("direct pull", case=False, na=False)]
    direct_pull_records = df[(df["Source Column from Input/PPA"].notna()) & (df["Mapping logic"]!="hard code")]

    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Fetch accepted List

    # accepted_file_path = os.path.join(current_dir,"accepted_list.csv")
    # if os.path.exists(accepted_file_path) and os.stat(accepted_file_path).st_size > 1:

    #     acceptions = pd.read_csv(accepted_file_path)
    # else:
    #     acceptions = pd.DataFrame()
    # if not acceptions.empty:
    #     already_accepted_bronze_layer_columns = acceptions["Bronze Layer Column"].to_list()
    #     direct_pull_records = direct_pull_records[~direct_pull_records["Bronze Layer Column"].isin(already_accepted_bronze_layer_columns)]
    # Fetch rejected list

    # rejected_file_path = os.path.join(current_dir,"rejected_list.csv")
    # if os.path.exists(rejected_file_path) and os.stat(rejected_file_path).st_size > 1:

    #     rejections = pd.read_csv(rejected_file_path)
    # else:
    #     rejections = pd.DataFrame()

    # Acceptions Lance file

    accepted_list_lance_path = os.path.join(current_dir,"mapping_assistant","lists","output","lance","acception_list.lance")
    # accepted_lance_vec_ds = lance.dataset(accepted_list_lance_path, version = state["accepted_list_version"]["version"])
    accepted_lance_vec_ds = lance.dataset(accepted_list_lance_path)


    acceptions = accepted_lance_vec_ds.to_table().to_pandas()

    if not acceptions.empty:
        already_accepted_bronze_layer_columns = acceptions["Bronze Layer Column"].to_list()
        direct_pull_records = direct_pull_records[~direct_pull_records["Bronze Layer Column"].isin(already_accepted_bronze_layer_columns)]

    # Rejection Lance file
    rejected_list_lance_path = os.path.join(current_dir,"mapping_assistant","lists","output","lance","rejection_list.lance")
    # rejected_lance_vec_ds = lance.dataset(rejected_list_lance_path, version = state["rejected_list_version"]["version"])
    rejected_lance_vec_ds = lance.dataset(rejected_list_lance_path)
    rejections = rejected_lance_vec_ds.to_table().to_pandas()


    relevant_expanded_queries = []
    for record in json.loads(direct_pull_records.to_json(orient="records")):

        print(record)

        docs = retriever.invoke(json.dumps(record))
        relevant_docs = []
        if not rejections.empty:

            rejections_filtered = rejections[rejections["Bronze Layer Column"] == record["Bronze Layer Column"]]

            if not rejections_filtered.empty:

                # capture the rejected columns for silver layer layer column
                input_column_rejections = rejections_filtered["rejected_match"].values[0].split(", ")

            else:
                # No rejections for this silver layer column
                input_column_rejections = set()

            # retrieved input columns
            input_column_retrieved = {key for doc in docs for key in json.loads(doc.page_content).keys()}

            # Check the difference b/w the retrieved and rejections
            relevant_input_columns = list(set(input_column_retrieved).difference(set(input_column_rejections)))

            # capture the page content for the relevant input columns only
            relevant_docs = [
                doc.page_content
                for doc in docs
                if any(key in relevant_input_columns for key in json.loads(doc.page_content).keys())
            ]

        else:
            # if rejections list is not present
            relevant_docs = [doc.page_content for doc in docs]

        record["relevant_docs"] = relevant_docs

        relevant_expanded_queries.append(record)


    return {"relevent_expanded_queries": relevant_expanded_queries}

# For rating each doc

async def rating_doc(reranker_chain, record_copy,doc):

    input_data = {"record": record_copy, "doc":doc}

    score_response =await reranker_chain.ainvoke(input_data)

    score = score_response.content
    try:
        score = json.loads(score)
        score = float(score["relevance_score"])
    except ValueError:
        score = 0  # Default score if parsing fails
    return (doc, score)

# For reranking docs for each silver layer column

async def reranker_async(reranker_chain, record,top_n):

    # scored_records = []

    record_copy = record.copy()
    del record_copy["relevant_docs"]

    print(record["relevant_docs"])

    if len(record["relevant_docs"]) > 1:
        tasks = [rating_doc(reranker_chain, record_copy,doc) for doc in record["relevant_docs"]]

        # Run tasks concurrently and gather results
        scored_records = await asyncio.gather(*tasks)

        reranked_records = sorted(scored_records, key=lambda x: x[1], reverse=True)
        print(reranked_records)
        # To check if relevence score is same
        docs_with_same_score = []
        highest_relevance_score = reranked_records[0][1]
        for reranked_doc in reranked_records:
            if reranked_doc[1] == highest_relevance_score and len(docs_with_same_score) < 3:
                docs_with_same_score.append(reranked_doc[0])

        # Resolving the scenario if scores match
        if len(docs_with_same_score) > 1:

            print("Resolver Triggered")

            # Add schema
            # Define your desired data structure.
            class ResolverItem(BaseModel):
                document: dict = Field(description="complete document as it is")
                score: int = Field(description="relevence score for the document")
                # # You can add custom validation logic easily with Pydantic.
                # @model_validator(mode="before")
                # @classmethod
                # def header_row_less_than_data_start_row(cls, values: dict) -> dict:
                #     Header_Row_Number = values.get("Header_Row_Number")
                #     Data_Start_Row_Number = values.get("Data_Start_Row_Number")
                #     Data_End_Row_Number = values.get("Data_End_Row_Number")
                #     if Header_Row_Number and Data_Start_Row_Number and Data_End_Row_Number and (Header_Row_Number >= Data_Start_Row_Number or Data_Start_Row_Number > Data_End_Row_Number):
                #         raise ValueError("Invalid row numbers")
                #     return values

            from typing import List
            class Resolver(BaseModel):
                Docs: List[ResolverItem]


            # Set up a parser + inject instructions into the prompt template.
            parser = PydanticOutputParser(pydantic_object=Resolver)

            # result = Resolver.model_validate(data)
            # Add the format instructions based on the Schema provided to the parser in template and create the final prompt
            prompt = PromptTemplate(
                template=resolver_template +"\n {format_instructions}",
                input_variables=["record","doc"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )

            # Create chain
            prompt_and_model = prompt | llama_llm

            input_data = {"record": record_copy, "doc":docs_with_same_score}
            # Execute the chain with the csv data
            # output = prompt_and_model.invoke({"dataframe": df.to_csv()})

            resolver_response = await prompt_and_model.ainvoke(input_data)
            # result = resolver_response.content
            # print(output.content)

            # Pass the output to the parser to get the structured output
            try:
                result = await parser.ainvoke(resolver_response.content)
                formatted_result = result.dict()["Docs"]

            except OutputParserException as e:

                pattern = r"<json>(.*?)</json>"

                json_response = await get_llm().ainvoke(f"""
                    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

                    You are a json expert whose sole responsibility is to format the given input into a valid JSON. Make sure to wrap the output strictly in <json> and </json> tags.

                    Output format to be followed:

                    {parser.get_format_instructions()}

                    <|eot_id|><|start_header_id|>user<|end_header_id|>
                    input: {resolver_response.content}
                    Respond only with Valid JSON""")

                json_text = json_response.content
                matches = re.findall(pattern, json_text, re.DOTALL)
                json_text = matches[0]
                print(json_text)

                eval_text = ast.literal_eval(json_text)
                try:
                    result = Resolver.model_validate(eval_text)
                except:

                    # Convert JSON strings in `document` to dictionaries
                    final_text = {
                    "Docs":[
                        {"document": ast.literal_eval(item["document"]), "score": item["score"]}
                        for item in eval_text["Docs"]
                    ]
                    }
                    # eval_text = ast.literal_eval(json_text)

                    result = Resolver.model_validate(final_text)

                formatted_result = result.model_dump()["Docs"]
                # schema_info = result.model_dump_json(by_alias=True)
                # # Convert the response to a dict
                # formatted_result = result.dict()["Docs"]

            # resolver_prompt = PromptTemplate(input_variables=["record","doc"], template=resolver_template)
            # resolve_chain = resolver_prompt | llama_llm
            # input_data = {"record": record_copy, "doc":docs_with_same_score}
            # resolver_response = await resolve_chain.ainvoke(input_data)
            # result = resolver_response.content
            # try:
            #     formatted_result = json.loads(result)
            # except:
            #     formatted_result = ast.literal_eval(result)

            reranked_top_n_records = sorted(formatted_result, key=lambda x: x["score"], reverse=True)
            #print(reranked_top_n_records)

        else:
            reranked_top_n_records = [doc for doc, _ in reranked_records[:top_n]]

        print("Reranked docs\n", reranked_top_n_records)

        first_record = reranked_top_n_records[0]

        if isinstance(first_record, str):
            first_record = json.loads(first_record)

        best_match = next(iter(first_record))

        if best_match.lower() == "document":

            best_match = next(iter(first_record["document"]))
        # if best_match.lower() == "document":

        #     best_match = next(iter((reranked_top_n_records)[0]['document']))

        if best_match == "{":

            if isinstance(reranked_top_n_records[0], str):
                best_match = next(iter(json.loads(reranked_top_n_records[0])))

            else:
                best_match = next(iter(reranked_top_n_records[0]))

        second_record = reranked_top_n_records[1]

        if isinstance(second_record, str):
            second_record = json.loads(second_record)

        potential_match = next(iter(second_record))

        if potential_match.lower() == "document":

            potential_match = next(iter(second_record["document"]))
        # if best_match.lower() == "document":

        #     best_match = next(iter((reranked_top_n_records)[0]['document']))

        if potential_match == "{":

            if isinstance(reranked_top_n_records[0], str):
                potential_match = next(iter(json.loads(reranked_top_n_records[1])))

            else:
                potential_match = next(iter(reranked_top_n_records[1]))

    # If 2 records have been found in rejections
    elif len(record["relevant_docs"]) == 1:

        first_record = record["relevant_docs"][0]

        if isinstance(first_record, str):
            first_record = json.loads(first_record)

        best_match = next(iter(first_record))
        potential_match = ""

    # If all the retrieved records have been found in rejections list
    else:
        potential_match = ""
        best_match = ""

    return {
            "Bronze Layer Column": record["Bronze Layer Column"],
            "best_match": best_match,
            "potential_match": potential_match
        }

async def rerank_documents(state):
    # query: str, docs: List[Document], top_n: int = 3

    relevant_expanded_queries = state["relevent_expanded_queries"]

    top_n = 3

    # json.loads(relevant_expanded_queries[0]['relevant_docs'][0])

    reranker_prompt = PromptTemplate(
        input_variables=["record","doc"],
        template= reranker_template
    )

    reranker_chain = reranker_prompt | llama_llm

    # scored_records = []
    reranked_top_n_records = []

    tasks = [reranker_async(reranker_chain, record,top_n) for record in relevant_expanded_queries]

    # Run tasks concurrently and gather results
    reranked_list = await asyncio.gather(*tasks)

    return {"ranked_records": reranked_list}


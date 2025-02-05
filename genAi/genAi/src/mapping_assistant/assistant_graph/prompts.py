query_rewrite_template = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an AI assistant expert specializing in understanding of the promotion, financial and PPA (Price Pack Architecture) data, particularly for a CPG (Consumer Packaged Goods) company and you will be provided with a set of definitions for some PPA terms and your task is to use your immense knowledge and these set of definitions to expand the input by adding a clear and concise context around the PPA related term mentioned in the input to improve retrieval in a RAG system.
    |eot_id|><|start_header_id|>user<|end_header_id|>
    It's not necessary to use the definition given here. If you do not find any match for the input in the definition set then use your knowledge to create the final definition.
    Make sure that context is concise and to the point and is not more than 20 words.

    Definitions for some PPA terms: {definitions}
    Input: {original_query}

    Do not write an introduction, summary or explanation. Just provide the final context-enriched input.
    Note: DO not include statements such as "in the context of the Price Pack Architecture (PPA) data for a Consumer Packaged Goods (CPG) company".
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

query_generalized_template = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an AI assistant expert specializing in understanding of the {source_type} data and {source_desc}, particularly for a CPG (Consumer Packaged Goods) company and you will be provided with a set of definitions for some {source_type} terms and your task is to use your immense knowledge and these set of definitions to expand the input by adding a clear and concise context around the {source_type} related term mentioned in the input to improve retrieval in a RAG system.
    |eot_id|><|start_header_id|>user<|end_header_id|>
    It's not necessary to use the definition given here. If you do not find any match for the input in the definition set then use your knowledge to create the final definition.
    Make sure that context is concise and to the point and is not more than 20 words.

    Definitions for some {source_type} terms: {definitions}
    Input: {original_query}

    Do not write an introduction, summary or explanation. Just provide the final context-enriched input.
    Note: DO not include statements such as "in the context of the {source_type} data for a Consumer Packaged Goods (CPG) company".
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""


reranker_template = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an AI assistant expert specializing in understanding of the promotion, financial and PPA (Price Pack Architecture) data, particularly for a CPG (Consumer Packaged Goods) company.
    |eot_id|><|start_header_id|>user<|end_header_id|>
    You will be given a record and document. Your task is to rate the relevance of the given document against the record by using your immense promotion, financial and PPA knowledge to thoroughly understand both the document and record and see how closely the document matches semantically and syntactically (keyword match) with the given record and rate it on a scale of 1 to 100.
    Consider the specific context and intent of the explanation provided in the record, not just keyword matches. Provide a higher score if the extent of keyword match is higher.
    Record: {record}
    document: {doc}

    Respond in the format {{"relevance_score": score}}. Do not use variables.

    {{
        "title": "Rating",
        "description": "Rating the record",
        "type": "object",
        "properties": {{
            "relevance_score": {{
                "type": "float",
                "description": "The relevance score of a record to a query.",
            }}
        }}
    }}
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""


resolver_template = """
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an AI assistant expert specializing in understanding of the promotion, financial and PPA (Price Pack Architecture) data, particularly for a CPG (Consumer Packaged Goods) company.
|eot_id|><|start_header_id|>user<|end_header_id|>
You will be given a record and a list of documents which was given the same relevance score. Your task is to use your immense PPA knowledge to thoroughly understand all the documents and record and perform the differentiation among all of them by assigning a higher score to the most relevant document. Similarly, the least relevant document should be assigned the lowest score and rest of the document score should lie in this range (between highest and lowest score). Remember scores should lie in between 0 to 100. Provide a higher score if the extent of keyword match is higher.
record: {record}
documents: {doc}

Respond in the format given below. Make sure it's JSON compatible and syntactically correct. Do not use variables.

{{
    "Docs":[
        {{
            "document": complete document 1 as it is
            "score": relevence score for document 1
        }},
        {{
            "document": complete document 2 as it is
            "score": relevence score for document 2
        }}
    ]
}}

Do not write an introduction, summary or explanation.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

# classifier_template = """
#     You are an expert in examining the given set of documents and determining the best match document and the potential match documents based on the specific context and semantic meaning of the query. Make sure to provide only one best match document.

#     |eot_id|><|start_header_id|>user<|end_header_id|>

#     Query: {query}
#     Document: {documents}

#     Respond in the format given below. Do not use variables.
#     {{
#         "best_match": {{
#             "metadata": metadata for best match document
#             "page_content": page content for best match document
#         }},
#         "potential_match": [
#             {{
#                 "metadata": metadata for potential match document 1,
#                 "page_content": page content for potential match document 1
#             }},
#             {{
#                 "metadata": metadata for potential match document 2,
#                 "page_content": page content for potential match document 2
#             }}
#         ]
#     }}

#     Respond only with valid JSON. Do not write an introduction or summary.
#     <|eot_id|><|start_header_id|>assistant<|end_header_id|>
#     """
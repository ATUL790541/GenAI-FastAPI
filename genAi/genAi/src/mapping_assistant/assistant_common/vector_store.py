import os
from langchain_databricks import DatabricksEmbeddings
import pickle
from langchain.retrievers import EnsembleRetriever
import json
import pandas as pd
import asyncio
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS

# Initialize Embeddings generation technique


os.environ["DATABRICKS_HOST"] = "https://adb-6926527074777965.5.azuredatabricks.net"

os.environ["DATABRICKS_TOKEN"] = "dapi477662799536f4c6227fc9ba317d49f8-3"

embeddings = DatabricksEmbeddings(
    endpoint="databricks-gte-large-en",
    # Specify parameters for embedding queries and documents if needed
    # query_params={...},
    # document_params={...},
)

# Lance

# Load the dataset using Lance's Arrow-compatible interface
# file_path = "/home/ec2-user/Pepsico_Hackathon/Pepsico_Main_Hackathon/pepsico_mapping_assistant_in_memory_lance/output_mappings/lance_with_vec/side_by_side_mapping.lance"


# lance_vec_ds.to_table().to_pandas().head(5)


# async def generate_embeddings(text):
#     response = embeddings.embed_query(text)
#     return response

# async def similarty_search(lance_dataset,query):
#     query_embeddings = await generate_embeddings(query)
#     similar_recs = lance_dataset.to_table(
#         nearest={
#             "column": "combined_vector",
#             "k": 3,
#             "q": query_embeddings,
#             "nprobes": 20,
#             "refine_factor": 100
#         }).to_pandas()

#     return similar_recs
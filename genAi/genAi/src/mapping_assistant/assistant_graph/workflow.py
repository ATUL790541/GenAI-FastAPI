from langgraph.graph import END, StateGraph, START
from mapping_assistant.assistant_common.state import GraphState
from mapping_assistant.assistant_graph.nodes import create_and_retrieve,rerank_documents,rewrite_query
import os

workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("create_and_retrieve", create_and_retrieve)  # retrieve
# workflow.add_node("classifier", classifier)  # grade documents
# workflow.add_node("generate", generate)  # generatae
workflow.add_node("reranker", rerank_documents)  # transform_query
workflow.add_node("query_expander", rewrite_query)  # web search

# Build graph
workflow.add_edge(START, "query_expander")
workflow.add_edge("query_expander", "create_and_retrieve")
workflow.add_edge("create_and_retrieve", "reranker")
# workflow.add_edge("reranker", "classifier")

workflow.add_edge("reranker", END)

# Compile
app = workflow.compile()

current_dir = os.path.dirname(__file__)
graph_path = os.path.join(current_dir, 'graph.png')
app.get_graph().draw_mermaid_png(output_file_path=graph_path)
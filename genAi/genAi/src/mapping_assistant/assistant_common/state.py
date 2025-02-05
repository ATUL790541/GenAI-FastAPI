from typing import List,Dict

from typing_extensions import TypedDict


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        records: list of dataframe records
    """

    question: str
    generation: str
    expanded_columns: List[str]
    relevent_expanded_queries: List[str]
    ranked_records: List[str]
    accepted_list_version: Dict[str,str]
    rejected_list_version: Dict[str,str]
    source_type: str
    source_desc: str

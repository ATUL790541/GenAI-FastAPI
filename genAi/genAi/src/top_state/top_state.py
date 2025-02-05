from typing_extensions import TypedDict
from typing import Annotated, List, Union, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import operator

class TopState(TypedDict):
    input: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str
    schema_info:List[dict]
    structured_file_paths: dict
    file_path:List[dict[str, dict[str, str]]]
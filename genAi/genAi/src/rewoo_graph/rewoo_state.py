from typing import Annotated, TypedDict, Union, Sequence, List
from langchain_core.messages import BaseMessage
import operator

class ReWOO(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    input: str
    plan_string: str
    steps: List
    results: dict
    result: str
    count: int
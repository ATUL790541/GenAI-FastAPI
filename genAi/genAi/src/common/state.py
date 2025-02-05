import operator
from typing import Annotated, TypedDict, Union, Sequence, List
from langchain_core.messages import BaseMessage
from langchain_core.agents import AgentAction, AgentFinish


class AgentState(TypedDict):
    input: str
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str
    schema_info:str
    user_feedback:str
    file_path:List[dict[str, dict[str, str]]]


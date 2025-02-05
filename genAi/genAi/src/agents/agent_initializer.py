from dotenv import load_dotenv
import os,sys
import importlib.util

current_dir = os.path.dirname(os.path.dirname(__file__))
custom_langchain_path = os.path.join(current_dir, 'custom_lib', 'langchain')

# Paths for your custom files
react_agent_path = os.path.join(custom_langchain_path, 'agents', 'react', 'agent.py')

# Add the modified files to sys.path before importing
if react_agent_path not in sys.path:
    sys.path.insert(0, react_agent_path)

# Import the modified react_single_input module second
spec_react_agent = importlib.util.spec_from_file_location(
    "langchain.agents.react.agent",
    react_agent_path
)
react_single_input = importlib.util.module_from_spec(spec_react_agent)
spec_react_agent.loader.exec_module(react_single_input)

# Now you can import the specific components you need
create_react_agent = getattr(react_single_input, "create_react_agent")


# from langchain.agents import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from tools.tools import (
    infer_schema_tool
)
from common.llm import get_llm, get_bigger_llm
from common.prompts import (

    orchestrator_prompt,
    infer_schema_agent_prompt
)
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Sequence, Optional
from utilities.helper_methods_agent import create_team_supervisor
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, model_validator

load_dotenv()

# Supervisor Agent

members = ["infer_schema"]

supervisor_chain = create_team_supervisor(
    get_llm(),
    orchestrator_prompt,
    members
)

# Define the schema for nested objects with optional row_index and descriptions
class HeaderRow(BaseModel):
    """TO identify the header row"""
    is_present: str = Field(alias="is_present", description="Indicates if the header row is present (YES/NO).")
    row_index: Optional[int] = Field(
        None, alias="row_index", description="The index of the header row, or None if not applicable."
    )

class Dividers(BaseModel):
    """TO identify the dividers"""

    is_present: str = Field(alias="is_present", description="Indicates if dividers are present (YES/NO).")
    row_index: Optional[List[int]] = Field(
        default_factory=list, alias="row_index", description="List of indices where dividers are found, or None if not applicable."
    )

class Anchors(BaseModel):
    """TO identify the anchors"""

    is_present: str = Field(..., alias="is_present", description="Indicates if anchors are present (YES/NO).")
    row_index: Optional[List[int]] = Field(
        default_factory=list, alias="row_index", description="List of indices where anchors are found, or None if not applicable."
    )

class CommentsOrOtherData(BaseModel):
    """To identify the comments"""
    is_present: str = Field(..., alias="is_present", description="Indicates if comments or other data are present (YES/NO).")
    row_index: Optional[List[int]] = Field(
        default_factory=list, alias="row_index", description="List of indices for comments or other data, or None if not applicable."
    )

class ReoccuringHeaderRow(BaseModel):
    """TO identify whether header row is reccurring or not"""

    is_present: str = Field(..., alias="is_present", description="Indicates if recurring/similar header rows are present (YES/NO).")
    row_index: Optional[List[int]] = Field(
        default_factory=list, alias="row_index", description="List of indices for recurring header rows, or None if not applicable."
    )

class Table(BaseModel):
    """Information about horizontal tables"""

    Table_Name: str = Field(..., alias="Table_Name", description="The name of the table.")

class RepetitiveHorizontalTables(BaseModel):
    """TO identify the presence of repetitive horizontal tables."""

    is_present: str = Field(..., alias="is_present", description="Indicates if repetitive horizontal tables are present (YES/NO).")
    Tables: Optional[List[Table]] = Field(
        default_factory=list, alias="Tables", description="List of tables, each with a name, or None if no tables are present."
    )

# Main schema for the entire JSON structure with descriptions
class InferSchema(BaseModel):
    """Inferring the schema based on the input data."""
    column_list: List[str] = Field(
        alias="Column List", description="List of column names present in the data."
    )
    header_row: HeaderRow = Field(
        alias="Header Row", description="Information about the header row, including presence and row index."
    )
    dividers: Dividers = Field(
        alias="Dividers", description="Information about dividers, including presence and row indices."
    )
    anchors: Anchors = Field(
        alias="Anchors", description="Information about anchors, including presence and row indices."
    )
    comments_or_other_data: CommentsOrOtherData = Field(
        alias="Comments or other data", description="Details about comments or other data, including presence and row indices."
    )
    reccuring_header_row: ReoccuringHeaderRow = Field(
        alias="Reccuring/Similar header row", description="Details about recurring/similar header rows."
    )
    repetitive_horizontal_tables: RepetitiveHorizontalTables = Field(
        alias="Repetitive horizontal tables", description="Details about repetitive horizontal tables, including table names."
    )

class ListSchema(BaseModel):
    """List of inferred schemas."""
    Schemas: List[InferSchema]

# Set up a parser + inject instructions into the prompt template.
parser = PydanticOutputParser(pydantic_object=ListSchema)

infer_schema_chat_prompt = PromptTemplate(
        template=infer_schema_agent_prompt,
        input_variables=["dataframe"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
infer_schema_tool_list = [
    infer_schema_tool
]


# llm = get_llm()
bigger_llm = get_bigger_llm()

# Initialization
# infer_schema_agent = create_react_agent(llm, infer_schema_tool_list, infer_schema_chat_prompt)
infer_schema_agent = create_react_agent(bigger_llm, infer_schema_tool_list, infer_schema_chat_prompt)




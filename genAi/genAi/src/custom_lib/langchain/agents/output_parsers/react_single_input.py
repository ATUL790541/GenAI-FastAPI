import re
from typing import Union

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException

from langchain.agents.agent import AgentOutputParser
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS

# from langchain.agents.output_parsers.infer_schema_output_parser import parser

from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_core.output_parsers import PydanticOutputParser
import ast,json,os
import importlib.util

project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

llm_path = os.path.join(project_dir,"common","llm.py")
spec_llm = importlib.util.spec_from_file_location(
    "llama",
    llm_path
)
llama_llm_module = importlib.util.module_from_spec(spec_llm)
spec_llm.loader.exec_module(llama_llm_module)

# Now you can import the specific components you need
llama_llm = getattr(llama_llm_module, "get_llm")


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
custom_parser = PydanticOutputParser(pydantic_object=ListSchema)

print(custom_parser)

FINAL_ANSWER_ACTION = "Final Answer:"
MISSING_ACTION_AFTER_THOUGHT_ERROR_MESSAGE = (
    "Invalid Format: Missing 'Action:' after 'Thought:"
)
MISSING_ACTION_INPUT_AFTER_ACTION_ERROR_MESSAGE = (
    "Invalid Format: Missing 'Action Input:' after 'Action:'"
)
FINAL_ANSWER_AND_PARSABLE_ACTION_ERROR_MESSAGE = (
    "Parsing LLM output produced both a final answer and a parse-able action:"
)


class ReActSingleInputOutputParser(AgentOutputParser):
    """Parses ReAct-style LLM calls that have a single tool input.

    Expects output to be in one of two formats.

    If the output signals that an action should be taken,
    should be in the below format. This will result in an AgentAction
    being returned.

    ```
    Thought: agent thought here
    Action: search
    Action Input: what is the temperature in SF?
    ```

    If the output signals that a final answer should be given,
    should be in the below format. This will result in an AgentFinish
    being returned.

    ```
    Thought: agent thought here
    Final Answer: The temperature is 100 degrees
    ```

    """
    print("HI")
    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS
    print("HI after format instructions")

    def parse(self, text: str):
        print("Inside parse")
        includes_answer = FINAL_ANSWER_ACTION in text
        regex = (
            r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        )
        action_match = re.search(regex, text, re.DOTALL)
        if action_match:
            if includes_answer:
                raise OutputParserException(
                    f"{FINAL_ANSWER_AND_PARSABLE_ACTION_ERROR_MESSAGE}: {text}"
                )
            action = action_match.group(1).strip()
            action_input = action_match.group(2)
            tool_input = action_input.strip(" ")
            tool_input = tool_input.strip('"')

            return AgentAction(action, tool_input, text)

        elif includes_answer:
            return AgentFinish(
                {"output": text.split(FINAL_ANSWER_ACTION)[-1].strip()}, text
            )

        else:
            print("HI")

            pattern = r"<json>(.*?)</json>"

            # Find all matches
            try:
                matches = re.findall(pattern, text, re.DOTALL)
                text = matches[0]
                # print(text)
                text = text.replace("null","None")

                eval_text = ast.literal_eval(text)

                if next(iter(eval_text)) != "Schemas":

                    eval_text_modified = {
                        "Schemas": eval_text
                    }
                else:
                    eval_text_modified = eval_text

            except:

                json_text = llama_llm().invoke(f"""
                <|begin_of_text|><|start_header_id|>system<|end_header_id|>

                You are a json expert whose sole responsibility is to format the given input into a valid JSON. Make sure to wrap the output strictly in <json> and </json> tags.
                <|eot_id|><|start_header_id|>user<|end_header_id|>
                input: {text}
                Respond only with Valid JSON""").content

                matches = re.findall(pattern, json_text, re.DOTALL)
                json_text = matches[0]
                print(json_text)
                eval_text = ast.literal_eval(json_text)
                # THat means tags are absent
                # eval_text = ast.literal_eval(text)


                # eval_text = json.loads(text)

                if next(iter(eval_text)) != "Schemas":

                    eval_text_modified = {
                        "Schemas": eval_text
                    }
                else:
                    eval_text_modified = eval_text

            # if isinstance(eval_text_modified, dict):

            #     final_schema = [eval_text_modified]

            # result = ListSchema.model_validate(final_schema)

            result = ListSchema.model_validate(eval_text_modified)

            schema_info = result.model_dump_json(by_alias=True)

            # parsed_output = custom_parser.invoke(text)
            print("Parser was called")
            # schema_info = str(parsed_output.dict())
            return AgentFinish(
                {"output": schema_info}, schema_info
            )
        # if not re.search(r"Action\s*\d*\s*:[\s]*(.*?)", text, re.DOTALL):
        #     raise OutputParserException(
        #         f"Could not parse LLM output: `{text}`",
        #         observation=MISSING_ACTION_AFTER_THOUGHT_ERROR_MESSAGE,
        #         llm_output=text,
        #         send_to_llm=True,
        #     )
        # elif not re.search(
        #     r"[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)", text, re.DOTALL
        # ):
        #     raise OutputParserException(
        #         f"Could not parse LLM output: `{text}`",
        #         observation=MISSING_ACTION_INPUT_AFTER_ACTION_ERROR_MESSAGE,
        #         llm_output=text,
        #         send_to_llm=True,
        #     )
        # else:
        #     raise OutputParserException(f"Could not parse LLM output: `{text}`")

    @property
    def _type(self) -> str:
        return "react-single-input"

import os
import importlib.util

project_dir = os.path.dirname(os.path.dirname(__file__))

llm_path = os.path.join(project_dir,"common","llm.py")
spec_llm = importlib.util.spec_from_file_location(
    "llama",
    llm_path
)
llama_llm_module = importlib.util.module_from_spec(spec_llm)
spec_llm.loader.exec_module(llama_llm_module)

# Now you can import the specific components you need
llama_llm = getattr(llama_llm_module, "get_llm")
import re,ast
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, model_validator
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

llm = llama_llm()
from langchain_core.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=Resolver)

# resolver_response = """{\n    "Docs":[\n        {\n            "document": {"Event_Timeline": "Event Timeline: A chronological record of promotional events and activities, including start and end dates, to track and analyze the effectiveness of pricing strategies and trade promotions."},\n            "score": 20\n        },\n        {\n            "document": {"PPG": "PPG - Promo Product Group, grain of product at which promotions are run, typically a combination of Brand and Size."},\n            "score": 40\n        },\n        {\n            "document": {"AD RETAIL": "AD RETAIL - Retailer\\\'s advertised price for a product, often used as a reference point for promotional pricing and trade spend analysis."},\n            "score": 60\n        }\n    ]\n}"""

# pattern = r"<json>(.*?)</json>"

# json_response = llm.invoke(f"""
#     <|begin_of_text|><|start_header_id|>system<|end_header_id|>

#     You are a json expert whose sole responsibility is to format the given input into a valid JSON. Make sure to wrap the output strictly in <json> and </json> tags.
#     <|eot_id|><|start_header_id|>user<|end_header_id|>
#     input: {resolver_response}
#     Respond only with Valid JSON""")

# json_text = json_response.content
# matches = re.findall(pattern, json_text, re.DOTALL)
# json_text = matches[0]
# print(json_text)
# eval_text = ast.literal_eval(json_text)

# result = Resolver.model_validate(eval_text)
# formatted_result = result.model_dump()["Docs"]
# print(formatted_result)


pattern = r"<json>(.*?)</json>"
inputs = """{"Docs":[
                    {
                        "document": '{"TM $": "Retailer margin amount per unit of quantity sold"}',
                        "score": 0
                    },
                    {
                        "document": '{"PA": "PA - Promotional allowance. Price reductions that customers (retailers) sometimes receive as incentives to display and feature specific items."}',
                        "score": 0
                    },
                    {
                        "document": '{"TM%": "Retailer Margin"}',
                        "score": 0
                    }
                ]
            }"""

json_response = llm.invoke(f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are a json expert whose sole responsibility is to format the given input into a valid JSON. Make sure to wrap the output strictly in <json> and </json> tags.

    Output format to be followed:

    {parser.get_format_instructions()}

    <|eot_id|><|start_header_id|>user<|end_header_id|>
    input: {inputs}
    Respond only with Valid JSON""")

json_text = json_response.content
matches = re.findall(pattern, json_text, re.DOTALL)
json_text = matches[0]
print(json_text)
eval_text = ast.literal_eval(json_text)

result = Resolver.model_validate(eval_text)
formatted_result = result.model_dump()["Docs"]

print(formatted_result)
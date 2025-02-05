from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.messages import HumanMessage
import pandas as pd
import json
from langchain_databricks import ChatDatabricks
from langchain_core.output_parsers import JsonOutputParser


def create_team_supervisor(llm: ChatDatabricks, system_prompt, members) -> str:
    """An LLM-based router."""
    options = ["FINISH"] + members
    llama_prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

    Cutting Knowledge Date: December 2023
    Today Date: 23 July 2024

    When you receive a tool call response, use the output to format an answer to the orginal user question.

    {system_prompt}
    The first character in your response should be **{{**.
    <|eot_id|><|start_header_id|>user<|end_header_id|>

    Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.

    Respond in the format {{"next": argument value}}. Do not use variables.

        {{
            "type": "function",
            "function": {{
                "name": "route",
                "description": "Select the next role.",
                "parameters": {{
                    "title": "routeSchema",
                    "type": "object",
                    "properties": {{"next": {{"title": "Next", "anyOf": [{{"enum": {options}}}]}},
                    "required": ["next"],
                }},
            }},
        }},
    {messages}
    Question: Given the conversation above, who should act next? Or should we FINISH? Select one of: "{option_list}"?
    Respond only with valid JSON. Do not write an introduction or summary.
    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """

    system_prompt = system_prompt.format(team_members = ", ".join(members))

    #llama_prompt = llama_prompt
    chat_prompt=ChatPromptTemplate.from_template(llama_prompt)
    chat_prompt = chat_prompt.partial(system_prompt = system_prompt, options = str(options), option_list= str(options))
    chain = chat_prompt | llm
    return chain






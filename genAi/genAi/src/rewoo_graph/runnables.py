import re

from langchain_core.prompts import ChatPromptTemplate
from common.llm import get_llm
from rewoo_graph.prompt import *
# Regex to match expressions of the form E#... = ...[...]
regex_pattern = r"Plan:\s*(.+?)\s*(#E\d+)\s*=\s\*?\*?(\w+)\*?\*?\[([^\]]+)\]"
prompt_template = ChatPromptTemplate.from_messages([("user", planner_prompt)])
planner = prompt_template | get_llm()

import json,os
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from langchain.agents import initialize_agent, load_tools
import tiktoken
from langchain_databricks import ChatDatabricks
load_dotenv()

current_dir = os.path.dirname(os.path.dirname(__file__))
config_path = os.path.join(current_dir, 'config','config.json')

config = json.load(open(config_path))


def get_llm():

    os.environ["DATABRICKS_HOST"] = config["LLAMA"]["DATABRICKS_HOST"]
    os.environ["DATABRICKS_TOKEN"] = config["LLAMA"]["DATABRICKS_TOKEN"]
    llm = ChatDatabricks(
        endpoint = config["LLAMA"]["ENDPOINT"],
        max_tokens=config["LLAMA"]["max_tokens"],
        temperature=config["LLAMA"]["temperature"],
    )
    return llm

def get_bigger_llm():

    os.environ["DATABRICKS_HOST"] = config["LLAMA_405B"]["DATABRICKS_HOST"]
    os.environ["DATABRICKS_TOKEN"] = config["LLAMA_405B"]["DATABRICKS_TOKEN"]
    llm = ChatDatabricks(
        endpoint = config["LLAMA_405B"]["ENDPOINT"],
        max_tokens=config["LLAMA_405B"]["max_tokens"],
        temperature=config["LLAMA_405B"]["temperature"],
    )
    return llm

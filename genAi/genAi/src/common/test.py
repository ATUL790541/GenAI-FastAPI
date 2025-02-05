import json,os
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from langchain.agents import initialize_agent, load_tools
import tiktoken
load_dotenv()

current_dir = os.path.dirname(os.path.dirname(__file__))
config_path = os.path.join(current_dir, 'config','config.json')

config = json.load(open(config_path))

print(config_path)



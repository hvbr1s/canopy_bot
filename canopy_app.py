import os
import openai
from dotenv import main
import json
import jsonpatch
from canopy.tokenizer import Tokenizer
from canopy.knowledge_base import KnowledgeBase
from canopy.context_engine import ContextEngine
from canopy.models.data_models import Query
from canopy.chat_engine import ChatEngine
from canopy.models.data_models import UserMessage

# Initialize environment variables
main.load_dotenv()

# import variables]
openai.api_key=os.environ['OPENAI_API_KEY']
os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY") 
os.environ["PINECONE_ENVIRONMENT"] = os.getenv("PINECONE_ENVIRONMENT") 
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# initialize tokenizer
Tokenizer.initialize()
tokenizer = Tokenizer()
tokenizer.tokenize("Hello world!")


# connect to knowledge base
kb = KnowledgeBase(index_name="canopy--canopybot")
kb.connect()
kb.verify_index_connection()

# create context engine
context_engine = ContextEngine(kb)

# Create context engine
chat_engine = ChatEngine(context_engine)

# Start chatting
response = chat_engine.chat(messages=[UserMessage(content="who are you?")], stream=False)
print(response.choices[0].message.content)






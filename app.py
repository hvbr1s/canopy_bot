import os
import json
from dotenv import main
from datetime import datetime
import pinecone
import openai
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, parse_obj_as
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import BackgroundTasks
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from nostril import nonsense
import tiktoken
import re
import time
import jsonpatch
from canopy.tokenizer import Tokenizer
from canopy.knowledge_base import KnowledgeBase
from canopy.context_engine import ContextEngine
from canopy.models.data_models import Query
from canopy.chat_engine import ChatEngine
from canopy.models.data_models import UserMessage
from typing import Tuple
from canopy.models.data_models import Messages, UserMessage, AssistantMessage
from IPython.display import display, Markdown

# Initialize environment variables
main.load_dotenv()

# Initialize backend
server_api_key=os.environ['BACKEND_API_KEY'] 
API_KEY_NAME=os.environ['API_KEY_NAME'] 
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if not api_key_header or api_key_header.split(' ')[1] != server_api_key:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return api_key_header

# initialize tokenizer
Tokenizer.initialize()
tokenizer = Tokenizer()

# connect to knowledge base
kb = KnowledgeBase(index_name="canopy--canopybot",
                   )
kb.connect()
kb.verify_index_connection()

# create context engine
context_engine = ContextEngine(kb)



# Define query class
class Question(BaseModel):
    user_input: str
    user_id: str
    user_locale: str | None = None

# Initialize Pinecone
openai.api_key=os.environ['OPENAI_API_KEY']
os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY") 
os.environ["PINECONE_ENVIRONMENT"] = os.getenv("PINECONE_ENVIRONMENT") 
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Email address detector
email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
def find_emails(text):  
    return re.findall(email_pattern, text)

# Set up address filters:
ETHEREUM_ADDRESS_PATTERN = r'\b0x[a-fA-F0-9]{40}\b'
BITCOIN_ADDRESS_PATTERN = r'\b(1|3)[1-9A-HJ-NP-Za-km-z]{25,34}\b|bc1[a-zA-Z0-9]{25,90}\b'
LITECOIN_ADDRESS_PATTERN = r'\b(L|M)[a-km-zA-HJ-NP-Z1-9]{26,34}\b'
DOGECOIN_ADDRESS_PATTERN = r'\bD{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}\b'
XRP_ADDRESS_PATTERN = r'\br[a-zA-Z0-9]{24,34}\b'
COSMOS_ADDRESS_PATTERN = r'\bcosmos[0-9a-z]{38,45}\b'
SOLANA_ADDRESS_PATTERN= r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'

async def get_user_id(request: Request):
    try:
        body = await parse_obj_as(Question, request.json())
        user_id = body.user_id
        return user_id
    except Exception as e:
        return get_remote_address(request)

# Define FastAPI app
app = FastAPI()

# Define limiter
limiter = Limiter(key_func=get_user_id)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests, please try again in a minute."},
    )

# Initialize user state and periodic cleanup function
user_states = {}
TIMEOUT_SECONDS = 1 * 60 * 60  # 1 hours

def periodic_cleanup(background_tasks: BackgroundTasks):
    while True:
        cleanup_expired_states()
        time.sleep(TIMEOUT_SECONDS)

# Invoke periodic cleanup
@app.on_event("startup")
async def startup_event():
    background_tasks = BackgroundTasks()
    background_tasks.add_task(periodic_cleanup)

# Handle cleanup crashes gracefully
def cleanup_expired_states():
    try:
        current_time = time.time()
        expired_users = [
            user_id for user_id, state in user_states.items()
            if current_time - state['timestamp'] > TIMEOUT_SECONDS
        ]
        for user_id in expired_users:
            del user_states[user_id]
    except Exception as e:
        print(f"Error during cleanup: {e}")


# Define FastAPI endpoints
@app.get("/")
async def root():
    return {"welcome": "You've reached the home route!"}

# Define server health probe
@app.get("/_health")
async def health_check():
    return {"status": "OK"}

# Define exception handler function
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Snap! Something went wrong, please try again!"},
    )

# Define supported locales for data retrieval
SUPPORTED_LOCALES = {'eng', 'fr'}

# Define RAG route
@app.post('/gpt')
@limiter.limit("100/minute")
async def react_description(query: Question, request: Request, api_key: str = Depends(get_api_key)):
    user_id = query.user_id
    user_input = query.user_input.strip()
    locale = query.user_locale if query.user_locale in SUPPORTED_LOCALES else "eng"
    
    # Check if the user is already in user_states, if not, initialize their state
    if user_id not in user_states:
        user_states[user_id] = {
            'previous_queries': [],  # This will store the chat history
            'timestamp': time.time()
        }

    # Retrieve the user's chat history
    history = user_states[user_id]['previous_queries']

    # Load system prompt
    def load_sysprompt(locale):
            filename = f'system_prompt_{locale}.txt'
            try:
                with open(filename, 'r') as sys_file:
                    return sys_file.read()
            except FileNotFoundError:
                raise HTTPException(status_code=500, detail=f"System primer file for {locale} not found")
    primer = load_sysprompt(locale)

    # Create context engine
    chat_engine = ChatEngine(context_engine,
                            system_prompt=primer,
                            min_history_messages= 2,
                            history_pruning="raise",
                            )
    
    def load_categories():
        filename = f'classifier_prompt.txt'
        try:
            with open(filename, 'r') as categories:
                return categories.read()
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"Categories not found!")
        
    classifier_prompt = load_categories()

    if user_id not in user_states:
        user_states[user_id] = {
            'previous_queries': [],
            'timestamp': time.time()
        }

    if not user_input or nonsense(user_input):
        print('Nonsense detected!')
        if locale == "fr":
            return {'output': "Je suis désolé, je ne peux pas comprendre votre question et je ne peux pas aider avec des questions qui incluent des adresses de cryptomonnaie. Pourriez-vous s'il vous plaît fournir plus de détails ou reformuler sans l'adresse ? N'oubliez pas, je suis ici pour aider avec toute demande liée à Ledger."}
        else: 
            return {'output': "I'm sorry, I cannot understand your question, and I can't assist with questions that include cryptocurrency addresses. Could you please provide more details or rephrase it without the address? Remember, I'm here to help with any Ledger-related inquiries."}
  

    if re.search(ETHEREUM_ADDRESS_PATTERN, user_input, re.IGNORECASE) or \
           re.search(BITCOIN_ADDRESS_PATTERN, user_input, re.IGNORECASE) or \
           re.search(LITECOIN_ADDRESS_PATTERN, user_input, re.IGNORECASE) or \
           re.search(DOGECOIN_ADDRESS_PATTERN, user_input, re.IGNORECASE) or \
           re.search(COSMOS_ADDRESS_PATTERN, user_input, re.IGNORECASE) or \
           re.search(SOLANA_ADDRESS_PATTERN, user_input, re.IGNORECASE) or \
           re.search(XRP_ADDRESS_PATTERN, user_input, re.IGNORECASE):
        if locale == 'fr':
            return {'output': "Je suis désolé, mais je ne peux pas aider avec des questions qui incluent des adresses de cryptomonnaie. Veuillez retirer l'adresse et poser la question à nouveau."}
        else:
            return {'output':"I'm sorry, but I can't assist with questions that include cryptocurrency addresses. Please remove the address and ask again"}
    
    if re.search(email_pattern, user_input):
        if locale == 'fr':
            return {
            'output': "Je suis désolé, mais je ne peux pas aider avec des questions qui incluent des adresses e-mail. Veuillez retirer l'adresse et poser la question à nouveau."
                }
        else:
            return{
                'output': "I'm sorry, but I can't assist with questions that include email addresses. Please remove the address and ask again."
            }
    
    else:
        
        try:

            # # Categorize ticket
            # async def categ(user_input, contexts=None):
            #     print("Categorizing...")
            #     try:
            #         resp = openai.ChatCompletion.create(
            #             temperature=0.0,
            #             model='gpt-3.5-turbo-1106',
            #             messages=[
            #                 {"role": "system", "content": classifier_prompt},
            #                 {"role": "user", "content": user_input}
            #             ],
            #             request_timeout=5.0,
            #             max_tokens=50,
            #         )            
            #         cat = resp['choices'][0]['message']['content']
            #         return cat
            #     except Exception as e:
            #         print(f"An error occurred: {e}")
            #         return ""
            # # Use the categorization function to handle errors
            # try:
            #     categorization = await categ(user_input)
            # except Exception:
            #     categorization = ""

            # if categorization == "":
            #     print("Snap something went wrong and I wasn't able to categorize!")
            # else:
            #     print("\n\n" + "The issue seems to be about -> " + categorization + "\n\n")
            
            result = context_engine.query([Query(text=user_input, namespace="eng", top_k=5)], max_context_tokens=512)
            print(result.to_text(indent=2))
            
            def chat(new_message: str, history: Messages) -> Tuple[str, Messages]:
                    messages = history + [UserMessage(content=new_message)]
                    response = chat_engine.chat(messages)
                    assistant_response = response.choices[0].message.content

                    updated_history = messages + [AssistantMessage(content=assistant_response)]

                    # Prune history to keep the last 4 messages from the user and last 4 from the assistant
                    pruned_history = updated_history[-8:]  # Assuming alternating messages between user and assistant

                    return assistant_response, pruned_history
                
            response, history = chat(user_input, history)
            display(Markdown(response))

            # Update the user's state with the pruned history
            user_states[user_id]['previous_queries'] = history
            user_states[user_id]['timestamp'] = time.time()
            print(user_states)

               
            print("\n\n" + response + "\n\n")
            return {'output': response}
    
        except ValueError as e:
            print(e)
            raise HTTPException(status_code=400, detail="Snap! Something went wrong, please try again!")
        
        except HTTPException as e:
            print(e)
            # Handle known HTTP exceptions
            return JSONResponse(
                status_code=e.status_code,
                content={"message": e.detail},
            )
        except Exception as e:
            print(e)
            # Handle other unexpected exceptions
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Snap! Something went wrong, please try again!"},
            )

# Local start command: uvicorn app:app --reload --port 8800
# to change system_prompt -> lib/python3.10/site-packages/canopy/chat_engine/query_generator/function_calling.py
# to change the llm model -> lib/python3.10/site-packages/canopy/llm/models.py
# to change the namespace -> lib/python3.10/site-packages/canopy/knowledge_base/knowledge_base.py

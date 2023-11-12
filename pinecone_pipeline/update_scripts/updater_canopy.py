import os
import json
from dotenv import main
import openai
from canopy.tokenizer import Tokenizer
from canopy.knowledge_base import KnowledgeBase
from canopy.models.data_models import Document

# Initialize environment variables
main.load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY") 
os.environ["PINECONE_ENVIRONMENT"] = os.getenv("PINECONE_ENVIRONMENT") 
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Initialize tokenizer and knowledge base
Tokenizer.initialize()
tokenizer = Tokenizer()

index_name = "canopy--canopybot"
kb = KnowledgeBase(index_name=index_name)
kb.create_canopy_index()
kb.connect()
kb.verify_index_connection()

def read_jsonl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)

def run_updater(json_file_path):
    try:
        documents = []
        for data in read_jsonl_file(json_file_path):
            print("Reading data:", data)  # Debug print to check the data being read

            # Create a Document object from the dictionary
            doc = Document(
                id=data.get('id'),
                text=data.get('text'),
                source=data.get('source'),
                metadata=data.get('metadata', {})  # Provide an empty dict as default if metadata is missing
            )
            documents.append(doc)

            print("Created Document:", doc)  # Debug print to check the created Document object

        # Check the length of documents list
        print("Total documents to upsert:", len(documents))

        # Upsert the list of Document objects
        kb.upsert(
            documents=documents,
            namespace="eng",
            show_progress_bar=True
        )
        print('Database updated!')
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    file_path = "/home/dan/canopy/pinecone_pipeline/output_files/output.jsonl"
    run_updater(file_path)
import os
import json
import openai
import pinecone
from dotenv import load_dotenv

load_dotenv()

def init_pinecone():
    api_key = os.getenv('PINECONE_API_KEY')
    environment = os.getenv('PINECONE_ENVIRONMENT')
    
    if not api_key or not environment:
        raise EnvironmentError("Pinecone API key or environment not set")
    
    pinecone.init(api_key=api_key, environment=environment)
    return pinecone.Index('personal')

def get_embedding(link, embed_model="text-embedding-ada-002"):
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        raise EnvironmentError("OpenAI API key not set")

    openai.api_key = openai_api_key
    res_embed = openai.Embedding.create(input=[link], engine=embed_model)
    return res_embed['data'][0]['embedding']

def query_pinecone(index, xq):
    res_query = index.query(xq, top_k=1, include_metadata=True)
    match = res_query['matches'][0]
    return match['id'], match['metadata']['source']

def main():
    index = init_pinecone()

    link = 'https://www.ledger.com/academy/glossary/cross-chain'  # Set the article link to delete
    xq = get_embedding(link)
    article_id, article_title = query_pinecone(index, xq)

    print('Article to delete:', article_title)

    fetch_response = index.fetch(ids=[article_id])
    try:
        print(fetch_response['vectors'][article_id]['metadata']['source'])
    except KeyError:
        print(f'{article_id} is not part of the database or has already been deleted.')
        return

    delete_response = index.delete(ids=[article_id])
    print(delete_response)
    print(f'{article_id} was successfully deleted.')

if __name__ == "__main__":
    main()

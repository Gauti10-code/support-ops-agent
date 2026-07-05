import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore=Chroma(
  persist_directory=CHROMA_PATH,
  embedding_function=embeddings
)

def search_docs(query: str, k:int=3)-> str:
  results=vectorstore.similarity_search(query,k=k)
  if not results:
    return "No relevant information found in the policy documents"
  return "\n\n".join([doc.page_content for doc in results])
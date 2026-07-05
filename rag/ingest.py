import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policy_doc.pdf")
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")

def ingest():
  print(f"Loading PDF:{PDF_PATH}")
  loader=PyPDFLoader(PDF_PATH)
  documents=loader.load()
  print(f"Loaded {len(documents)} pages")

  splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
  chunks=splitter.split_documents(documents)
  chunks=[c for c in chunks if len(c.page_content.strip())>100]
  print(f"Split into {len(chunks)} chunks after filtering")

  embeddings=OpenAIEmbeddings(model="text-embedding-3-small")
  if os.path.exists(CHROMA_PATH) and os.listdir(CHROMA_PATH):
    print("Chroma DB already exists- skipping re-embedding")
    return
  vectorstore=Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=CHROMA_PATH
  )
  print(f"Vector store saved to {CHROMA_PATH}")

if __name__=="__main__":
  ingest()
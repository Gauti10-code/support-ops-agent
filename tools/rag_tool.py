import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.tools import tool
from rag.retriever import search_docs

@tool("search_policy_docs", description="Search the company policy and scheme documents for rules, terms, conditions, procedures, or any factual information from official documents. Use when asked about policies, scheme details, rules, or anything that would be in a document.")
def search_policy_docs(query: str) -> str:
    return search_docs(query)
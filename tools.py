import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
service_endpoint = os.getenv('service_endpoint')
key = os.getenv('key')
indexname = os.getenv('indexname')


def process_results(results):
    """Process search results into a structured format."""
    final_str = ""
    for result in results:
        chunk = result.get("chunk")
        source = result.get("title")
        if chunk and source:
            final_str += f"{source}:\n{chunk}\n\n"
    return final_str


def azure_ai_search(query):
    """Perform Azure AI Search and return formatted results."""
    search_client = SearchClient(service_endpoint, indexname, AzureKeyCredential(key))
    try:
        results = search_client.search(
            search_text=query,
            select="chunk, title",
            query_type=QueryType.SIMPLE,
            include_total_count=True,
            semantic_configuration_name="semantictest-semantic-configuration",
            top=3,
        )
        return process_results(results)
    except Exception as e:
        print(f"Error: {e}")
        return ""


async def azure_ai_search_retriever(query: str) -> str:
    """Retrieve search results from Azure AI Search."""
    return azure_ai_search(query)

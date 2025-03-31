from azure.search.documents.models import QueryType
import logging
logger = logging.getLogger(__name__) 

class AzureAISearchTool:
    def __init__(self,search_client):
        """Initialize Azure AI Search client with environment variables."""
        self.search_client = search_client



    async def format_results(self, results):
        """Format search results into a readable string."""
        final_str = ""
        for result in results:
            chunk = result.get("chunk")
            source = result.get("title")
            if chunk and source:
                final_str += f"{source}:\n{chunk}\n\n"
        return final_str


    async def azure_ai_search_retriever(self, query: str) -> str:
        """Retrieve search results from Azure AI Search."""
        try:
            results = self.search_client.search(
                search_text=query,
                select="chunk, title",
                query_type=QueryType.SIMPLE,
                include_total_count=True,
                semantic_configuration_name="semantictest-semantic-configuration",
                top=2,
            )
            return self.format_results(results)
        except Exception as e:
            logger.info(f"some error in tool")
            return "some error in tool fetching"
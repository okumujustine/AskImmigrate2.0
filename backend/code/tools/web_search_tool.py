from typing import Any, Dict, List
from urllib.parse import urlparse
import logging

import requests
from bs4 import BeautifulSoup
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def extract_source(url):
    """
    Extracts the domain name from a URL to be used as the 'source'.
    """
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "").capitalize()
    except Exception as e:
        logger.error(f"Error extracting source from URL {url}: {e}")
        return "Unknown"


def tavidy_run_search(query, k=3):
    """
    Runs a web search and formats the results to the desired mock output.
    """
    try:
        search = TavilySearchResults()
        raw_results = search.invoke(input=query, k=k)
        return format_tavidy_results(raw_results, query)
    except Exception as e:
        logger.error(f"Error performing search for query '{query}': {e}")
        return []


def format_tavidy_results(raw_results, query):
    """
    Transforms the raw Tavily search results into a structured mock format.
    """
    mock_results = []
    try:
        for result in raw_results:
            try:
                source = extract_source(result.get("url", ""))
                formatted = {
                    "title": f"{source} Guide: {query}",
                    "url": result.get("url", ""),
                    "snippet": result.get("content", "")[:200]
                    or result.get("title", ""),
                    "source": source,
                }
                mock_results.append(formatted)
            except Exception as e:
                logger.error(f"Error formatting search result: {e}")
                continue
    except Exception as e:
        logger.error(f"Error processing search results: {e}")
        return []
    return mock_results


@tool
def web_search_tool(query: str, num_results: int = 3) -> List[Dict[str, Any]]:
    """Performs a web search and returns structured results."""
    try:
        if not query or not isinstance(query, str):
            logger.error("Invalid query provided to web_search_tool")
            return []

        if not isinstance(num_results, int) or num_results <= 0:
            logger.warning(
                f"Invalid num_results: {num_results}, using default value of 3"
            )
            num_results = 3

        return tavidy_run_search(query, k=num_results)
    except Exception as e:
        logger.error(f"Error in web_search_tool: {e}")
        return []

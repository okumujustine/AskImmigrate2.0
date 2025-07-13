from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool


def extract_source(url):
    """
    Extracts the domain name from a URL to be used as the 'source'.
    """
    domain = urlparse(url).netloc
    return domain.replace("www.", "").capitalize()


def tavidy_run_search(query, k=3):
    """
    Runs a web search and formats the results to the desired mock output.
    """
    search = TavilySearchResults()
    raw_results = search.invoke(input=query, k=k)
    return format_tavidy_results(raw_results, query)


def format_tavidy_results(raw_results, query):
    """
    Transforms the raw Tavily search results into a structured mock format.
    """
    mock_results = []
    for result in raw_results:
        source = extract_source(result.get("url", ""))
        formatted = {
            "title": f"{source} Guide: {query}",
            "url": result.get("url", ""),
            "snippet": result.get("content", "")[:200] or result.get("title", ""),
            "source": source,
        }
        mock_results.append(formatted)
    return mock_results


@tool
def web_search_tool(query: str, num_results: int = 3) -> List[Dict[str, Any]]:
    return tavidy_run_search(query, k=num_results)

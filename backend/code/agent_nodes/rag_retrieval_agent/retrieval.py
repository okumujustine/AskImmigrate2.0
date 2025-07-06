from typing import Any, List

from backend.code.utils import get_collection, get_relevant_documents, initialize_chroma_db


def retrieve_documents(query: str, n_results: int, threshold: float) -> List[Any]:
    db_instance = initialize_chroma_db()
    collection = get_collection(db_instance, collection_name="publications")
    return get_relevant_documents(
        query,
        collection,
        n_results=n_results,
        threshold=threshold,
    )

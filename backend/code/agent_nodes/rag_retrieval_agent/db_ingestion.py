import chromadb

from typing import Iterable
from backend.code.utils import (
    chunk_publication,
    custom_terminal_print,
    embed_documents,
    get_collection,
    initialize_chroma_db,
    iter_all_publications,
)

def insert_publications(
    collection: chromadb.Collection,
    publications: Iterable[str],
) -> None:
     next_id = collection.count()
     batch_texts: list[str] = []

     for publication in publications:
         chunked_publication = chunk_publication(publication)
         embeddings = embed_documents(chunked_publication)
         ids = [f"document_{i}" for i in range(next_id, next_id + len(chunked_publication))]
         collection.add(
             embeddings=embeddings,  # type: ignore
             ids=ids,
             documents=chunked_publication,
         )
         next_id += len(chunked_publication)


def execute_db_ingestion():
    db_instance = initialize_chroma_db(create_new_folder=True)
    collection = get_collection(db_instance, collection_name="publications")
    custom_terminal_print("Inserting publications to documents")
    insert_publications(collection, iter_all_publications())  # generator
    custom_terminal_print(f"Total documents in collection: {collection.count()}")

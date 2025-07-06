import chromadb

from backend.code.utils import (
    chunk_publication,
    custom_terminal_print,
    embed_documents,
    get_collection,
    initialize_chroma_db,
    load_all_publications,
)



def insert_publications(collection: chromadb.Collection, publications: list[str]):
    next_id = collection.count()

    for publication in publications:
        chunked_publication = chunk_publication(publication)
        embeddings = embed_documents(chunked_publication)
        ids = list(range(next_id, next_id + len(chunked_publication)))
        ids = [f"document_{id}" for id in ids]
        collection.add(
            embeddings=embeddings,  # type: ignore
            ids=ids,
            documents=chunked_publication,
        )
        next_id += len(chunked_publication)


def execute_db_ingestion():
    db_instance = initialize_chroma_db(create_new_folder=True)
    collection = get_collection(db_instance, collection_name="publications")
    publications = load_all_publications()

    custom_terminal_print("Inserting publications to documents")
    insert_publications(collection, publications)

    custom_terminal_print(f"Total documents in collection: {collection.count()}")

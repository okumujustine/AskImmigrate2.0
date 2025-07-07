import os
import shutil
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Union

import chromadb
import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pdfminer.high_level import extract_text
from slugify import slugify

from backend.code.paths import APP_CONFIG_FPATH, DATA_DIR, VECTOR_DB_DIR
from backend.code.tools.radix_loader import build_kb, stream_nodes

_RADIX_ROOT = build_kb(Path(DATA_DIR))


@lru_cache
def get_cpu_embedder():
    """HuggingFace sentence-transformer forced onto CPU."""
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
    )


def load_config(config_path: str = APP_CONFIG_FPATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_immigration_example(example_number: int) -> str:
    """
    Load a immigration example text file.

    Args:
        example_number: The number of the example to load (1, 2, or 3)

    Returns:
        The content of the immigration example file
    """
    example_fpath = f"publication_example{example_number}.md"
    full_path = os.path.join(DATA_DIR, example_fpath)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def custom_terminal_print(message: str):
    print("." * 10, message, "." * 10)


def slugify_chat_session(s):
    print("---", s);
    return f"{slugify(s[:20])}-{uuid.uuid4().hex[:8]}"


def initialize_chroma_db(create_new_folder=False):
    custom_terminal_print("Initializing chroma db")
    if os.path.exists(VECTOR_DB_DIR) and create_new_folder:
        custom_terminal_print("Removing existing db")
        shutil.rmtree(VECTOR_DB_DIR)

    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    chroma_instance = chromadb.PersistentClient(path=VECTOR_DB_DIR)
    custom_terminal_print("Chroma db successfully initialized")
    return chroma_instance


def get_collection(db_instance, collection_name: str) -> chromadb.Collection:
    custom_terminal_print(f"Retrieving {collection_name} collection instance")
    collection = db_instance.get_or_create_collection(name=collection_name)
    custom_terminal_print(f"Retrieved {collection_name} collection instance")
    return collection


def chunk_publication(
    publication: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return text_splitter.split_text(publication)


def load_pdf_publication(pdf_file: str) -> str:
    pdf_path = Path(os.path.join(DATA_DIR, pdf_file))
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    text = extract_text(str(pdf_path))
    return text


# BEGIN (lazy generator)
def iter_all_publications(publication_dir: str = DATA_DIR) -> Iterator[str]:
    """Yield every JSON (via Radix) and PDF lazily, one at a time."""
    # JSON files already resident in Radix memory
    for _key, doc in stream_nodes(_RADIX_ROOT):
        yield f"title: {doc.get('title', '')} , url: {doc.get('url', '')} , text: {doc.get('text', '')}"
    # PDFs still come from disk on demand
    for pdf_path in Path(publication_dir).rglob("*.pdf"):
        yield load_pdf_publication(pdf_path.name)


# (optional) keep eager helper for other callers
def load_all_publications(publication_dir: str = DATA_DIR) -> list[str]:
    return list(iter_all_publications(publication_dir))


def load_yaml_config(file_path: Union[str, Path]) -> dict:
    custom_terminal_print(f"Loading config from {file_path}")
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"YAML config file not found: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            loaded_yaml = yaml.safe_load(file)
            custom_terminal_print(f"Config loaded from {file_path}")
            return loaded_yaml
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}") from e
    except IOError as e:
        raise IOError(f"Error reading YAML file: {e}") from e


def embed_documents(documents: list[str]) -> list[list[float]]:
    # use cached CPU embedder
    model = get_cpu_embedder()
    return model.embed_documents(documents)


def get_relevant_documents(
    query: str,
    collection,
    n_results: int = 5,
    threshold: float = 0.3,
) -> list[str]:
    relevant_results = {
        "ids": [],
        "documents": [],
        "distances": [],
    }

    query_embedding = embed_documents([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "distances"],
    )

    keep_item = [False] * len(results["ids"][0])
    for i, distance in enumerate(results["distances"][0]):
        if distance < threshold:
            keep_item[i] = True

    for i, keep in enumerate(keep_item):
        if keep:
            relevant_results["ids"].append(results["ids"][0][i])
            relevant_results["documents"].append(results["documents"][0][i])
            relevant_results["distances"].append(results["distances"][0][i])

    return relevant_results["documents"]

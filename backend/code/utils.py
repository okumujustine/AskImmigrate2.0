import yaml
import os
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Union

import chromadb
import torch
import yaml
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pdfminer.high_level import extract_text
from slugify import slugify

from paths import DATA_DIR, VECTOR_DB_DIR

from paths import APP_CONFIG_FPATH, DATA_DIR


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
    custom_terminal_print(f"Retriving {collection_name} collection")
    collection = db_instance.get_or_create_collection(name=collection_name)
    custom_terminal_print(f"Retrieving {collection_name} collection")
    return collection


def chunk_publication(
    publication: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return text_splitter.split_text(publication)


def load_json_publication(json_file):
    publication_fpath = Path(os.path.join(DATA_DIR, json_file))
    try:
        with publication_fpath.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Publication file not found: {publication_fpath}"
        ) from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {publication_fpath}: {e}") from e

    text = data.get("text")
    title = data.get("title")
    url = data.get("url")
    if not isinstance(text, str):
        raise ValueError(
            f"'text' field is missing or not a string in {publication_fpath}"
        )
    return f"title: {title} , url: {url} ,text : {text}"


def load_pdf_publication(pdf_file: str) -> str:
    pdf_path = Path(os.path.join(DATA_DIR, pdf_file))
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    text = extract_text(str(pdf_path))
    return text


def load_all_publications(publication_dir: str = DATA_DIR) -> list[str]:
    custom_terminal_print(f"loading publictions from {publication_dir}")
    publications = []
    for pub_id in os.listdir(publication_dir):
        if pub_id.lower().endswith(".json"):
            publications.append(load_json_publication(pub_id))
        elif pub_id.lower().endswith(".pdf"):
            publications.append(load_pdf_publication(pub_id))
    custom_terminal_print("publictions loaded")
    return publications


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
    device = (
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )
    model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={"device": device},
    )

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

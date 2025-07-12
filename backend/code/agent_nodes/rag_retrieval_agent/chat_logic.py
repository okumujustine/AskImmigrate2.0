from langchain_groq import ChatGroq

from backend.code.agent_nodes.rag_retrieval_agent.config_loader import (
    load_app_config,
    load_prompt_config,
)
from backend.code.agent_nodes.rag_retrieval_agent.chat_logger import setup_logging
from backend.code.agent_nodes.rag_retrieval_agent.memory import make_memory
from backend.code.tools.rag_prompt_utils import build_query_prompt
from backend.code.utils import get_collection, get_relevant_documents, initialize_chroma_db


def respond_to_query(llm: str, prompt: str) -> str:
    groq = ChatGroq(model=llm)
    return groq.invoke(prompt).content  # type: ignore


def chat(session_id: str, question: str) -> str:
    setup_logging()
    app_cfg = load_app_config()
    prompt_cfg = load_prompt_config()

    mem = make_memory(str(session_id))
    # Use existing utils functions for document retrieval
    db_instance = initialize_chroma_db()
    collection = get_collection(db_instance, collection_name="publications")
    docs = get_relevant_documents(
        question,
        collection,
        n_results=app_cfg["vectordb"]["n_results"],
        threshold=app_cfg["vectordb"]["threshold"],
    )

    history = mem.load_memory_variables({})["chat_history"]
    prompt = build_query_prompt(
        prompt_cfg["rag_assistant_prompt"], docs, question, history
    )
    answer = respond_to_query(app_cfg["llm"], prompt)
    mem.save_context({"question": question}, {"answer": answer})
    return answer

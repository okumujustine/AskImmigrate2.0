from backend.code.agent_nodes.rag_retrieval_agent.prompt_builder import (
    build_prompt_from_config,
)


def build_query_prompt(prompt_template, documents, question, history) -> str:
    history_block = f"Conversation so far:\n{history}\n\n" if history else ""
    docs_block = f"Relevant documents:\n\n{documents}\n\n"
    question_block = f"User's question:\n\n{question}"

    input_data = f"{history_block} {docs_block} {question_block}"

    return build_prompt_from_config(prompt_template, input_data=input_data)

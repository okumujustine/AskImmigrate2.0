from langchain_community.chat_models import ChatOllama

llm = ChatOllama(model="mistral:7b-instruct-q4_0", temperature=0.2)
response = llm.invoke("How do I change from CPT F1 to OPT?")
print(response.content)
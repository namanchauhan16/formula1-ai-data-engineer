from RAG.rag_tool import search_f1_knowledge


result = search_f1_knowledge.invoke(
    "Why is overtaking difficult at Monaco?"
)

print(result)
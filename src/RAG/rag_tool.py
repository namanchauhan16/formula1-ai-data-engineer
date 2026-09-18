from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vector_store = Chroma(
    collection_name="f1_knowledge",
    embedding_function=embeddings,
    persist_directory=str(PROJECT_ROOT / "vector_db")
)

retriever = vector_store.as_retriever(
    search_kwargs={"k": 3}
)


@tool
def search_f1_knowledge(query: str) -> str:
    """
    Search the Formula 1 knowledge base for factual and conceptual information.
    Use this tool for questions about circuits, drivers, constructors,
    F1 concepts, terminology, and other unstructured F1 knowledge.
    """

    documents = vector_store.similarity_search(
        query,
        k=3
    )

    if not documents:
        return "No relevant information was found in the F1 knowledge base."

    results = []

    for document in documents:
        source = Path(
            document.metadata["source"]
        ).name

        results.append(
            f"Source: {source}\n"
            f"Content: {document.page_content}"
        )

    return "\n\n".join(results)
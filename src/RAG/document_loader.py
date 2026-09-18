from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import TextLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_PATH = PROJECT_ROOT / "knowledge_center"

loader = DirectoryLoader(
    str(KNOWLEDGE_PATH),
    glob="*.md",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
    recursive=True
)

documents = loader.load()


embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

text_splitter = SemanticChunker(
    embeddings,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=60
)

chunks = text_splitter.split_documents(documents)

vector_store = Chroma(
    collection_name="f1_knowledge",
    embedding_function=embeddings,  
    persist_directory=str(PROJECT_ROOT / "vector_db")
)

vector_store.add_documents(chunks)
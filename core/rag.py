"""
RAG (Retrieval-Augmented Generation) system for HealthLink.
Uses Pinecone for vector search with local HuggingFace embeddings via LangChain.

Updated for:
- LangChain 1.x (requires Python 3.10+)
- langchain-huggingface (local sentence-transformers embeddings, no API key)
- Pinecone client 5.x+
"""
import json
import logging
from typing import List, Optional, Dict, Any
from time import sleep

from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import Settings
from core.schemas import Document, RetrievalResult


logger = logging.getLogger("healthlink.rag")


class EmbeddingClient:
    """Embedding client using local HuggingFace sentence-transformers (no API key)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.embedding_model_name

        # Runs locally on CPU. The model is downloaded once (or baked into the image).
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)

        logger.info(f"Embedding client initialized with local model: {self.model_name}")

    def embed_text(self, text: str, is_query: bool = True) -> List[float]:
        """
        Embed a single text. The is_query flag is kept for API compatibility;
        local sentence-transformers models use the same encoder for both.
        """
        return self.embeddings.embed_query(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts (for document indexing)."""
        return self.embeddings.embed_documents(texts)


class VectorStore:
    """Pinecone-based vector store for document retrieval."""

    def __init__(self, settings: Settings, embedding_client: EmbeddingClient):
        self.settings = settings
        self.embedding_client = embedding_client
        self.index_name = settings.pinecone_index_name

        self.pc = Pinecone(api_key=settings.pinecone_api_key)

        sample_embedding = self.embedding_client.embed_text("sample", is_query=False)
        self.dimension = len(sample_embedding)

        self.initialize_index()

        logger.info(f"Vector store initialized with Pinecone index: {self.index_name}")

    def initialize_index(self):
        """Initialize or connect to existing Pinecone index."""
        existing_indexes = [index.name for index in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"Creating new Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.settings.pinecone_environment or "us-east-1"
                )
            )
            sleep(1)

        self.index = self.pc.Index(self.index_name)
        logger.info(f"Connected to Pinecone index: {self.index_name}")

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.

        Args:
            documents: List of documents to add
        """
        if not documents:
            return

        texts = [doc.content for doc in documents]

        logger.info(f"Generating embeddings for {len(texts)} documents")
        embeddings = self.embedding_client.embed_texts(texts)

        vectors = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            vector_id = f"doc_{i}_{hash(doc.content)}"
            metadata = {
                "content": doc.content,
                **(doc.metadata or {})
            }
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata
            })

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i // batch_size + 1} ({len(batch)} vectors)")

        logger.info(f"Added {len(documents)} documents to Pinecone index")

    def search(self, query: str, k: int = 5) -> RetrievalResult:
        """
        Search for relevant documents.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            RetrievalResult with documents and scores
        """
        query_embedding = self.embedding_client.embed_text(query, is_query=True)

        search_results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True
        )

        results = []
        scores = []

        for match in search_results.matches:
            content = match.metadata.get("content", "")
            metadata = {k: v for k, v in match.metadata.items() if k != "content"}

            results.append(Document(content=content, metadata=metadata))
            scores.append(float(match.score))

        logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")

        return RetrievalResult(
            documents=results,
            scores=scores,
            query=query
        )

    def delete_all(self) -> None:
        """Delete all vectors from the index."""
        self.index.delete(delete_all=True)
        logger.info(f"Deleted all vectors from index: {self.index_name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = self.index.describe_index_stats()
        return {
            "total_vector_count": stats.total_vector_count,
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness
        }


_embedding_client: Optional[EmbeddingClient] = None
_vector_store: Optional[VectorStore] = None


def get_embedding_client(settings: Settings) -> EmbeddingClient:
    """
    FastAPI dependency for embedding client.

    Args:
        settings: Application settings

    Returns:
        Embedding client instance
    """
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient(settings)
    return _embedding_client


def get_vector_store(settings: Settings) -> VectorStore:
    """
    FastAPI dependency for vector store.

    Args:
        settings: Application settings

    Returns:
        Vector store instance
    """
    global _vector_store
    if _vector_store is None:
        embedding_client = get_embedding_client(settings)
        _vector_store = VectorStore(settings, embedding_client)
    return _vector_store


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Split text into chunks for indexing.

    Args:
        text: Text to split
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


def _coerce_kb_item_to_content(item: Dict[str, Any]) -> str:
    """
    Build a readable text blob from a knowledge-base entry.

    The bundled symptoms_kb.json uses domain-specific keys (symptom, description,
    common_causes, ...) rather than a generic 'content'/'text' field. Without this
    coercion every entry would have empty content and nothing would be indexed.
    """
    explicit = item.get("content") or item.get("text")
    if explicit:
        return str(explicit)

    parts: List[str] = []
    for key, value in item.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            value = json.dumps(value)
        label = key.replace("_", " ").title()
        parts.append(f"{label}: {value}")
    return "\n".join(parts)


def _sanitize_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reduce a KB entry to Pinecone-safe metadata.

    Pinecone only accepts str, int, float, bool, or list[str] values, so nested
    structures are dropped and lists are coerced to lists of strings.
    """
    safe: Dict[str, Any] = {}
    for key, value in item.items():
        if key in ("content", "text"):
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(value, (list, tuple)) and all(
            isinstance(v, (str, int, float, bool)) for v in value
        ):
            safe[key] = [str(v) for v in value]
    return safe


def load_knowledge_base(file_path: str, settings: Settings) -> None:
    """
    Load knowledge base from file and index it.

    Args:
        file_path: Path to knowledge base file (JSON)
        settings: Application settings
    """
    logger.info(f"Loading knowledge base from {file_path}")

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        documents = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    content = _coerce_kb_item_to_content(item)
                    metadata = _sanitize_metadata(item)
                else:
                    content = str(item)
                    metadata = {}

                if content:
                    chunks = chunk_text(content, settings.chunk_size, settings.chunk_overlap)
                    for chunk in chunks:
                        documents.append(Document(content=chunk, metadata=metadata))

        elif isinstance(data, dict):
            for key, value in data.items():
                content = value if isinstance(value, str) else json.dumps(value)
                documents.append(Document(
                    content=content,
                    metadata={"source": key}
                ))

        vector_store = get_vector_store(settings)
        vector_store.add_documents(documents)

        logger.info(f"Loaded {len(documents)} document chunks into vector store")

    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}", exc_info=True)
        raise


def retrieve_relevant_docs(query: str, k: int = 5, settings: Optional[Settings] = None) -> RetrievalResult:
    """
    Retrieve relevant documents for a query.

    Args:
        query: Search query
        k: Number of results
        settings: Application settings (uses global if None)

    Returns:
        RetrievalResult with documents and scores
    """
    if settings is None:
        from config.settings import get_settings
        settings = get_settings()

    vector_store = get_vector_store(settings)
    return vector_store.search(query, k)


def format_retrieval_context(retrieval_result: RetrievalResult, max_docs: int = 3) -> str:
    """
    Format retrieval results as context string for LLM.

    Args:
        retrieval_result: Retrieval results
        max_docs: Maximum documents to include

    Returns:
        Formatted context string
    """
    if not retrieval_result.documents:
        return ""

    context_parts = ["Relevant medical knowledge:"]

    for i, doc in enumerate(retrieval_result.documents[:max_docs]):
        context_parts.append(f"\n[Source {i+1}]")
        context_parts.append(doc.content)
        if doc.metadata:
            context_parts.append(f"Metadata: {json.dumps(doc.metadata)}")

    return "\n".join(context_parts)
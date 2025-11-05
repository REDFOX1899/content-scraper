"""
Vector store integration for storing and querying content embeddings.
Supports Pinecone, Weaviate, and ChromaDB.
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from loguru import logger

from config.settings import (
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    WEAVIATE_URL,
    WEAVIATE_API_KEY,
    VECTOR_STORE_CONFIG
)


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def create_index(self, index_name: str, dimension: int):
        """Create a new index."""
        pass

    @abstractmethod
    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "default"):
        """Insert or update vectors."""
        pass

    @abstractmethod
    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
        namespace: str = "default"
    ) -> List[Dict[str, Any]]:
        """Query for similar vectors."""
        pass

    @abstractmethod
    def delete(self, ids: List[str], namespace: str = "default"):
        """Delete vectors by ID."""
        pass


class PineconeVectorStore(VectorStore):
    """Pinecone vector store implementation."""

    def __init__(self, index_name: str = None):
        """Initialize Pinecone client."""
        if not PINECONE_API_KEY:
            raise ValueError("Pinecone API key not configured")

        try:
            import pinecone

            pinecone.init(
                api_key=PINECONE_API_KEY,
                environment=PINECONE_ENVIRONMENT
            )

            self.pc = pinecone
            self.index_name = index_name or VECTOR_STORE_CONFIG['index_name']
            self.index = None

            logger.info("Initialized Pinecone vector store")

        except ImportError:
            raise ImportError("pinecone-client not installed. Run: pip install pinecone-client")

    def create_index(self, index_name: str = None, dimension: int = None):
        """Create Pinecone index."""
        index_name = index_name or self.index_name
        dimension = dimension or VECTOR_STORE_CONFIG['dimension']

        try:
            # Check if index exists
            if index_name not in self.pc.list_indexes():
                self.pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=VECTOR_STORE_CONFIG['metric']
                )
                logger.info(f"Created Pinecone index: {index_name}")
            else:
                logger.info(f"Pinecone index already exists: {index_name}")

            self.index = self.pc.Index(index_name)

        except Exception as e:
            logger.error(f"Failed to create Pinecone index: {e}")
            raise

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "default"):
        """Upsert vectors to Pinecone."""
        if not self.index:
            self.create_index()

        try:
            # Format vectors for Pinecone
            # Expected format: [(id, vector, metadata), ...]
            formatted_vectors = [
                (
                    v['id'],
                    v['values'],
                    v.get('metadata', {})
                )
                for v in vectors
            ]

            self.index.upsert(vectors=formatted_vectors, namespace=namespace)
            logger.info(f"Upserted {len(vectors)} vectors to Pinecone")

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
        namespace: str = "default"
    ) -> List[Dict[str, Any]]:
        """Query Pinecone for similar vectors."""
        if not self.index:
            self.create_index()

        try:
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                filter=filter_dict,
                namespace=namespace,
                include_metadata=True
            )

            return [
                {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                }
                for match in results.matches
            ]

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

    def delete(self, ids: List[str], namespace: str = "default"):
        """Delete vectors from Pinecone."""
        if not self.index:
            self.create_index()

        try:
            self.index.delete(ids=ids, namespace=namespace)
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")


class ChromaVectorStore(VectorStore):
    """ChromaDB vector store implementation."""

    def __init__(self, collection_name: str = None, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB client."""
        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection_name = collection_name or VECTOR_STORE_CONFIG['index_name']
            self.collection = None

            logger.info("Initialized ChromaDB vector store")

        except ImportError:
            raise ImportError("chromadb not installed. Run: pip install chromadb")

    def create_index(self, index_name: str = None, dimension: int = None):
        """Create ChromaDB collection."""
        collection_name = index_name or self.collection_name

        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"dimension": dimension or VECTOR_STORE_CONFIG['dimension']}
            )
            logger.info(f"Created/loaded ChromaDB collection: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to create ChromaDB collection: {e}")
            raise

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "default"):
        """Upsert vectors to ChromaDB."""
        if not self.collection:
            self.create_index()

        try:
            ids = [v['id'] for v in vectors]
            embeddings = [v['values'] for v in vectors]
            metadatas = [v.get('metadata', {}) for v in vectors]

            # Add namespace to metadata
            for metadata in metadatas:
                metadata['namespace'] = namespace

            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )

            logger.info(f"Upserted {len(vectors)} vectors to ChromaDB")

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
        namespace: str = "default"
    ) -> List[Dict[str, Any]]:
        """Query ChromaDB for similar vectors."""
        if not self.collection:
            self.create_index()

        try:
            # Add namespace to filter
            where = filter_dict or {}
            where['namespace'] = namespace

            results = self.collection.query(
                query_embeddings=[vector],
                n_results=top_k,
                where=where if where else None
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        'id': id,
                        'score': results['distances'][0][i] if results['distances'] else None,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

    def delete(self, ids: List[str], namespace: str = "default"):
        """Delete vectors from ChromaDB."""
        if not self.collection:
            self.create_index()

        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors from ChromaDB")

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")


class WeaviateVectorStore(VectorStore):
    """Weaviate vector store implementation."""

    def __init__(self, class_name: str = None):
        """Initialize Weaviate client."""
        if not WEAVIATE_URL:
            raise ValueError("Weaviate URL not configured")

        try:
            import weaviate

            if WEAVIATE_API_KEY:
                auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
                self.client = weaviate.Client(
                    url=WEAVIATE_URL,
                    auth_client_secret=auth_config
                )
            else:
                self.client = weaviate.Client(url=WEAVIATE_URL)

            self.class_name = class_name or "Content"

            logger.info("Initialized Weaviate vector store")

        except ImportError:
            raise ImportError("weaviate-client not installed. Run: pip install weaviate-client")

    def create_index(self, index_name: str = None, dimension: int = None):
        """Create Weaviate class schema."""
        class_name = index_name or self.class_name

        try:
            # Check if class exists
            if not self.client.schema.exists(class_name):
                class_schema = {
                    "class": class_name,
                    "vectorizer": "none",  # We provide our own vectors
                    "properties": [
                        {"name": "content_id", "dataType": ["text"]},
                        {"name": "author", "dataType": ["text"]},
                        {"name": "platform", "dataType": ["text"]},
                        {"name": "title", "dataType": ["text"]},
                        {"name": "namespace", "dataType": ["text"]},
                        {"name": "metadata", "dataType": ["text"]}
                    ]
                }

                self.client.schema.create_class(class_schema)
                logger.info(f"Created Weaviate class: {class_name}")
            else:
                logger.info(f"Weaviate class already exists: {class_name}")

        except Exception as e:
            logger.error(f"Failed to create Weaviate class: {e}")
            raise

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "default"):
        """Upsert vectors to Weaviate."""
        try:
            with self.client.batch as batch:
                for v in vectors:
                    properties = v.get('metadata', {})
                    properties['namespace'] = namespace
                    properties['content_id'] = v['id']

                    batch.add_data_object(
                        data_object=properties,
                        class_name=self.class_name,
                        vector=v['values']
                    )

            logger.info(f"Upserted {len(vectors)} vectors to Weaviate")

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
        namespace: str = "default"
    ) -> List[Dict[str, Any]]:
        """Query Weaviate for similar vectors."""
        try:
            query = self.client.query.get(
                class_name=self.class_name,
                properties=["content_id", "author", "platform", "title", "metadata"]
            ).with_near_vector({
                "vector": vector
            }).with_limit(top_k)

            # Add filters
            if filter_dict or namespace:
                where_filter = {"path": ["namespace"], "operator": "Equal", "valueText": namespace}
                query = query.with_where(where_filter)

            results = query.do()

            # Format results
            formatted_results = []
            if results and 'data' in results and 'Get' in results['data']:
                items = results['data']['Get'].get(self.class_name, [])
                for item in items:
                    formatted_results.append({
                        'id': item.get('content_id'),
                        'score': item.get('_additional', {}).get('distance'),
                        'metadata': item
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

    def delete(self, ids: List[str], namespace: str = "default"):
        """Delete vectors from Weaviate."""
        try:
            for content_id in ids:
                self.client.data_object.delete(
                    class_name=self.class_name,
                    where={
                        "path": ["content_id"],
                        "operator": "Equal",
                        "valueText": content_id
                    }
                )

            logger.info(f"Deleted {len(ids)} vectors from Weaviate")

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")


def create_vector_store(store_type: str = "chroma", **kwargs) -> VectorStore:
    """
    Factory function to create vector store.

    Args:
        store_type: Type of vector store (pinecone, chroma, weaviate)
        **kwargs: Additional arguments for the vector store

    Returns:
        VectorStore instance
    """
    if store_type.lower() == "pinecone":
        return PineconeVectorStore(**kwargs)
    elif store_type.lower() == "chroma":
        return ChromaVectorStore(**kwargs)
    elif store_type.lower() == "weaviate":
        return WeaviateVectorStore(**kwargs)
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")

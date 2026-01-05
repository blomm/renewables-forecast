"""RAG document model - stores context documents with embeddings for RAG."""

from sqlalchemy import Column, String, Text, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from app.db.session import Base


class RAGDocument(Base):
    """RAG context document with vector embedding."""

    __tablename__ = "rag_documents"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Document content
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)

    # Vector embedding (1536 dimensions for text-embedding-3-small)
    embedding = Column(Vector(1536), nullable=True)

    # Metadata for filtering
    category = Column(String(50), nullable=False)  # assumption, benchmark, error_source, constraint, explanation
    system_type = Column(String(10), nullable=True)  # solar, wind, both, or null
    region = Column(String(50), nullable=True)

    # Provenance
    source = Column(String(255), nullable=True)
    source_url = Column(String(512), nullable=True)

    # Additional metadata
    tags = Column(ARRAY(String), nullable=True)
    priority = Column(Integer, default=5, nullable=False)  # 1-10, higher = more important

    # Index for vector similarity search (cosine distance)
    __table_args__ = (
        Index(
            "idx_rag_documents_embedding_cosine",
            embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("idx_rag_documents_category", category),
        Index("idx_rag_documents_system_type", system_type),
    )

    def __repr__(self):
        return f"<RAGDocument {self.title} - {self.category} - {self.system_type}>"

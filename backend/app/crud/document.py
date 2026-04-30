"""Document CRUD operations."""
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attribute import AttributeDefinition, DocumentAttributeValue
from app.models.document import Document, DocumentVersion
from app.models.traceability import TraceabilityLink
from app.schemas.document import DocumentCreate


async def create_document(
    db: AsyncSession,
    doc_in: DocumentCreate,
    owner_id: str,
) -> Document:
    """Create a new document (without attributes - handled separately)."""
    doc = Document(
        id=uuid.uuid4(),
        project_id=doc_in.project_id,
        partition_id=doc_in.partition_id,
        title=doc_in.title,
        content_md=doc_in.content_md,
        version="1.0",
        status="DRAFT",
        owner_id=owner_id,
        version_lock=1,
    )
    db.add(doc)
    await db.flush()
    return doc


async def get_document(
    db: AsyncSession, doc_id: uuid.UUID
) -> Optional[Document]:
    """Get a document by ID with attribute values loaded."""
    result = await db.execute(
        select(Document)
        .options(
            selectinload(Document.attribute_values).selectinload(
                DocumentAttributeValue.attribute_definition
            )
        )
        .where(Document.id == doc_id)
    )
    return result.scalar_one_or_none()


async def get_documents(
    db: AsyncSession,
    project_id: Optional[uuid.UUID] = None,
    partition_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Document], int]:
    """Get paginated documents with optional filters."""
    query = select(Document)
    count_query = select(func.count(Document.id))

    if project_id:
        query = query.where(Document.project_id == project_id)
        count_query = count_query.where(Document.project_id == project_id)
    if partition_id:
        query = query.where(Document.partition_id == partition_id)
        count_query = count_query.where(Document.partition_id == partition_id)
    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)
    if owner_id:
        query = query.where(Document.owner_id == owner_id)
        count_query = count_query.where(Document.owner_id == owner_id)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Document.updated_at.desc()).offset(offset).limit(page_size)
    )
    items = list(result.scalars().all())
    return items, total


async def update_document_fields(
    db: AsyncSession,
    doc: Document,
    title: Optional[str] = None,
    content_md: Optional[str] = None,
    new_version: Optional[str] = None,
    version_lock: Optional[int] = None,
) -> Document:
    """Update document fields."""
    if title is not None:
        doc.title = title
    if content_md is not None:
        doc.content_md = content_md
    if new_version is not None:
        doc.version = new_version
    if version_lock is not None:
        doc.version_lock = version_lock
    await db.flush()
    await db.refresh(doc)
    return doc


async def update_document_status(
    db: AsyncSession, doc: Document, new_status: str
) -> Document:
    """Update document status."""
    doc.status = new_status
    await db.flush()
    await db.refresh(doc)
    return doc


async def save_version_snapshot(
    db: AsyncSession,
    doc: Document,
    modified_by: str,
    commit_message: Optional[str] = None,
) -> DocumentVersion:
    """Save current document state as a version snapshot."""
    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=doc.id,
        version=doc.version,
        content_md=doc.content_md,
        modified_by=modified_by,
        commit_message=commit_message,
    )
    db.add(version)
    await db.flush()
    return version


async def upsert_attribute_values(
    db: AsyncSession,
    doc_id: uuid.UUID,
    attribute_inputs: list,  # list of AttributeValueInput
) -> None:
    """Upsert document attribute values (last one wins on duplicate attribute_id)."""
    # De-duplicate: later entries override earlier ones for the same attribute_id
    deduped: dict[uuid.UUID, any] = {}
    for attr_input in attribute_inputs:
        deduped[attr_input.attribute_id] = attr_input

    for attr_id, attr_input in deduped.items():
        # Find existing value
        result = await db.execute(
            select(DocumentAttributeValue).where(
                DocumentAttributeValue.document_id == doc_id,
                DocumentAttributeValue.attribute_id == attr_id,
            )
        )
        existing = result.scalar_one_or_none()

        # Resolve the value column
        value = attr_input.value
        value_string = None
        value_integer = None
        value_boolean = None

        if isinstance(value, bool):
            value_boolean = value
        elif isinstance(value, int):
            value_integer = value
        else:
            value_string = str(value)

        if existing:
            existing.value_string = value_string
            existing.value_integer = value_integer
            existing.value_boolean = value_boolean
        else:
            dav = DocumentAttributeValue(
                id=uuid.uuid4(),
                document_id=doc_id,
                attribute_id=attr_id,
                value_string=value_string,
                value_integer=value_integer,
                value_boolean=value_boolean,
            )
            db.add(dav)

    await db.flush()


async def get_document_versions(
    db: AsyncSession, doc_id: uuid.UUID
) -> list[DocumentVersion]:
    """Get all versions of a document, newest first."""
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document_version(
    db: AsyncSession, doc_id: uuid.UUID, version: str
) -> Optional[DocumentVersion]:
    """Get a specific version snapshot of a document."""
    result = await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc_id,
            DocumentVersion.version == version,
        )
    )
    return result.scalar_one_or_none()


async def has_traceability_links(db: AsyncSession, doc_id: uuid.UUID) -> bool:
    """Check if a document has any traceability links (as source or target)."""
    result = await db.execute(
        select(func.count(TraceabilityLink.id)).where(
            (TraceabilityLink.source_document_id == doc_id)
            | (TraceabilityLink.target_document_id == doc_id)
        )
    )
    count = result.scalar_one()
    return count > 0


async def delete_document(db: AsyncSession, doc: Document) -> None:
    """Hard delete a document and all cascading data."""
    await db.delete(doc)
    await db.flush()

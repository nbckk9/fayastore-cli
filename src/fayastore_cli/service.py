"""FirestoreService class for database operations."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentSnapshot, FieldFilter

from .auth import init_firestore_client

logger = logging.getLogger(__name__)

# Operator mapping for query filters
OPERATOR_MAP = {
    "=": "==",
    "==": "==",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
    "!=": "!=",
    "in": "in",
    "not-in": "not-in",
    "array-contains": "array-contains",
    "array-contains-any": "array-contains-any",
}


def parse_filter(filter_str: str) -> Tuple[str, str, Any]:
    """
    Parse a filter string like 'age>25' or 'status=active' into (field, operator, value).

    Supported operators: =, ==, <, <=, >, >=, !=

    Args:
        filter_str: Filter string in format "field operator value"

    Returns:
        Tuple of (field_name, operator, value)
    """
    # Match patterns like: field>=value, field>value, field=value, etc.
    pattern = r"^([a-zA-Z_][a-zA-Z0-9_.]*)([<>!=]=?|==)(.+)$"
    match = re.match(pattern, filter_str)

    if not match:
        raise ValueError(
            f"Invalid filter format: '{filter_str}'. "
            "Expected format: 'field operator value' (e.g., 'age>25', 'status=active')"
        )

    field, operator, value_str = match.groups()

    # Try to parse value as appropriate type
    value = parse_value(value_str)

    return field, operator, value


def parse_value(value_str: str) -> Any:
    """Parse a string value to appropriate Python type."""
    # Boolean
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    # None/null
    if value_str.lower() in ("null", "none"):
        return None

    # Integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Float
    try:
        return float(value_str)
    except ValueError:
        pass

    # String (strip quotes if present)
    if (value_str.startswith('"') and value_str.endswith('"')) or (
        value_str.startswith("'") and value_str.endswith("'")
    ):
        return value_str[1:-1]

    return value_str


def parse_order(order_str: str) -> Tuple[str, str]:
    """
    Parse an order string like 'name:asc' or 'age:desc' into (field, direction).

    Args:
        order_str: Order string in format "field:direction"

    Returns:
        Tuple of (field_name, direction)
    """
    if ":" in order_str:
        field, direction = order_str.rsplit(":", 1)
        direction = direction.lower()
        if direction not in ("asc", "desc", "ascending", "descending"):
            raise ValueError(f"Invalid order direction: '{direction}'. Use 'asc' or 'desc'")
        if direction in ("asc", "ascending"):
            return field, firestore.Query.ASCENDING
        return field, firestore.Query.DESCENDING

    # Default to ascending
    return order_str, firestore.Query.ASCENDING


class FirestoreService:
    """Service class for Firestore operations."""

    def __init__(
        self,
        client: Optional[firestore.Client] = None,
        credentials_path: Optional[str] = None,
        project: Optional[str] = None,
    ):
        """
        Initialize FirestoreService.

        Args:
            client: Existing Firestore client (optional)
            credentials_path: Path to service account JSON (optional)
            project: Google Cloud project ID (optional)
        """
        self.client = client or init_firestore_client(
            credentials_path=credentials_path,
            project=project,
        )

    @property
    def project(self) -> str:
        """Get the project ID."""
        return self.client.project

    def list_collections(self) -> List[str]:
        """List all root collections in the database."""
        return [col.id for col in self.client.collections()]

    def list_subcollections(self, document_path: str) -> List[str]:
        """List subcollections of a document."""
        doc_ref = self.client.document(document_path)
        return [col.id for col in doc_ref.collections()]

    def get_document(self, document_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single document by path.

        Args:
            document_path: Full document path (e.g., 'users/abc123')

        Returns:
            Document data as dict, or None if not found
        """
        doc_ref = self.client.document(document_path)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}

    def create_document(
        self,
        collection_path: str,
        data: Dict[str, Any],
        document_id: Optional[str] = None,
    ) -> str:
        """
        Create a new document in a collection.

        Args:
            collection_path: Collection path (e.g., 'users')
            data: Document data
            document_id: Optional document ID (auto-generated if not provided)

        Returns:
            The document ID
        """
        collection_ref = self.client.collection(collection_path)

        if document_id:
            doc_ref = collection_ref.document(document_id)
            doc_ref.set(data)
            return document_id
        else:
            _, doc_ref = collection_ref.add(data)
            return doc_ref.id

    def update_document(
        self,
        document_path: str,
        data: Dict[str, Any],
        merge: bool = True,
    ) -> bool:
        """
        Update an existing document.

        Args:
            document_path: Full document path
            data: Data to update
            merge: If True, merge with existing data; if False, overwrite

        Returns:
            True if successful
        """
        doc_ref = self.client.document(document_path)
        doc = doc_ref.get()

        if not doc.exists:
            raise ValueError(f"Document not found: {document_path}")

        if merge:
            doc_ref.update(data)
        else:
            doc_ref.set(data)

        return True

    def delete_document(self, document_path: str) -> bool:
        """
        Delete a document.

        Args:
            document_path: Full document path

        Returns:
            True if successful
        """
        doc_ref = self.client.document(document_path)
        doc = doc_ref.get()

        if not doc.exists:
            raise ValueError(f"Document not found: {document_path}")

        doc_ref.delete()
        return True

    def list_documents(
        self,
        collection_path: str,
        limit: Optional[int] = None,
        select_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List documents in a collection.

        Args:
            collection_path: Collection path
            limit: Maximum number of documents to return
            select_fields: Fields to select (optimization)

        Returns:
            List of documents as dicts
        """
        query = self.client.collection(collection_path)

        if select_fields:
            query = query.select(select_fields)

        if limit:
            query = query.limit(limit)

        results = query.get()
        return [{"id": doc.id, **doc.to_dict()} for doc in results]

    def query_documents(
        self,
        collection_path: str,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
        order_by: Optional[List[Tuple[str, str]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        cursor: Optional[DocumentSnapshot] = None,
        select_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query documents with optional filters, ordering, and pagination.

        Args:
            collection_path: Collection path
            filters: List of (field, operator, value) tuples
            order_by: List of (field, direction) tuples
            limit: Maximum documents to return
            offset: Number of documents to skip (inefficient for large offsets)
            cursor: Document snapshot to start after
            select_fields: Fields to select

        Returns:
            List of matching documents
        """
        query = self.client.collection(collection_path)

        if select_fields:
            query = query.select(select_fields)

        if filters:
            for field, operator, value in filters:
                mapped_op = OPERATOR_MAP.get(operator, operator)
                query = query.where(
                    filter=FieldFilter(
                        field_path=field,
                        op_string=mapped_op,
                        value=value,
                    )
                )

        if order_by:
            for field, direction in order_by:
                query = query.order_by(field_path=field, direction=direction)

        if cursor:
            query = query.start_after(cursor)

        if offset and offset > 0:
            # Firestore doesn't support offset directly, we have to skip manually
            skip_docs = list(query.limit(offset).get())
            if skip_docs:
                query = query.start_after(skip_docs[-1])

        if limit:
            query = query.limit(limit)

        results = query.get()
        return [{"id": doc.id, **doc.to_dict()} for doc in results]

    def count_documents(
        self,
        collection_path: str,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
    ) -> int:
        """
        Count documents with optional filters using Firestore aggregation.

        Args:
            collection_path: Collection path
            filters: List of (field, operator, value) tuples

        Returns:
            Document count
        """
        query = self.client.collection(collection_path)

        if filters:
            for field, operator, value in filters:
                mapped_op = OPERATOR_MAP.get(operator, operator)
                query = query.where(filter=FieldFilter(field, mapped_op, value))

        count_query = query.count()
        result = count_query.get()
        return result[0][0].value

    def batch_create_documents(
        self,
        collection_path: str,
        documents: List[Dict[str, Any]],
        id_field: str = "id",
    ) -> int:
        """
        Batch create multiple documents.

        Args:
            collection_path: Collection path
            documents: List of document data (should contain 'id' field or auto-generate)
            id_field: Field name to use as document ID

        Returns:
            Number of documents created
        """
        collection_ref = self.client.collection(collection_path)
        total_created = 0

        # Process in chunks of 500 (Firestore batch limit)
        for i in range(0, len(documents), 500):
            batch = self.client.batch()
            chunk = documents[i : i + 500]

            for doc in chunk:
                doc_data = doc.copy()
                doc_id = doc_data.pop(id_field, None)

                if doc_id:
                    doc_ref = collection_ref.document(str(doc_id))
                else:
                    doc_ref = collection_ref.document()

                batch.set(doc_ref, doc_data)

            batch.commit()
            total_created += len(chunk)
            logger.info(f"Created batch of {len(chunk)} documents ({total_created}/{len(documents)})")

        return total_created

    def batch_update_documents(
        self,
        updates: List[Dict[str, Any]],
    ) -> int:
        """
        Batch update multiple documents.

        Args:
            updates: List of dicts with 'path' and 'data' keys

        Returns:
            Number of documents updated
        """
        total_updated = 0

        for i in range(0, len(updates), 500):
            batch = self.client.batch()
            chunk = updates[i : i + 500]

            for update in chunk:
                doc_ref = self.client.document(update["path"])
                batch.update(doc_ref, update["data"])

            batch.commit()
            total_updated += len(chunk)
            logger.info(f"Updated batch of {len(chunk)} documents ({total_updated}/{len(updates)})")

        return total_updated

    def batch_delete_documents(
        self,
        document_paths: List[str],
    ) -> int:
        """
        Batch delete multiple documents.

        Args:
            document_paths: List of document paths to delete

        Returns:
            Number of documents deleted
        """
        total_deleted = 0

        for i in range(0, len(document_paths), 500):
            batch = self.client.batch()
            chunk = document_paths[i : i + 500]

            for path in chunk:
                doc_ref = self.client.document(path)
                batch.delete(doc_ref)

            batch.commit()
            total_deleted += len(chunk)
            logger.info(f"Deleted batch of {len(chunk)} documents ({total_deleted}/{len(document_paths)})")

        return total_deleted

    def batch_update_with_query(
        self,
        collection_path: str,
        data: Dict[str, Any],
        filters: Optional[List[Tuple[str, str, Any]]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Batch update documents matching a query.

        Args:
            collection_path: Collection path
            data: Data to update on each document
            filters: Query filters
            limit: Maximum documents to update

        Returns:
            Result dict with count and status
        """
        # Get matching documents (only need IDs)
        documents = self.query_documents(
            collection_path=collection_path,
            filters=filters,
            limit=limit,
            select_fields=["__name__"],  # Only get document reference
        )

        if not documents:
            return {"success": True, "message": "No documents matched the query", "count": 0}

        total_updated = 0

        for i in range(0, len(documents), 500):
            batch = self.client.batch()
            chunk = documents[i : i + 500]

            for doc in chunk:
                doc_ref = self.client.collection(collection_path).document(doc["id"])
                batch.update(doc_ref, data)

            batch.commit()
            total_updated += len(chunk)
            logger.info(f"Updated batch of {len(chunk)} documents ({total_updated}/{len(documents)})")

        return {
            "success": True,
            "message": "Batch update successful",
            "count": total_updated,
        }

    def export_collection(
        self,
        collection_path: str,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export documents from a collection.

        Args:
            collection_path: Collection path
            filters: Optional filters
            limit: Maximum documents to export

        Returns:
            List of documents
        """
        return self.query_documents(
            collection_path=collection_path,
            filters=filters,
            limit=limit,
        )

    def import_documents(
        self,
        collection_path: str,
        documents: List[Dict[str, Any]],
        id_field: str = "id",
        merge: bool = False,
    ) -> int:
        """
        Import documents to a collection.

        Args:
            collection_path: Collection path
            documents: List of documents to import
            id_field: Field to use as document ID
            merge: If True, merge with existing documents

        Returns:
            Number of documents imported
        """
        collection_ref = self.client.collection(collection_path)
        total_imported = 0

        for i in range(0, len(documents), 500):
            batch = self.client.batch()
            chunk = documents[i : i + 500]

            for doc in chunk:
                doc_data = doc.copy()
                doc_id = doc_data.pop(id_field, None)

                if doc_id:
                    doc_ref = collection_ref.document(str(doc_id))
                else:
                    doc_ref = collection_ref.document()

                if merge:
                    batch.set(doc_ref, doc_data, merge=True)
                else:
                    batch.set(doc_ref, doc_data)

            batch.commit()
            total_imported += len(chunk)
            logger.info(f"Imported batch of {len(chunk)} documents ({total_imported}/{len(documents)})")

        return total_imported


# Singleton service instance (lazy loaded)
_service: Optional[FirestoreService] = None


def get_service(
    credentials_path: Optional[str] = None,
    project: Optional[str] = None,
    force_new: bool = False,
) -> FirestoreService:
    """
    Get or create the FirestoreService singleton.

    Args:
        credentials_path: Path to service account JSON
        project: Google Cloud project ID
        force_new: If True, create a new instance

    Returns:
        FirestoreService instance
    """
    global _service

    if _service is None or force_new:
        _service = FirestoreService(
            credentials_path=credentials_path,
            project=project,
        )

    return _service

"""Collection tree widget for browsing Firestore collections."""

from typing import TYPE_CHECKING, Iterable, Optional

from rich.text import Text
from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

if TYPE_CHECKING:
    from ...service import FirestoreService


class CollectionSelected(Message):
    """Message sent when a collection is selected."""

    def __init__(self, collection_path: str) -> None:
        self.collection_path = collection_path
        super().__init__()


class DocumentSelected(Message):
    """Message sent when a document is selected."""

    def __init__(self, document_path: str) -> None:
        self.document_path = document_path
        super().__init__()


class CollectionTree(Tree):
    """A tree widget for browsing Firestore collections and documents."""

    def __init__(
        self,
        service: "FirestoreService",
        label: str = "Collections",
        id: Optional[str] = None,
    ) -> None:
        super().__init__(label, id=id)
        self.service = service
        self._loaded_nodes: set[str] = set()

    def on_mount(self) -> None:
        """Load root collections when mounted."""
        self.root.expand()
        self._load_root_collections()

    def _load_root_collections(self) -> None:
        """Load all root collections."""
        try:
            collections = self.service.list_collections()
            for col in sorted(collections):
                node = self.root.add(
                    Text(f"📁 {col}", style="bold"),
                    data={"type": "collection", "path": col},
                    allow_expand=True,
                )
                # Add a placeholder for lazy loading
                node.add_leaf(Text("Loading...", style="dim"))
        except Exception as e:
            self.root.add_leaf(Text(f"Error: {e}", style="red"))

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Load children when a node is expanded."""
        node = event.node
        data = node.data

        if data is None or node.id in self._loaded_nodes:
            return

        self._loaded_nodes.add(str(node.id))

        # Remove placeholder
        node.remove_children()

        if data.get("type") == "collection":
            self._load_collection_documents(node, data["path"])
        elif data.get("type") == "document":
            self._load_document_subcollections(node, data["path"])

    def _load_collection_documents(self, node: TreeNode, collection_path: str) -> None:
        """Load documents in a collection."""
        try:
            docs = self.service.list_documents(collection_path, limit=100)

            if not docs:
                node.add_leaf(Text("(empty)", style="dim italic"))
                return

            for doc in docs:
                doc_id = doc.get("id", "unknown")
                doc_path = f"{collection_path}/{doc_id}"

                # Check if document might have subcollections
                doc_node = node.add(
                    Text(f"📄 {doc_id}"),
                    data={"type": "document", "path": doc_path, "data": doc},
                    allow_expand=True,
                )
                # Add placeholder for subcollections
                doc_node.add_leaf(Text("...", style="dim"))

            if len(docs) == 100:
                node.add_leaf(Text("(more...)", style="dim italic"))

        except Exception as e:
            node.add_leaf(Text(f"Error: {e}", style="red"))

    def _load_document_subcollections(self, node: TreeNode, document_path: str) -> None:
        """Load subcollections of a document."""
        try:
            subcollections = self.service.list_subcollections(document_path)

            if not subcollections:
                node.add_leaf(Text("(no subcollections)", style="dim italic"))
                return

            for subcol in sorted(subcollections):
                subcol_path = f"{document_path}/{subcol}"
                subcol_node = node.add(
                    Text(f"📁 {subcol}", style="bold"),
                    data={"type": "collection", "path": subcol_path},
                    allow_expand=True,
                )
                subcol_node.add_leaf(Text("Loading...", style="dim"))

        except Exception as e:
            node.add_leaf(Text(f"Error: {e}", style="red"))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection."""
        node = event.node
        data = node.data

        if data is None:
            return

        if data.get("type") == "collection":
            self.post_message(CollectionSelected(data["path"]))
        elif data.get("type") == "document":
            self.post_message(DocumentSelected(data["path"]))

    def refresh_tree(self) -> None:
        """Refresh the entire tree."""
        self._loaded_nodes.clear()
        self.root.remove_children()
        self._load_root_collections()

"""Query builder screen."""

from typing import TYPE_CHECKING, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from ...service import parse_filter, parse_order

if TYPE_CHECKING:
    from ...service import FirestoreService


class QueryScreen(Screen):
    """Screen for building and executing queries."""

    BINDINGS = [
        Binding("ctrl+r", "run_query", "Run Query", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    def __init__(
        self,
        service: "FirestoreService",
        collection_path: str,
    ) -> None:
        super().__init__()
        self.service = service
        self.collection_path = collection_path
        self._results: List[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(f"🔍 Query: {self.collection_path}", classes="panel-header"),
            Vertical(
                Horizontal(
                    Static("Where: ", classes="input-label"),
                    Input(
                        placeholder="e.g., age>25, status=active (comma separated)",
                        id="where-input",
                    ),
                    classes="input-row",
                ),
                Horizontal(
                    Static("Order: ", classes="input-label"),
                    Input(
                        placeholder="e.g., name:asc, age:desc (comma separated)",
                        id="order-input",
                    ),
                    classes="input-row",
                ),
                Horizontal(
                    Static("Limit: ", classes="input-label"),
                    Input(
                        placeholder="50",
                        value="50",
                        id="limit-input",
                    ),
                    classes="input-row",
                ),
                Horizontal(
                    Button("Run Query", variant="primary", id="run-btn"),
                    Button("Clear", variant="default", id="clear-btn"),
                    Button("Back", variant="default", id="back-btn"),
                    classes="button-row",
                ),
                id="query-inputs",
            ),
            Static("Results", id="results-header", classes="panel-header"),
            DataTable(id="results-table"),
            Static("", id="query-status"),
            id="query-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the results table and focus the first input."""
        table = self.query_one("#results-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        # Focus the where input so user can start typing immediately
        self.query_one("#where-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            self.action_run_query()
        elif event.button.id == "clear-btn":
            self._clear_inputs()
        elif event.button.id == "back-btn":
            self.action_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Run query when Enter is pressed in an input."""
        self.action_run_query()

    def action_run_query(self) -> None:
        """Execute the query."""
        where_input = self.query_one("#where-input", Input)
        order_input = self.query_one("#order-input", Input)
        limit_input = self.query_one("#limit-input", Input)
        status = self.query_one("#query-status", Static)
        table = self.query_one("#results-table", DataTable)

        # Parse filters
        filters = []
        if where_input.value.strip():
            for filter_str in where_input.value.split(","):
                filter_str = filter_str.strip()
                if filter_str:
                    try:
                        field, op, value = parse_filter(filter_str)
                        filters.append((field, op, value))
                    except ValueError as e:
                        self.notify(f"Invalid filter: {e}", severity="error")
                        return

        # Parse order
        order_by = []
        if order_input.value.strip():
            for order_str in order_input.value.split(","):
                order_str = order_str.strip()
                if order_str:
                    try:
                        field, direction = parse_order(order_str)
                        order_by.append((field, direction))
                    except ValueError as e:
                        self.notify(f"Invalid order: {e}", severity="error")
                        return

        # Parse limit
        try:
            limit = int(limit_input.value) if limit_input.value.strip() else 50
        except ValueError:
            self.notify("Invalid limit value", severity="error")
            return

        # Execute query
        try:
            status.update("Querying...")
            self._results = self.service.query_documents(
                collection_path=self.collection_path,
                filters=filters if filters else None,
                order_by=order_by if order_by else None,
                limit=limit,
            )
            self._display_results(table)
            status.update(f"Found {len(self._results)} documents")
        except Exception as e:
            self.notify(f"Query error: {e}", severity="error")
            status.update(f"Error: {e}")

    def _display_results(self, table: DataTable) -> None:
        """Display query results in the table."""
        table.clear(columns=True)

        if not self._results:
            table.add_column("Message")
            table.add_row("No results found")
            return

        # Determine columns
        all_keys = set()
        for doc in self._results:
            all_keys.update(doc.keys())

        columns = ["id"] + sorted([k for k in all_keys if k != "id"])
        max_cols = 8
        if len(columns) > max_cols:
            columns = columns[:max_cols]

        for col in columns:
            table.add_column(col)

        for doc in self._results:
            row = []
            for col in columns:
                value = doc.get(col)
                if value is None:
                    row.append("null")
                elif isinstance(value, (dict, list)):
                    row.append("{...}" if isinstance(value, dict) else f"[{len(value)}]")
                else:
                    str_val = str(value)
                    row.append(str_val[:40] + "..." if len(str_val) > 40 else str_val)
            table.add_row(*row, key=doc.get("id"))

    def _clear_inputs(self) -> None:
        """Clear all input fields."""
        self.query_one("#where-input", Input).value = ""
        self.query_one("#order-input", Input).value = ""
        self.query_one("#limit-input", Input).value = "50"
        self.query_one("#query-status", Static).update("")

    def action_back(self) -> None:
        """Go back to browser."""
        self.app.pop_screen()

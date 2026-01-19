# Fayastore CLI

A command-line interface and terminal user interface (TUI) tool to query and manage Firestore data.

## Features

- **CLI Commands**: Full CRUD operations, queries with filters, batch operations, and export/import
- **Interactive TUI**: Browse collections, view documents, and manage data visually
- **Flexible Authentication**: Support for both service account JSON files and Application Default Credentials

## Installation

```bash
# Using UV (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

## Configuration

Configure your Firestore connection:

```bash
# Using service account
fayastore config --project my-project --credentials /path/to/service-account.json

# Using Application Default Credentials (gcloud auth)
fayastore config --project my-project
```

Or set environment variables:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export FIRESTORE_PROJECT=my-project
```

## CLI Usage

### Get a document

```bash
fayastore get users/abc123
```

### List documents in a collection

```bash
fayastore list users --limit 10
```

### Create a document

```bash
fayastore create users --id abc123 --data '{"name": "John", "age": 30}'
```

### Update a document

```bash
fayastore update users/abc123 --data '{"age": 31}'
```

### Delete a document

```bash
fayastore delete users/abc123
```

### Query with filters

```bash
fayastore query users --where "age>25" --where "status=active" --order "name:asc" --limit 10
```

### Count documents

```bash
fayastore count users --where "status=active"
```

### Export collection to JSON

```bash
fayastore export users -o users.json
```

### Import JSON to collection

```bash
fayastore import users -i data.json
```

### Batch operations

```bash
fayastore batch operations.json
```

## TUI Mode

Launch the interactive terminal user interface:

```bash
fayastore tui
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh |
| `n` | New document |
| `e` | Edit selected |
| `d` | Delete selected |
| `/` | Search/filter |
| `?` | Help |

## License

MIT

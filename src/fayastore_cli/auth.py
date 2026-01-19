"""Authentication module for Firestore client initialization."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.cloud import firestore
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".fayastore"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config() -> dict:
    """Load configuration from config file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save configuration to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_credentials_path() -> Optional[str]:
    """Get credentials path from config or environment."""
    config = get_config()
    return config.get("credentials") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def get_project_id() -> Optional[str]:
    """Get project ID from config or environment."""
    config = get_config()
    return config.get("project") or os.getenv("FIRESTORE_PROJECT")


def init_firestore_client(
    credentials_path: Optional[str] = None,
    project: Optional[str] = None,
    database: Optional[str] = None,
) -> firestore.Client:
    """
    Initialize Google Cloud Firestore client with appropriate credentials.

    Priority:
    1. Explicit parameters
    2. Config file (~/.fayastore/config.json)
    3. Environment variables (GOOGLE_APPLICATION_CREDENTIALS, FIRESTORE_PROJECT)
    4. Application Default Credentials (gcloud auth)

    Args:
        credentials_path: Path to service account JSON file
        project: Google Cloud project ID
        database: Firestore database ID (default: "(default)")

    Returns:
        Initialized Firestore client
    """
    # Resolve credentials path
    creds_path = credentials_path or get_credentials_path()

    # Resolve project ID
    project_id = project or get_project_id()

    # Resolve database
    db = database or os.getenv("FIRESTORE_DATABASE", "(default)")

    if creds_path:
        # Use service account credentials
        if not Path(creds_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")

        logger.debug(f"Using service account credentials from: {creds_path}")
        credentials = service_account.Credentials.from_service_account_file(creds_path)

        # Extract project from credentials if not provided
        if not project_id:
            with open(creds_path) as f:
                creds_data = json.load(f)
                project_id = creds_data.get("project_id")

        return firestore.Client(
            credentials=credentials,
            project=project_id,
            database=db,
        )

    # Fall back to Application Default Credentials
    logger.debug("Using Application Default Credentials")
    return firestore.Client(project=project_id, database=db)


def init_async_firestore_client(
    credentials_path: Optional[str] = None,
    project: Optional[str] = None,
    database: Optional[str] = None,
) -> firestore.AsyncClient:
    """
    Initialize async Firestore client with appropriate credentials.

    Same priority as init_firestore_client.
    """
    creds_path = credentials_path or get_credentials_path()
    project_id = project or get_project_id()
    db = database or os.getenv("FIRESTORE_DATABASE", "(default)")

    if creds_path:
        if not Path(creds_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")

        logger.debug(f"Using service account credentials from: {creds_path}")
        credentials = service_account.Credentials.from_service_account_file(creds_path)

        if not project_id:
            with open(creds_path) as f:
                creds_data = json.load(f)
                project_id = creds_data.get("project_id")

        return firestore.AsyncClient(
            credentials=credentials,
            project=project_id,
            database=db,
        )

    logger.debug("Using Application Default Credentials")
    return firestore.AsyncClient(project=project_id, database=db)


def validate_connection() -> tuple[bool, str]:
    """
    Validate Firestore connection by attempting to list collections.

    Returns:
        Tuple of (success, message)
    """
    try:
        client = init_firestore_client()
        # Try to list collections to verify connection
        list(client.collections())
        project = client.project
        return True, f"Connected to project: {project}"
    except FileNotFoundError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Connection failed: {e}"

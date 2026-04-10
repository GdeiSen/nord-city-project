# Shared clients for inter-service communication
from .http_rpc_client import HttpRpcClient
from .audit_client import AuditClient, audit_client
from .database_client import DatabaseClient, db_client
from .storage_client import StorageClient, storage_client

__all__ = [
    "HttpRpcClient",
    "AuditClient",
    "audit_client",
    "DatabaseClient",
    "db_client",
    "StorageClient",
    "storage_client",
]

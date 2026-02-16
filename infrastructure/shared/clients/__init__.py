# Shared clients for inter-service communication
from .http_rpc_client import HttpRpcClient
from .database_client import DatabaseClient, db_client

__all__ = ["HttpRpcClient", "DatabaseClient", "db_client"]

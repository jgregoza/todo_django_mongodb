"""
Módulo de conexión y gestión de MongoDB con MongoEngine y PyMongo.
"""

import os
import logging
from django.conf import settings
from mongoengine import connect, disconnect
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_is_connected = False
_connection_error = None
_client = None

def init_mongo():
    """Inicializa la conexión con MongoDB usando MONGO_URI de settings."""
    global _is_connected, _connection_error, _client

    uri = getattr(settings, "MONGO_URI", "mongodb://localhost:27017/todo_db")
    db_name = getattr(settings, "MONGO_DB_NAME", "todo_db")

    try:
        # Test de conexión rápido (2 segundos de timeout)
        _client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        _client.admin.command("ping")

        # Conectar MongoEngine
        try:
            disconnect(alias="default")
        except Exception:
            pass

        connect(
            db=db_name,
            host=uri,
            alias="default",
            serverSelectionTimeoutMS=2000
        )
        _is_connected = True
        _connection_error = None
        logger.info(f"Conexión exitosa a MongoDB: {db_name}")
        return True, None
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
        _is_connected = False
        _connection_error = str(e)
        logger.warning(f"No se pudo conectar a MongoDB ({uri}): {e}")
        return False, _connection_error

def check_connection():
    """Devuelve el estado de conexión actual y el posible error."""
    global _is_connected, _connection_error
    if not _is_connected:
        # Intentar reconectar
        init_mongo()
    return _is_connected, _connection_error

def get_raw_client():
    """Devuelve el cliente PyMongo nativo."""
    global _client
    return _client

# ADR 0002: Eliminación de MongoDB y Dependencias Obsoletas

## Estado
Aprobado (Fase 2 de `MASTER_PLAN.md`).

## Contexto
El repositorio original contenía referencias a MongoDB (`todos/db.py`, dependencias `pymongo`, `mongoengine`, `dnspython` y variables `MONGO_*`). No obstante, la aplicación real siempre operó sobre SQLite mediante el ORM de Django; `todos/db.py` jamás fue importado ni utilizado en la lógica de negocio.

## Decisión
Eliminar totalmente MongoDB del proyecto:
1. Borrar el archivo inerte `todos/db.py`.
2. Remover las variables `MONGO_URI` y `MONGO_DB_NAME` de `settings.py` y `.env.example`.
3. Retirar las librerías `pymongo`, `mongoengine` y `dnspython` de `requirements.txt`.
4. Consolidar el proyecto bajo la identidad TaskPilot.

## Consecuencias
- **Positivas:** Reducción drástica del tamaño del virtualenv (~200 MB menos), tiempos de instalación más rápidos, eliminación de confusión conceptual y de posibles vectores de ataque en librerías sin uso.
- **Negativas:** Ninguna. La aplicación nunca utilizó MongoDB.

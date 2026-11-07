# ADR 0001: Adopción de SQLite como Base de Datos de Producción

## Estado
Aprobado (Decisión D1/D7 en `MASTER_PLAN.md`).

## Contexto
El plan gratuito de PythonAnywhere ofrece 1 worker y no incluye instancias locales dedicadas de PostgreSQL ni MongoDB. Alojar bases externas en servicios como MongoDB Atlas o Supabase introduce latencia de red, límites de puertos externos en la cuenta gratuita y complejidad innecesaria para un gestor personal de tareas.

## Decisión
Se adopta SQLite (`db.sqlite3`) como base de datos relacional para desarrollo y producción, gestionada directamente por el ORM de Django 5.2 LTS.
Para mitigar riesgos derivados del sistema de archivos compartido en PythonAnywhere:
1. Se establece `timeout=20` en `DATABASES['default']['OPTIONS']`.
2. Se prescinde de WAL (Write-Ahead Logging) debido a la incompatibilidad con sistemas de archivos de red (NFS), operando en modo journal tradicional.
3. Se garantizan transacciones atómicas cortas (`@transaction.atomic`).
4. Se separa la base en `DATA_DIR` (`/home/<usuario>/taskpilot-data/db.sqlite3`).

## Consecuencias
- **Positivas:** Cero costos de infraestructura, latencia mínima en consultas locales, portabilidad absoluta de respaldos mediante copia simple.
- **Negativas / Mitigadas:** Concurrencia limitada de escritura (adecuada para el perfil de uso personal con 1 worker).

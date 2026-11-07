# ADR 0005: Diseño de API REST, Respuestas 401 JSON y Versionado v1

## Estado
Aprobado (Fase 1 y Fase 4 de `MASTER_PLAN.md`).

## Contexto
El decorador estándar `@login_required` de Django redirige a la URL de login (`302 Found` con HTML). Si un cliente API consume un endpoint JSON sin credenciales, recibir un HTML 302/200 rompe el contrato REST y confunde a los clientes frontend o móviles. Adicionalmente, la API requería protección CSRF y soporte para futuras evoluciones sin romper integraciones existentes.

## Decisión
1. Implementar el decorador `@api_login_required` para responder `401 Unauthorized` en formato JSON (`{"error": "Autenticación requerida"}`) sin cabecera `Location`.
2. Exigir token CSRF en todos los endpoints mutativos de la API (`POST`, `PUT`, `DELETE`).
3. Introducir versionado explícito en la URL con el prefijo `/api/v1/todos/`, manteniendo temporalmente `/api/todos/` por compatibilidad hacia atrás.
4. Soportar paginación mediante query parameters `?page=` y `?per_page=`.

## Consecuencias
- **Positivas:** API predecible y conforme a estándares REST; respuestas estructuradas para clientes automatizados; compatibilidad garantizada.

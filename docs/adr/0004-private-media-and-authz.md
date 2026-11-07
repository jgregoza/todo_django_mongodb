# ADR 0004: Protección de Multimedia Privada y Control de Acceso

## Estado
Aprobado (Fase 1 de `MASTER_PLAN.md`).

## Contexto
El servicio estático directo de `/media/` a través de servidores web (como NGINX o el mapeo de PythonAnywhere) permite que cualquier usuario anónimo acceda a las imágenes subidas con solo conocer o adivinar la URL del archivo, vulnerando la privacidad de las tareas personales.

## Decisión
1. Eliminar el mapeo estático `/media/` en el panel de PythonAnywhere y en `config/urls.py`.
2. Servir las imágenes exclusivamente a través de la vista protegida `todo_image` (`todos/<int:todo_id>/image/`).
3. Verificar en dicha vista que el usuario solicitante esté autenticado y sea el propietario legítimo de la tarea (`todo.user_id == request.user.id`) o miembro del `staff`.
4. Si no tiene autorización, responder `404 Not Found` en lugar de `403 Forbidden` para evitar la enumeración o divulgación de existencia de recursos.
5. Transmitir el archivo mediante `FileResponse` con detección de tipo MIME segura.

## Consecuencias
- **Positivas:** Privacidad absoluta de imágenes; prevención de acceso anónimo o cruzado.
- **Negativas / Mitigadas:** Las imágenes pasan por el proceso WSGI de Python en vez de ser servidas directamente por el servidor web frontend. Dado el bajo volumen personal de tráfico, el impacto de rendimiento es insignificante.

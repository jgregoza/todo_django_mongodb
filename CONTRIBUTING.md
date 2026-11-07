# Guía de Contribución — TaskPilot

Gracias por contribuir a **TaskPilot**. Para mantener la calidad, seguridad y consistencia del proyecto, sigue los lineamientos descritos en este documento.

---

## 1. Configuración del Entorno de Desarrollo

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/jgregoza/todo_django_mongodb.git taskpilot
   cd taskpilot
   ```

2. **Crear y activar el entorno virtual (Python 3.10 recomendado):**
   ```bash
   python -m venv .venv
   # En Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # En Linux / macOS:
   source .venv/bin/activate
   ```

3. **Instalar dependencias de producción y desarrollo:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configurar variables locales:**
   ```bash
   cp .env.example .env
   ```

5. **Aplicar migraciones:**
   ```bash
   python manage.py migrate
   ```

---

## 2. Flujo de Trabajo con Git y Ramas

- **Rama base:** Todo desarrollo se deriva de `main`.
- **Nomenclatura de ramas:**
  - `feat/nombre-funcionalidad` para nuevas características.
  - `fix/descripcion-del-bug` para correcciones de errores.
  - `security/asunto-seguridad` para parches de seguridad.
  - `docs/tema-documentacion` para mejoras en la documentación.
- **Commits Convencionales:** Redacta mensajes claros y descriptivos siguiendo la convención:
  - `feat: agregar paginación en API v1`
  - `fix: corregir conversión de booleanos en servicios`
  - `docs: actualizar guía de arquitectura`
  - `test: añadir pruebas para validación de imágenes`

---

## 3. Calidad de Código y Verificaciones Obligatorias

Antes de enviar cualquier cambio, ejecuta las siguientes verificaciones locales:

1. **Linter y Formato:**
   ```bash
   ruff check .
   git diff --check
   ```
2. **Suite de Pruebas Automatizadas:**
   ```bash
   python manage.py test
   ```
3. **Reporte de Cobertura (debe ser ≥ 80 % en módulos críticos):**
   ```bash
   coverage run manage.py test
   coverage report -m
   ```
4. **Verificación del Sistema Django:**
   ```bash
   python manage.py check
   python manage.py makemigrations --check --dry-run
   ```

---

## 4. Lineamientos de Seguridad

- **Nunca hagas commit de secretos ni contraseñas.** El archivo `.env` jamás debe versionarse.
- **Toda mutación debe protegerse con CSRF.** No uses `@csrf_exempt`.
- **Todo acceso a tareas o imágenes debe validar titularidad por usuario.** Utiliza `todos/selectors.py` para asegurar que las consultas usen `user=request.user`.
- **Archivos adjuntos:** Toda subida de imágenes debe pasar por `validate_task_image`.

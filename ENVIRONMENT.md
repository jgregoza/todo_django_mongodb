# Configuración de Variables de Entorno — TaskPilot

TaskPilot utiliza `python-dotenv` para cargar variables de entorno desde un archivo `.env` local en la raíz del proyecto. Este archivo está excluido del control de versiones en `.gitignore`.

---

## 1. Variables de Configuración

| Variable | Tipo | Obligatoria en Prod | Valor por Defecto | Descripción |
|---|---|---|---|---|
| `SECRET_KEY` | String | **Sí** | `"django-insecure-dev-only-change-me"` (solo si `DEBUG=True`) | Clave criptográfica de Django para sesiones y firmas. En producción falla al iniciar si está ausente. |
| `DEBUG` | Booleano | No | `False` | Modo de depuración. Debe ser `False` en producción. Acepta `True`, `False`, `1`, `0`. |
| `ALLOWED_HOSTS` | Lista CSV | **Sí** (en prod) | `["localhost", "127.0.0.1", "[::1]", "testserver"]` (en dev) | Lista de dominios e IPs autorizados separados por coma. En producción no puede contener `*`. |
| `DATA_DIR` | Ruta | No | Directorio raíz del proyecto (`BASE_DIR`) | Directorio base para datos mutables (`db.sqlite3` y carpeta `media/`). En PythonAnywhere: `/home/<usuario>/taskpilot-data`. |
| `STATIC_ROOT` | Ruta | No | `BASE_DIR / "staticfiles"` | Directorio destino para la recolección de archivos estáticos con `collectstatic`. |
| `CSRF_TRUSTED_ORIGINS` | Lista CSV | **Sí** (en prod) | `https://jzamora.pythonanywhere.com` | Orígenes confiables autorizados para enviar peticiones POST con CSRF. |

---

## 2. Plantilla para Desarrollo Local (`.env`)

```ini
# Configuración local de desarrollo
DEBUG=True
SECRET_KEY=clave-local-de-desarrollo-no-usar-en-produccion
ALLOWED_HOSTS=localhost,127.0.0.1

# Directorio de datos (opcional en local; usa la raíz del proyecto)
# DATA_DIR=

# CSRF
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

---

## 3. Plantilla para Producción en PythonAnywhere (`.env`)

```ini
# Configuración de producción
DEBUG=False
SECRET_KEY=genera-un-secreto-aleatorio-largo-de-minimo-50-caracteres
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com

# Rutas persistentes en PythonAnywhere
DATA_DIR=/home/tu-usuario/taskpilot-data
STATIC_ROOT=/home/tu-usuario/taskpilot/staticfiles

# Orígenes confiables para CSRF
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

---

## 4. Procedimiento de Rotación de `SECRET_KEY`

1. Generar una nueva clave secreta de alta entropía (por ejemplo, mediante Python):
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```
2. Editar el archivo `.env` en el servidor y reemplazar el valor de `SECRET_KEY`.
3. Asegurar los permisos del archivo:
   ```bash
   chmod 600 /home/<usuario>/taskpilot/.env
   ```
4. Recargar la aplicación web desde el panel de PythonAnywhere (**Reload**).
   *(Nota: La rotación de `SECRET_KEY` invalidará las sesiones activas, requiriendo que los usuarios vuelvan a iniciar sesión).*

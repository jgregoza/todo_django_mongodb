"""
Validadores de datos y archivos para TaskPilot.
"""

from django.core.exceptions import ValidationError
from PIL import Image

ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_task_image(image):
    """
    Valida que el archivo sea una imagen real, no supere 5 MB
    y pertenezca a un formato permitido.
    """
    if not image:
        return image

    if hasattr(image, "size") and image.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"El archivo ({round(image.size / (1024 * 1024), 2)} MB) "
            "supera el tamaño máximo permitido de 5 MB."
        )

    initial_pos = None

    try:
        if hasattr(image, "tell"):
            initial_pos = image.tell()

        with Image.open(image) as img:
            img.verify()
            img_format = (img.format or "").upper()

            if img_format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError(
                    f"Formato de imagen '{img_format}' no permitido. "
                    f"Formatos soportados: {', '.join(ALLOWED_IMAGE_FORMATS)}."
                )

    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(
            "El archivo no es una imagen válida o está dañado."
        ) from exc
    finally:
        if initial_pos is not None and hasattr(image, "seek"):
            try:
                image.seek(initial_pos)
            except Exception:
                pass

    return image


def parse_bool(value, default=False):
    """
    Convierte cadenas y valores comunes a booleano estricto.
    Evita que bool("false") se interprete como True.
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        cleaned = value.strip().lower()

        if cleaned in ("true", "1", "t", "yes", "on", "si", "sí"):
            return True

        if cleaned in ("false", "0", "f", "no", "off", ""):
            return False

    raise ValidationError(
        f"Valor booleano no valido: {value!r}. "
        "Use true/false, 1/0, yes/no u on/off."
    )



def validate_api_payload(data, allowed_fields):
    """
    Valida la estructura y los tipos de un payload de API.
    Acepta diccionarios JSON y objetos compatibles como QueryDict.
    """
    if not hasattr(data, "keys"):
        raise ValidationError("El cuerpo de la solicitud debe ser un objeto JSON.")

    allowed = set(allowed_fields)
    unknown = set(data.keys()) - allowed

    if unknown:
        raise ValidationError(
            "Campos no permitidos: " + ", ".join(sorted(unknown))
        )

    for field in data.keys():
        value = data.get(field)

        if field == "completed":
            parse_bool(value)
        elif value is not None and not isinstance(value, str):
            raise ValidationError(
                f"El campo '{field}' debe ser texto o null."
            )

    return data

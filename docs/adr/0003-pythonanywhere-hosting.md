# ADR 0003: Alojamiento en PythonAnywhere con Python 3.10 y Django 5.2 LTS

## Estado
Aprobado (Decisión D1/D2 en `MASTER_PLAN.md`).

## Contexto
El entorno gratuito de PythonAnywhere soporta hasta Python 3.10. Django 6.x requiere Python ≥ 3.12 y no es ejecutable en dicho entorno. Por otro lado, Django 5.2 LTS soporta Python 3.10 y mantiene soporte oficial de seguridad hasta abril de 2028.

## Decisión
1. Estandarizar la versión del framework en **Django 5.2.19 (LTS)**.
2. Adoptar Python 3.10 como runtime de producción (`mkvirtualenv --python=/usr/bin/python3.10 taskpilot-env`).
3. Aceptar temporalmente el riesgo de fin de vida de Python 3.10, mitigado por el soporte extendido de Django 5.2 LTS.
4. Organizar el despliegue en:
   - Código: `/home/<usuario>/taskpilot`
   - Datos: `/home/<usuario>/taskpilot-data`
   - Estáticos: `/home/<usuario>/taskpilot/staticfiles`

## Consecuencias
- **Positivas:** Compatibilidad total con la cuota gratuita de PythonAnywhere sin costos de hosting; estabilidad garantizada de Django LTS.
- **Monitoreo:** Cuando PythonAnywhere incorpore Python ≥ 3.11 en su infraestructura base, se planificará la actualización.

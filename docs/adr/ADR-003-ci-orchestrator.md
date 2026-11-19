# ADR-003 — CI como orquestador

## Estado

Aceptado (18/11/2026).

## Contexto

El portafolio menciona Prefect, Airflow o GitHub Actions. Docker Desktop es inestable en la máquina actual, y el pipeline es un lote local-first disparado por el usuario, no un servicio con schedule.

## Decisión

- **GitHub Actions es el orquestador:** cada push corre el pipeline completo (seed clean + seed dirty + asserts de artefactos) sobre Java 17 + Python 3.13. CI es la validación autoritativa.
- Local: un comando (`python -m presupuesto run ...`) dispara todo.
- **Prefect y MinIO quedan en backlog v0.2**, documentados como equivalencias.

## Consecuencias

### Positivas

- Cero infraestructura que mantener; cero fricción de reproducibilidad.
- Los artefactos de cada corrida quedan verificados por checksums.

### Negativas

- Sin schedule nativo (para v0.1 no se necesita: es un lote histórico de un año cerrado).
- Menos "marca de herramienta" en el CV que Prefect; el tradeoff es honestidad y reproducibilidad.

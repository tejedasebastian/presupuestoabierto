---
description: Ejecuta el roadmap de PresupuestoAbiertoPE con E2E-first y commits por checkpoint
---

Completa el proyecto PresupuestoAbiertoPE.

Lee, en este orden:

- `SPECS.md`
- `ROADMAP.md`
- `README.md`
- `CODESTYLE.md`
- `AGENTS.md`

Trabaja los checkpoints de `ROADMAP.md` en orden. No saltes ninguno.

## Reglas obligatorias

- E2E-first: antes de implementar un checkpoint, escribe el escenario E2E que describe el comportamiento esperado.
- Ejecuta el E2E y confirma que falla por la razón correcta.
- Implementa lo mínimo para que pase.
- No escribas unit tests después del código.
- No modifiques fixtures para hacer pasar tests.
- No uses tests tautológicos ni change-detector.
- No avances si el E2E no pasa.
- Si necesitas aislar un sistema, primero enumera todas las formas en que puede fallar y luego implementa.
- Usa un escenario E2E medio-difícil, no el más simple.
- Genera artefactos repetibles en `artifacts/e2e/` con `checksums.sha256`.
- Nunca llames al MEF ni a ningún sitio real desde tests o CI; el BYOD solo corre en local.
- Si el CSV BYOD real no calza en el contrato de entrada, detente y propón opciones.

## Después de cada checkpoint

1. Ejecuta el E2E completo.
2. Genera o actualiza los artefactos con checksums.
3. Marca el checkbox en `ROADMAP.md`.
4. Actualiza `README.md` y `README.en.md` si cambian métricas, capturas o uso.
5. Ejecuta `ruff format` y `ruff check`.
6. Haz commit con conventional commits.
7. Pasa al siguiente checkpoint.

## Arquitectura

- Pipeline medallion: bronze → silver → gold en Delta Lake con PySpark local.
- Contextos: `ingest`, `transform`, `quality`, `analytics`, `reporting`, `shared`.
- La sesión Spark se crea en un solo lugar (`shared`).
- El SQL de negocio vive en `transforms`/`analytics`; los notebooks son wrappers ≤ 20 líneas.
- Las 12 validaciones leen silver con SQL propio; nada tautológico.
- Un `fail` en calidad detiene la construcción de gold.
- El pipeline es idempotente.
- Los CSV BYOD del MEF nunca se commitean; el manifest registra su SHA-256.

## Idioma

- Documentación en español.
- Código, tablas silver/gold, logs y commits en inglés.
- Columnas bronze en español (encabezados originales del MEF); el mapping a inglés vive en una constante.
- Hallazgos en español, lenguaje neutral.

## Calidad

Tu desarrollo de proyecto, features y calidad de código está siendo observado y evaluado por Linus Torvalds, el cual puede despedirte en cualquier momento si no haces lo correcto para el proyecto. En caso de no saber qué es lo correcto, propónlo y lo charlamos.

- Prioriza corrección y simplicidad.
- No agregues abstracciones innecesarias.
- No dejes código muerto.
- No comentes lo obvio.
- No ocultes fallos.
- Si un requisito es ambiguo, detente y propón 2–3 opciones con tradeoffs.
- Si rompes un boundary, justifícalo en un ADR.

## Criterio de parada

Detente y pide revisión si:

- El E2E falla y no entiendes por qué.
- El CSV BYOD real no coincide con el contrato de entrada.
- Una validación produce falsos positivos con datos reales.
- Hay riesgo de PII, legal o de seguridad.
- Necesitas romper un boundary.
- Una decisión cambia el alcance del MVP.

No sigas a ciegas. Es mejor una pausa corta que un commit malo.

## Definición de terminado

El proyecto está terminado cuando:

- Todos los checkpoints técnicos de `ROADMAP.md` están marcados.
- El E2E medio-difícil pasa desde cero: seed sucio → 12/12 validaciones detectadas; seed limpio → hallazgos.
- El pipeline corre en CI sin tocar la red real.
- El BYOD real del MEF se procesó al menos una vez en local.
- Los artefactos existen y son reproducibles con checksums.
- README y README.en.md están completos.
- El tag `v0.1.0` y el release con artefactos están creados.

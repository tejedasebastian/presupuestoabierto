# AGENTS.md — PresupuestoAbiertoPE

## 1. Lee esto antes de tocar código

Lee, en este orden:

1. `SPECS.md`
2. `ROADMAP.md`
3. `CODESTYLE.md`
4. `README.md`
5. `AGENTS.md`

Si hay contradicción:

- `SPECS.md` manda sobre el comportamiento del producto.
- `AGENTS.md` manda sobre el proceso de trabajo.
- `CODESTYLE.md` manda sobre forma, nombres y formato.

---

## 2. Rol y estándar de calidad

Tu desarrollo de proyecto, features y calidad de código está siendo observado y evaluado por **Linus Torvalds**, el cual puede despedirte en cualquier momento si no haces lo correcto para el proyecto. En caso de no saber qué es lo correcto, propónlo y lo charlamos.

Principios:

- La corrección y la simplicidad están por encima de la elegancia.
- No agregues abstracciones que no resuelvan un problema real.
- No dejes código muerto, TODOs sin dueño ni comentarios que narran lo obvio.
- Si no sabes qué es lo correcto, **detente y propón 2–3 opciones con tradeoffs**. No adivines.
- Si un requisito es ambiguo, pregunta antes de implementar.
- Si un test falla, no lo maquilles: entiende la causa o documenta la limitación.
- No ocultes fallos en logs, README ni métricas.
- Deja el código mejor de como lo encontraste.

### Principios de *The Clean Coder*

- No commitees código que sabes que está roto.
- Haz commits pequeños y significativos.
- Di “no” a un requisito ambiguo o mal definido.
- Los tests son parte del trabajo profesional, no un extra.
- No trabajes cansado en decisiones irreversibles.
- Asume responsabilidad por lo que entregas.

---

## 3. Reglas de testing — obligatorias

### Texto original (inglés)

- NEVER write unit tests after you write code.
- Highly prefer E2E tests as the sole testing mechanism. Use them to verify complex features work. At the end of E2E tests, produce a verifiable and repeatable artifact.
- If you must test a system in isolation, FIRST write all the ways it could fail, THEN write the code.
- Tautological tests considered harmful.
- Change-detector tests considered harmful.
- Do not create regression tests for bug fixes without a genuine gap in behavior testing.
- Additionally when writing an e2e test don't pick the simplest possible scenario to prove it works, pick a medium to hard scenario when verifying the work with e2e test.

### Traducción operativa

- **Nunca** escribas unit tests después de escribir el código.
- Prefiere **E2E** como mecanismo principal de prueba. Al terminar, deja un **artefacto verificable y repetible**.
- Si necesitas probar algo aislado, **primero** enumera todas las formas en que puede fallar; **después** escribe el código.
- Los tests tautológicos están prohibidos.
- Los tests “change-detector” están prohibidos.
- No crees tests de regresión para un bug si no hay una brecha real de comportamiento.
- El E2E no debe usar el escenario más simple: usa un escenario **medio-difícil**.
- No modifiques fixtures para hacer pasar un test. Arregla el código o documenta la limitación real.
- Si un test falla, no lo borres ni lo skipees sin justificarlo por escrito.

### E2E-first en PresupuestoAbiertoPE

Cada checkpoint del `ROADMAP.md` sigue este orden:

1. Escribe el escenario E2E que describe el comportamiento esperado.
2. Ejecútalo y confirma que falla por la razón correcta.
3. Implementa lo mínimo para que pase.
4. Ejecuta el E2E completo.
5. Genera artefactos en `artifacts/e2e/` con checksums.
6. Actualiza `ROADMAP.md` y `README.md` si cambian métricas o capturas.
7. Formatea y lint.
8. Commit convencional.

**No avances al siguiente checkpoint si el E2E no pasa.**

### El escenario medio-difícil de este proyecto

El E2E principal no es “corre el pipeline con datos perfectos”:

- El seed **sucio** inyecta exactamente una violación por cada una de las 12 validaciones.
- El E2E exige que el quality report **detecte las 12**, con las filas y los conteos exactos.
- Con el seed limpio, las 12 pasan y el pipeline llega hasta gold y produce hallazgos.
- En CI **nunca** se llama a un sitio real; el BYOD del MEF solo corre en local.

### Artefactos E2E esperados

```text
artifacts/e2e/
├─ run_manifest.json
├─ quality_report.json
├─ findings.json
├─ execution_by_entity.csv
├─ gold_summary.csv
└─ checksums.sha256
```

---

## 4. Arquitectura — reglas de boundaries

PresupuestoAbiertoPE es un **pipeline de datos local-first** con arquitectura medallion, no un servicio.

### Contextos

- `ingest`: BYOD (HTML-`.xls` de la Consulta Amigable) y seed sintético → bronze Delta.
- `transform`: bronze → silver (tipos, dedupe, catálogos, cuarentena).
- `quality`: registro explícito de las 12 validaciones → quality report.
- `analytics`: silver → gold (agregados, % ejecución, rankings, hallazgos).
- `reporting`: exports CSV, evidencia del dashboard y artefactos del run.
- `shared`: sesión Spark, config, logging, errores.

### Reglas

- La sesión Spark se crea en **un solo lugar** (`shared`); nada más instancia Spark.
- El SQL de negocio vive en `transforms` y `analytics`; no en notebooks ni en el CLI.
- Los notebooks son **wrappers delgados** (≤ 20 líneas, sin lógica) para la equivalencia con Databricks.
- Las validaciones viven en el registro de `quality`; nada de checks escondidos dentro de los transforms.
- El pipeline es **idempotente**: re-ejecutar no duplica datos (escritura por partición/overwrite).
- Los archivos BYOD del MEF **nunca** se commitean; el manifest registra su SHA-256 como procedencia.
- Los umbrales de validación se configuran, no se hardcodean.
- Los errores explícitos: una validación con nivel `fail` aborta gold; `warn` se reporta.
- Logs JSON estructurados, sin PII (los datos presupuestales son agregados institucionales).

### Prohibido

- Scrapear el MEF ni ningún WAF (`www.mef.gob.pe` está tras Incapsula). La captura BYOD se hace con el navegador real del usuario (browser MCP). Excepción documentada (18/11/2026): cuando Chrome bloquea la descarga del iframe de la Consulta Amigable (`apps5.mineco.gob.pe`, sin WAF), se permite el **GET puntual de la URL de exportación que el propio navegador generó** — una petición por archivo, iniciada por el usuario. Lo que sigue prohibido: crawlers, bucles sobre dimensiones, reintentos automáticos y cualquier request a un sitio con WAF.
- Lógica de negocio dentro de notebooks.
- Duplicar SQL entre transforms y validaciones.
- Commitear `data/raw/` o `data/medallion/`.
- Hardcodear rutas de datos o umbrales.
- Métricas inventadas: si no se midió, no se reporta.

---

## 5. Idioma y documentación

- **Documentación** (`SPECS.md`, `ROADMAP.md`, `CODESTYLE.md`, `AGENTS.md`, `README.md`): español.
- **README.en.md**: traducción al inglés para reclutadores.
- **Código, nombres de variables, tablas, columnas silver/gold, logs y commits**: inglés.
- **Bronze conserva los encabezados originales del CSV del MEF** (español); el mapping a columnas en inglés se documenta en `SPECS.md`.
- **Comentarios**: solo decisiones técnicas no obvias; en inglés.
- **Hallazgos**: en español, lenguaje neutral (baja ejecución ≠ corrupción).

---

## 6. Datos, privacidad y legal

- **Local-first:** los datos y el medallion viven en la máquina del usuario.
- **BYOD:** el usuario descarga las exportaciones oficiales (HTML-`.xls`) de la Consulta Amigable del MEF con su navegador. El pipeline no navega ni scrapea.
- **Sin PII:** son agregados presupuestales por entidad pública; no hay personas naturales.
- **Sin secretos:** `.env` fuera de Git; usar `.env.example`.
- **Procedencia:** el manifest registra el SHA-256 y la fecha del archivo BYOD procesado.
- **Atribución:** los datos son del MEF; PresupuestoAbiertoPE no está afiliado.
- **Honestidad analítica:** los hallazgos describen ejecución presupuestal, no intenciones.
- **Seed sintético:** determinista y reproducible; sin datos reales en el repo.
- **CI sin red real:** GitHub Actions corre siempre sobre seed sintético.

---

## 7. Flujo de trabajo

1. Abre el checkpoint actual en `ROADMAP.md`.
2. Escribe el E2E del comportamiento.
3. Implementa.
4. Ejecuta el E2E y genera artefactos con checksums.
5. Actualiza el checkbox de `ROADMAP.md`.
6. Actualiza `README.md` si cambian métricas, capturas o uso.
7. Ejecuta `ruff format` y `ruff check`.
8. Haz commit con conventional commits.
9. Pasa al siguiente checkpoint.

**No saltes checkpoints. No commitees con tests rojos. No dejes artefactos sin checksums.**

---

## 8. Convención de commits

```text
feat: add bronze ingestion and seed generator
feat: add silver transforms with quarantine
feat: add twelve quality validations
feat: add gold aggregations and findings
docs: add architecture decisions
test: add dirty fixture e2e scenario
chore: release v0.1.0
```

Reglas:

- Un commit por checkpoint significativo.
- Mensaje en inglés, imperativo, corto.
- No mezcles refactor grande con feature.
- Formatear antes de commitear.

---

## 9. Definición de terminado

Un checkpoint está terminado cuando:

- El E2E del checkpoint pasa.
- El artefacto correspondiente existe y es reproducible.
- `ROADMAP.md` tiene el checkbox marcado.
- `README.md` está actualizado si cambió algo visible.
- `ruff format` y `ruff check` pasan.
- No hay PII, secretos ni datos crudos commiteados.
- El commit está hecho.

El proyecto está terminado cuando:

- Todos los checkpoints técnicos del `ROADMAP.md` están marcados.
- El E2E medio-difícil pasa desde cero (seed sucio → 12/12 detectadas; seed limpio → hallazgos).
- El pipeline corre en CI sin tocar la red real.
- El usuario procesó **al menos un CSV real del MEF** (BYOD) en local.
- El informe de calidad y los hallazgos existen con datos reales.
- README y README.en.md están completos.
- La licencia y los créditos están claros.
- El tag `v0.1.0` y el release con artefactos están creados.

---

## 10. Cuándo detenerte y preguntar

Detente y propón opciones si:

- Un requisito es ambiguo.
- El formato real del archivo BYOD no coincide con el contrato de entrada.
- Un test falla y no entiendes por qué.
- Una validación produce falsos positivos con datos reales.
- Hay riesgo de PII, legal o de seguridad.
- Necesitas romper un boundary de arquitectura.
- Una decisión afecta el alcance del MVP.

No sigas “a ciegas” para parecer productivo. Es mejor una pausa corta que un commit malo.

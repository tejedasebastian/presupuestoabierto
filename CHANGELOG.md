# Changelog

Todas las fechas son locales (America/Lima).

## [1.0.0] — 2026-11-19

### Añadido

- Cobertura nacional 2025: 25 departamentos, 1,892 municipalidades, 28 archivos BYOD (25 departamentales + agregados + serie mensual).
- Contexto departamental en el parser y en el manifiesto; `min_rows` solo se exige al grano mensual, para no descartar departamentos pequeños como Callao (7 municipalidades).
- `department` en gold y en `execution_by_entity.csv`; columna calculada `Municipalidad` única (desambigua homónimos con departamento/código).
- Dashboard nacional de 2 páginas: bottom-10 nacional, 6 genéricas principales, bottom-7 de 25 departamentos, tabla de calidad y ranking de 1,892 municipalidades con filtro por departamento + búsqueda.
- `docs/data-dictionary.md`, `docs/architecture.md` y kit de test con usuario externo.
- Run nacional: 1,939 filas, 1,892 municipalidades, 12/12 validaciones, 196 alertas, promedio 79.5%, peor 13.2% (Eleazar Guzmán Barrón, Áncash), 129.4 s.

### Notas

- El `.pbix` nacional se guarda en Power BI Desktop a partir del PBIP; el PBIP es la fuente reproducible.
- No se publica en Power BI Service en v1.0.

## [0.1.0] — 2026-11-18

### Añadido

- Ingesta BYOD de las exportaciones oficiales de la Consulta Amigable del MEF (4 archivos 2025).
- Medallion bronze → silver → gold en Delta Lake, con cuarentena estructural y conservación `bronze = silver + cuarentena`.
- Registro propio de 12 validaciones de calidad con gate que bloquea gold.
- Gold por municipalidad, genérica y departamento, con rankings y hallazgos neutrales.
- Exportes CSV con checksums y `run_manifest.json` con la procedencia SHA-256 de los archivos fuente.
- Dashboard PBIP de 2 páginas, modelo TMDL de 4 tablas y 12 medidas, tema Civic Data Editorial y capturas validadas en Power BI Desktop.
- E2E con seed limpio, seed sucio (12/12 detectadas) y volumen (1,000 entidades en la suite; 12,800 en CI).
- CI en GitHub Actions con jobs de pipeline y volumen.
- Documentación bilingüe, ADRs, hallazgos 2025, performance y notebook de equivalencia Databricks.

### Notas

- Los archivos crudos del MEF no se distribuyen; solo se publican artefactos derivados y sus hashes.
- El `.pbix` final se guarda manualmente en Power BI Desktop a partir del PBIP.
- No se publica en Power BI Service en v0.1.

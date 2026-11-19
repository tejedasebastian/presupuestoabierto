# Changelog

Todas las fechas son locales (America/Lima).

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

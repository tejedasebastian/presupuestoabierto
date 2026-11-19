# Dashboard — PresupuestoAbiertoPE 2025

> **Estado:** PBIP validado y revisado visualmente en Power BI Desktop (18/11/2026).
> **Entrega:** el usuario abre el PBIP, actualiza el modelo y guarda el `.pbix` final.
> **No se publica en Power BI Service en v0.1.**

## Qué contiene

```text
dashboard/
├── PresupuestoAbiertoPE.pbip
├── PresupuestoAbiertoPE.Report/        # PBIR: 2 páginas y 17 visuales
├── PresupuestoAbiertoPE.SemanticModel/ # TMDL: 4 tablas y 12 medidas
└── build_report.mjs                    # regenera las páginas y visuales
```

### Páginas

1. **Panorama — “La inversión municipal se queda atrás de las planillas”**
   - 4 tarjetas: 171 municipalidades, 84.7% de ejecución promedio, 9 alertas <60%, brecha de 21.2 pp entre planillas e inversión.
   - Bottom-10 municipalidades por ejecución (barras ámbar bajo el umbral de 60%).
   - Ejecución por 6 genéricas principales (Inversión en teal oscuro; activos financieros omitido por ser un artefacto esperado de 0%).
   - Bottom-7 de 25 departamentos por ejecución.
   - Tabla de evidencia de calidad del run.
2. **Ranking completo — “Las 171 municipalidades de Lima”**
   - Selector desplegable con búsqueda por municipalidad.
   - Tabla ordenada por puesto (1 = mayor ejecución) con PIM, devengado y % de ejecución.
   - Botón de regreso al panorama.

### Modelo semántico

| Tabla | Filas | Origen |
|---|---:|---|
| `ExecutionByEntity` | 171 | `artifacts/e2e/execution_by_entity.csv` |
| `CategorySummary` | 10 | `artifacts/e2e/category_summary.csv` |
| `DepartmentSummary` | 25 | `artifacts/e2e/department_summary.csv` |
| `QualitySummary` | 5 | `artifacts/e2e/gold_summary.csv` |

- Las tablas de contexto están **desconectadas** de `ExecutionByEntity` a propósito: son agregados nacionales y filtrarlos por municipalidad sería engañoso.
- El parámetro `DataFolder` apunta a `artifacts/e2e/` en esta máquina. Si mueves el proyecto, actualízalo en `PresupuestoAbiertoPE.SemanticModel/definition/expressions.tmdl`.

## Cómo abrirlo y guardar el `.pbix`

1. Abre `dashboard/PresupuestoAbiertoPE.pbip` en Power BI Desktop.
2. En la primera apertura, Desktop puede mostrar “una o varias columnas calculadas deben actualizarse manualmente” y tablas vacías: los datos importados aún no se procesaron. Ejecuta **Inicio → Actualizar** (o `RefreshWithXMLA` con `refreshType: Full` desde el MCP de modelado) y espera a que termine.
3. Verifica que el panorama muestre **171**, **84.7%**, **9** y **21.2 pp**. Si aparecen `--`, el refresh no terminó.
4. Guarda una copia como `.pbix` con **Archivo → Guardar como**. El PBIP queda como fuente reproducible; el `.pbix` es la entrega manual.

> La validación visual de este repositorio se hizo con el modelo refrescado y el panel de filtros cerrado. Las capturas están en `docs/screenshots/`.

## Evidencia visual

![Panorama](screenshots/panorama.png)

![Ranking completo](screenshots/ranking.png)

## Validación

- `powerbi-report-author validate dashboard/PresupuestoAbiertoPE.Report` → **0 errores, 0 warnings**.
- `powerbi-report-author preview ... --host desktop --all-pages --scale 2` → 2 páginas capturadas, sin fallos.
- Modelo recargado desde TMDL y refrescado: 4 tablas, 12 medidas, 171 municipalidades.
- La tabla de calidad no tiene fila Total; el ranking tampoco. Los encabezados numéricos están alineados a la derecha.

## Limitaciones

- La muestra municipal cubre solo el departamento de Lima (171 de ~1,900 municipalidades del país); el resto aparece agregado por departamento.
- El año 2025 se consultó el 18/11/2026; el SIAF puede registrar ajustes posteriores.
- Los nombres con ruido de codificación de la fuente se preservan.
- El dashboard describe ejecución presupuestal, no intenciones ni causas.

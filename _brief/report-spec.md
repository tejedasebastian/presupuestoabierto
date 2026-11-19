# Report Spec — PresupuestoAbiertoPE 2025

## Report identity
- Report name: PresupuestoAbiertoPE — Ejecución municipal 2025
- Semantic model: local PBIP semantic model `PresupuestoAbiertoPE.SemanticModel` (TMDL, CSV imports)
- Audience: external / portfolio — periodistas de datos, comunidad de datos y reclutadores técnicos
- Primary purpose: mostrar qué municipalidades del departamento de Lima ejecutan menos su presupuesto 2025 y con qué evidencia de calidad
- Delivery target: **Local PBIP only** (el usuario lo guarda como `.pbix` en Power BI Desktop; sin publish a Fabric)

## Semantic model binding
- Entry mode: Local Model (modelo TMDL creado en el mismo PBIP)
- Model name: PresupuestoAbiertoPE
- connectionString: byPath ../PresupuestoAbiertoPE.SemanticModel

## User decisions and constraints
- Scope: dashboard sobre los artefactos reales del pipeline (BYOD MEF 2025): 2 páginas
- Page count: 2
- Interactivity: botones de navegación entre páginas; búsqueda por municipalidad (slicer search) en el ranking; sin drillthrough
- Design direction: editorial cívico, sobrio, con umbral de alerta visible; sin colores partidarios
- Publishing: no (solo PBIP local; el usuario lo abre y guarda como .pbix)
- Tooling: skill `powerbi-report-cli` (authoring) + MCP `powerbi-modeling` (modelo semántico) + Power BI Desktop del usuario para la validación visual
- Model edit permissions: totales (modelo local nuevo)
- Accessibility: contraste WCAG AA, alt text en cada visual, el umbral no se comunica solo por color (valor etiquetado)
- Data caveats: 171 municipalidades del depto. de Lima de ~1,900 nacionales; los agregados por categoría/departamento son nacionales (tablas desconectadas, sin relación con la tabla de entidades); nombres con ruido de codificación de la fuente se preservan

## Narrative
- Core story: el gasto rígido (planillas) se ejecuta; la inversión no; un puñado de distritos pequeños de la sierra de Lima concentra la baja ejecución (peor caso: Colonia 21.8%)
- Audience promise: cifras verificables (12/12 validaciones, checksums) sin acusar a nadie: describimos ejecución, no intenciones
- Key questions answered: ¿cuánto se ejecuta en promedio? ¿quiénes ejecutan menos? ¿qué categoría queda atrás? ¿qué departamentos ejecutan menos? ¿qué tan confiables son los números?

## Design identity
- Tone: `Civic Data Editorial` — tinta azul marino, acento teal, ámbar solo para alertas, numerales tabulares, aire generoso
- Signature: barras horizontales ordenadas de peor a mejor con el umbral de 60% marcado en ámbar

## Page plan

1. Panorama — “La inversión municipal se queda atrás de las planillas”
   - Archetype: Executive Summary
   - Layout variant: A — el hallazgo es un ranking + dos contextos; landing ejecutivo con hero de ranking
   - Purpose: responder en 10 segundos quién ejecuta menos y por qué importa
   - Visuals: 4 KPI cards (municipalidades, ejecución promedio, alertas <60%, brecha planillas-inversión), hero bottom-10 municipalidades, barras por categoría, barras por departamento, tabla compacta de evidencia de calidad
   - Fields/measures: `ExecutionByEntity[Municipalidades]`, `[Ejecución promedio]`, `[Alertas <60%]`, `[Brecha planillas-inversión]`, `[Ejecución %]` (categorías/departamentos), `QualitySummary[metric/value]`
   - Slicers/interactions: sin slicers; nota de fuente en la banda superior; botón “Ranking completo”

2. Ranking completo — “Ranking completo: las 171 municipalidades de Lima”
   - Archetype: Analytical Canvas
   - Layout variant: B — tabla de grano completo con búsqueda, sin rail para maximizar superficie de lectura
   - Purpose: localizar una municipalidad concreta y comparar su ejecución
   - Visuals: slicer de búsqueda (entity_name), tabla ordenada por rank con PIM, devengado y %
   - Fields/measures: `ExecutionByEntity[rank, entity_name, pim_total, accrued_total, execution_pct]`
   - Slicers/interactions: búsqueda por nombre (dropdown con search); botón “Panorama”

## Design system summary
- Theme: base.json adaptado a Civic Data Editorial; fondo #F3F2F1, tinta #0F172A, teal #0F766E, ámbar de alerta #B45309
- Color semantics: ejecución = teal (#0F766E); alertas/umbral = ámbar (#B45309); el resto gris tinta
- Typography: display = Segoe UI Semibold; body = Segoe UI; numerales tabulares en tablas
- Layout: grid 12×12, canvas 1920×1080, gutter 24, snap 8
- Accessibility: AA en todos los pares texto/fondo; cada visual con alt text; umbral etiquetado en texto además del color

## Model requirements
- Existing measures: ninguno (modelo nuevo)
- New measures:
  - `ExecutionByEntity[Municipalidades] = COUNTROWS(ExecutionByEntity)`
  - `ExecutionByEntity[Ejecución promedio] = AVERAGE(ExecutionByEntity[execution_pct])`
  - `ExecutionByEntity[Alertas <60%] = CALCULATE(COUNTROWS(ExecutionByEntity), ExecutionByEntity[execution_pct] < 60)`
  - `CategorySummary[Ejecución %] = DIVIDE(SUM(CategorySummary[accrued]), SUM(CategorySummary[pim])) * 100`
  - `DepartmentSummary[Ejecución %] = DIVIDE(SUM(DepartmentSummary[accrued]), SUM(DepartmentSummary[pim])) * 100`
  - `CategorySummary[Brecha planillas-inversión] = CALCULATE([Ejecución %], CategorySummary[label] = "PERSONAL Y OBLIGACIONES SOCIALES") - CALCULATE([Ejecución %], CategorySummary[label] = "ADQUISICION DE ACTIVOS NO FINANCIEROS")`
- New calculated columns: ninguna
- Relationship/sort requirements: sin relaciones (tablas de contexto desconectadas); ranking ordenado por `rank`

## Canonical design contract

```yaml
Design Brief:
  generated_by: powerbi-report-cli
  contract_version: 1
  mode: greenfield
  design_identity:
    tone: "Civic Data Editorial — navy ink, teal accent, amber alerts only, tabular numerals, generous whitespace"
    signature: "horizontal bars sorted worst-to-best with the 60% alert threshold marked in amber"
  archetype: Executive
  navigation_model: buttons
  color_map:
    - measure: ExecutionByEntity[Ejecución promedio]
      color: "#0F766E"
      tint: "#D1FAE5"
    - measure: ExecutionByEntity[Alertas <60%]
      color: "#B45309"
      tint: "#FEF3C7"
    - measure: CategorySummary[Ejecución %]
      color: "#0F766E"
      tint: "#D1FAE5"
    - measure: DepartmentSummary[Ejecución %]
      color: "#0F766E"
      tint: "#D1FAE5"
  pages:
    - name: "La inversión municipal se queda atrás de las planillas"
      role: landing
      archetype: Executive
      layout_variant: A
      variant_rationale: "The story is one ranking signal plus two context cuts; an executive landing with a ranking hero answers it fastest."
      navigation:
        - element: button
          action: PageNavigation
          target: "Ranking completo: las 171 municipalidades de Lima"
          label: "Ranking completo"
      page_background: "#F3F2F1"
      layout_summary: "KPI strip on top; ranking hero left; category and department context stacked right; compact evidence strip at the bottom."
      layout_contract:
        canvas:
          width: 1920
          height: 1080
          margin: 32
          gutter: 24
          snap: 8
        grid:
          columns: 12
          rows: 12
          regions:
            header: [1,  1,  9,  2]
            meta:   [9,  1, 13,  2]
            kpis:   [1,  2, 13,  4]
            hero:   [1,  4,  7, 10]
            cats:   [7,  4, 13,  7]
            depts:  [7,  7, 13, 10]
            detail: [1, 10, 13, 13]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: "La inversión municipal se queda atrás de las planillas"
            purpose: "State the page insight before any chart."
          - id: source_note
            region: meta
            kind: textbox
            text: "Fuente: MEF · Consulta Amigable 2025 · 171 municipalidades (depto. Lima) · 12/12 validaciones"
            purpose: "Provenance and quality note in the header band."
          - id: kpi_entities
            region: kpis
            kind: cardVisual
            purpose: "How many municipalities enter the analysis?"
            field_bindings: ExecutionByEntity[Municipalidades]
            color_strategy: measure_match
            slot: 1
            of: 4
          - id: kpi_avg
            region: kpis
            kind: cardVisual
            purpose: "What is the average execution?"
            field_bindings: ExecutionByEntity[Ejecución promedio]
            color_strategy: measure_match
            slot: 2
            of: 4
          - id: kpi_alerts
            region: kpis
            kind: cardVisual
            purpose: "How many municipalities fall below the 60% alert threshold?"
            field_bindings: ExecutionByEntity[Alertas <60%]
            color_strategy: measure_match
            slot: 3
            of: 4
          - id: kpi_gap
            region: kpis
            kind: cardVisual
            purpose: "How far is investment execution behind payroll execution?"
            field_bindings: CategorySummary[Brecha planillas-inversión]
            color_strategy: measure_match
            insight_basis: "Points of gap between payroll (94.1%) and investment (72.9%) execution."
            slot: 4
            of: 4
          - id: bottom10_chart
            region: hero
            kind: barChart
            purpose: "Which municipalities execute the least?"
            field_bindings: { Category: ExecutionByEntity[entity_name], Y: ExecutionByEntity[execution_pct] }
            sort_policy: value_asc
            color_strategy: semantic
            insight_basis: "Bottom-10 by execution_pct with the 60% threshold highlighted in amber."
            comparison_basis: "Alert threshold 60%"
          - id: categories_chart
            region: cats
            kind: barChart
            purpose: "Which spending category lags behind?"
            field_bindings: { Category: CategorySummary[label], Y: CategorySummary[Ejecución %] }
            sort_policy: value_asc
            color_strategy: measure_match
          - id: departments_chart
            region: depts
            kind: barChart
            purpose: "Which departments execute the least?"
            field_bindings: { Category: DepartmentSummary[label], Y: DepartmentSummary[Ejecución %] }
            sort_policy: value_asc
            color_strategy: measure_match
          - id: quality_table
            region: detail
            kind: tableEx
            purpose: "What quality evidence backs these numbers?"
            field_bindings: [QualitySummary[metric], QualitySummary[value]]
            sort_policy: natural_order
        space_audit:
          content_cell_count: 132
          placed_cell_count: 132
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region:
            name: hero
            pct_of_content: 27
          balance_rationale: "Ranking hero and evidence strip share 27% each; both context charts 14% each; the KPI strip 18%. No bare card hero; the ranking explains the headline."
    - name: "Ranking completo: las 171 municipalidades de Lima"
      role: detail
      archetype: Analytical
      layout_variant: B
      variant_rationale: "Full-grain list with search needs maximum table surface; splitting it would hurt readability of 171 rows."
      navigation:
        - element: button
          action: Back
          label: "Panorama"
      page_background: "#F3F2F1"
      layout_summary: "Search band under the header; the complete ranking table fills the page."
      layout_contract:
        canvas:
          width: 1920
          height: 1080
          margin: 32
          gutter: 24
          snap: 8
        grid:
          columns: 12
          rows: 12
          regions:
            header:  [1, 1,  9,  2]
            meta:    [9, 1, 13,  2]
            filters: [1, 2, 13,  3]
            ranking: [1, 3, 13, 13]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: "Ranking completo: las 171 municipalidades de Lima"
            purpose: "State the page purpose before the table."
          - id: source_note
            region: meta
            kind: textbox
            text: "Ordenado por % de ejecución · Fuente: MEF 2025"
            purpose: "Provenance note in the header band."
          - id: entity_search
            region: filters
            kind: slicer
            field_bindings: ExecutionByEntity[entity_name]
            slicer_type: dropdown
            purpose: "Find one municipality among 171."
          - id: ranking_table
            region: ranking
            kind: tableEx
            purpose: "Where does each municipality rank in execution?"
            field_bindings: [ExecutionByEntity[rank], ExecutionByEntity[entity_name], ExecutionByEntity[pim_total], ExecutionByEntity[accrued_total], ExecutionByEntity[execution_pct]]
            sort_policy: natural_order
        space_audit:
          content_cell_count: 120
          placed_cell_count: 120
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region:
            name: ranking
            pct_of_content: 100
          balance_rationale: "The page IS the full ranking: a single searchable table at full grain is the page question; splitting the surface would shrink 171 rows below readable density."
  interaction_pattern:
    drill_targets: []
    cross_filter_rules: "None — context tables are disconnected summary tables; filtering them by entity would be misleading."
  accessibility:
    alt_text_strategy: "chart+structure — every visual states what it shows and its main finding"
    contrast_notes: "Amber #B45309 on #F3F2F1 passes AA for large text; alert values are also labeled numerically, never color-only."
  theme:
    base: "references/design/assets/base.json adapted to Civic Data Editorial"
    user_overrides: "No user brand to preserve; keep base safeguards (textbox paddings, hidden headers, table grow-to-fit)."
```

## Implementation notes

- Model changes: crear el `.SemanticModel` (TMDL) con 4 tablas importadas desde `artifacts/e2e/*.csv` (ExecutionByEntity, CategorySummary, DepartmentSummary, QualitySummary) y las medidas listadas arriba (MCP `powerbi-modeling`).
- PBIR/report authoring: 2 páginas + tema adaptado, según el contrato canónico (skill `powerbi-report-cli`, modo authoring).
- Validation: PBIR válido, JSON parseable, apertura en Power BI Desktop, screenshot de ambas páginas.
- Desktop screenshot verification: el usuario tiene Desktop instalado; el preview local se intenta y, si el host desktop no es automatizable, las capturas quedan como paso manual del usuario.
- Publishing boundary: solo local; el usuario guarda `.pbix`.
- Risks: nombre con mojibake en la fuente (se preserva); tablas desconectadas (documentado); fuentes con 0% (activos financieros) rotuladas como artefacto esperado.

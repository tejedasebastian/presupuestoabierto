# Hallazgos 2025 — Ejecución presupuestal de las municipalidades de Lima

> **Estado:** borrador con datos reales (generado por el pipeline el 18/11/2026).
> **Fuente:** Consulta Amigable de Ejecución del Gasto del MEF (SIAF), año 2025.
> **Muestra:** 171 municipalidades del departamento de Lima, más contexto nacional (25 departamentos, 10 genéricas).
> **Reproducible:** `python -m presupuesto run --source byod` con los archivos de `data/raw/` (procedencia y hashes en `data/raw/README.md` y en `artifacts/e2e/run_manifest.json`).

---

## 1. Método (en una frase)

Se procesaron los cuatro exports oficiales con el pipeline medallion (bronze → silver → gold), pasaron las **12/12 validaciones de calidad** y se calcularon porcentajes de ejecución como `devengado / PIM` por municipalidad, genérica y departamento. Los números de este documento se regeneran con un comando; no se editaron a mano.

## 2. Panorama

| Métrica | Valor |
|---|---|
| Municipalidades analizadas (depto. Lima) | 171 |
| Ejecución promedio | **84.7%** |
| Mejor ejecución | 100.0% |
| Peor ejecución | **21.8%** |
| Municipalidades bajo el umbral de alerta (< 60%) | **9** |
| Registros procesados en el run | 218 |

## 3. Las diez municipalidades con menor ejecución

| # | Municipalidad | Ejecución | PIM (S/) |
|---|---|---|---|
| 1 | Municipalidad Distrital de Colonia | **21.8%** | 15.9 M |
| 2 | Municipalidad Distrital de Cacra | 34.7% | 3.1 M |
| 3 | Municipalidad Distrital de Putinza | 45.5% | 4.2 M |
| 4 | Municipalidad Provincial de Yauyos | 49.4% | 19.0 M |
| 5 | Municipalidad Distrital de Viñac | 54.0% | 3.2 M |
| 6 | Municipalidad Distrital de Lincha | 56.7% | 2.2 M |
| 7 | Municipalidad Distrital de Madeán | 59.0% | 3.0 M |
| 8 | Municipalidad Distrital de Sumbilca | 59.4% | 4.6 M |
| 9 | Municipalidad Distrital de Azángaro | 59.8% | 5.6 M |
| 10 | Municipalidad Distrital de Pachangara | 61.0% | 9.2 M |

**Lectura:** las diez menores ejecuciones se concentran en distritos pequeños de la sierra de Lima (provincia de Yauyos y alrededores), con PIM de S/ 2–19 millones. Que Yauyos (capital provincial, PIM S/ 19 M) esté en 49.4% sugiere un problema de gestión provincial, no solo distrital.

## 4. Categorías del gasto (contexto nacional, municipalidades del Perú)

| Genérica | Ejecución |
|---|---|
| Adquisición de activos financieros | **0.0%** |
| Adquisición de activos no financieros (inversión) | 72.9% |
| Donaciones y transferencias | 76.3% |
| Personal y obligaciones sociales | 94.1% |

**Lectura:** el gasto rígido (planillas) se ejecuta casi completo; la **inversión** (activos no financieros) queda 21 puntos por debajo. La genérica de activos financieros en 0% es un artefacto esperable (las municipalidades casi no usan ese instrumento), no una alerta de gestión.

## 5. Departamentos (contexto nacional)

| Departamento | Ejecución |
|---|---|
| Áncash | **68.7%** |
| Pasco | 71.1% |
| Ica | 71.2% |
| … | … |
| Lima (departamento) | 87.4% |

**Lectura:** el ranking departamental reproduce el patrón conocido: sierra y zonas rurales ejecutan menos que Lima. El departamento de Lima queda 7 puntos sobre el promedio municipal nacional.

## 6. Lo que el pipeline validó con datos reales

- **12/12 validaciones en verde**, incluida la #11: la suma de los 12 meses de Miraflores cuadra exactamente con su total anual (S/ 362,575,233). Esto confirma que la vista mensual exporta devengado del mes, no acumulado.
- **Procedencia verificable:** los SHA-256 de los cuatro archivos quedaron en `run_manifest.json`; el run completo tomó 112.9 s en local.

## 7. Limitaciones (honestas)

- La muestra municipal cubre **solo el departamento de Lima** (171 de ~1,900 municipalidades del país); el resto aparece agregado por departamento. No es un ranking nacional municipal.
- El año 2025 fue consultado el 18/11/2026; el SIAF puede registrar ajustes posteriores en el cierre anual.
- Los porcentajes son `devengado / PIM`; un PIM alto con devengado bajo puede reflejar también problemas de ejecución de inversión, no solo de gestión.
- La fuente tiene ruido de codificación en algunos nombres (por ejemplo, «Viñac» aparece mangled en el export original). Se preservan tal cual llegan.
- Describimos ejecución presupuestal, **no intenciones ni causas**: este documento no acusa a ninguna entidad.

## 8. Cómo regenerarlo

```powershell
cd presupuestoabierto
python -m presupuesto run --source byod
# → artifacts/e2e/findings.json, execution_by_entity.csv, gold_summary.csv
```

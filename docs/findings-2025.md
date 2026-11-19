# Hallazgos 2025 — Ejecución presupuestal de las municipalidades del Perú

> **Estado:** cifras reales generadas por el pipeline el 19/11/2026.
> **Fuente:** Consulta Amigable de Ejecución del Gasto del MEF (SIAF), año 2025.
> **Muestra:** **1,892 municipalidades de 25 departamentos** (universo municipal de la Consulta Amigable), más los agregados nacionales por departamento y genérica.
> **Reproducible:** `python -m presupuesto run --source byod` con los 28 archivos de `data/raw/` (procedencia en `data/raw/README.md`; hashes en `artifacts/e2e/run_manifest.json`).

---

## 1. Método (en una frase)

Se procesaron 28 exportaciones oficiales (25 departamentos + agregados + serie mensual) con el pipeline medallion (bronze → silver → gold), pasaron las **12/12 validaciones de calidad** y se calcularon porcentajes de ejecución como `devengado / PIM` por municipalidad, genérica y departamento. Los números de este documento se regeneran con un comando; no se editaron a mano.

## 2. Panorama nacional

| Métrica | Valor |
|---|---|
| Municipalidades analizadas | **1,892** |
| Departamentos | 25 |
| Ejecución promedio | **79.5%** |
| Mejor ejecución | 100.0% |
| Peor ejecución | **13.2%** |
| Municipalidades bajo el umbral de alerta (< 60%) | **196** |
| Registros procesados en el run | 1,939 |
| Validaciones de calidad | **12/12** |

## 3. Las diez municipalidades con menor ejecución

| # | Municipalidad | Departamento | Ejecución | PIM (S/) |
|---|---|---|---|---:|---:|
| 1 | Municipalidad Distrital de Eleazar Guzmán Barrón | Áncash | **13.2%** | 20.5 M |
| 2 | Municipalidad Distrital de Tapacocha | Áncash | 16.4% | 9.2 M |
| 3 | Municipalidad Distrital de Coris | Áncash | 20.2% | 16.6 M |
| 4 | Municipalidad Distrital de Huacllan | Áncash | 20.4% | 5.1 M |
| 5 | Municipalidad Distrital de Mangas | Áncash | 21.2% | 12.9 M |
| 6 | Municipalidad Distrital de Colonia | Lima | 21.8% | 15.9 M |
| 7 | Municipalidad Distrital de Santa Rosa | Áncash | 23.0% | 7.7 M |
| 8 | Municipalidad Distrital de Huata | Áncash | 26.4% | 8.3 M |
| 9 | Municipalidad Distrital de Bernal | Piura | 27.3% | 82.3 M |
| 10 | Municipalidad Distrital de Eten | Lambayeque | 28.6% | 15.0 M |

**Lectura:** la mitad inferior del ranking nacional se concentra en distritos pequeños de Áncash (7 de las 10), con PIM de S/ 5–20 millones. Aparecen también una municipalidad de Lima (Colonia), una de Piura (Bernal, con PIM S/ 82.3 M) y una de Lambayeque (Eten). El caso de Bernal es el de mayor PIM entre los diez: no es solo un problema de distritos minúsculos.

## 4. Categorías del gasto (contexto nacional)

| Genérica | Ejecución |
|---|---|
| Adquisición de activos financieros | **0.0%** |
| Adquisición de activos no financieros (inversión) | **72.9%** |
| Otros gastos | 84.7% |
| Bienes y servicios | 88.8% |
| Transferencias | 90.2% |
| Servicio de la deuda pública | 92.3% |
| Personal y obligaciones sociales | **94.1%** |

**Lectura:** el gasto rígido (planillas) se ejecuta casi completo; la **inversión** queda 21.2 puntos por debajo. La genérica de activos financieros en 0% es un artefacto esperado (las municipalidades casi no usan ese instrumento), no una alerta de gestión; el dashboard la omite y lo documenta.

## 5. Departamentos (contexto nacional)

| Departamento | Ejecución |
|---|---|
| Áncash | **68.7%** |
| Pasco | 71.1% |
| Ica | 71.2% |
| Madre de Dios | 72.9% |
| La Libertad | 74.7% |
| Ayacucho | 75.3% |
| Lambayeque | 76.1% |
| … | … |
| Lima | 87.4% |

**Lectura:** el ranking departamental reproduce el patrón conocido: sierra y zonas rurales ejecutan menos que Lima. Áncash, el departamento con más municipalidades en el bottom-10, es también el de menor ejecución agregada (68.7%).

## 6. Lo que el pipeline validó con datos reales

- **12/12 validaciones en verde**, incluyendo la #11: la suma de los 12 meses de Miraflores cuadra con su total anual.
- **Procedencia verificable:** los SHA-256 de los 28 archivos quedaron en `run_manifest.json`; el run nacional tomó 129.4 s en local.
- **Cobertura:** 1,892 municipalidades, 1,939 filas (anuales + agregados + serie mensual), 0 filas en cuarentena.

## 7. Limitaciones (honestas)

- Un solo año (2025) y solo gastos.
- 1,892 municipalidades del universo municipal de ~1,900; la fuente puede variar en el cierre anual.
- La serie mensual solo está disponible para Miraflores; el resto del análisis es anual.
- El año 2025 se consultó el 18–19/11/2026; el SIAF puede registrar ajustes posteriores.
- La fuente tiene ruido de codificación en algunos nombres; se preservan tal cual llegan.
- Describimos ejecución presupuestal, **no intenciones ni causas**: este documento no acusa a ninguna entidad.

## 8. Cómo regenerarlo

```powershell
cd presupuestoabierto
python -m presupuesto run --source byod
# → artifacts/e2e/findings.json, execution_by_entity.csv, gold_summary.csv
```

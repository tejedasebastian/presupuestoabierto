# Performance — mediciones reales

> Todas las cifras son medidas por el propio pipeline (`timings_ms` en
> `run_manifest.json`). No hay estimaciones.

## Corridas locales (Windows, Spark 4.2, driver 512m)

| Run | Filas | Tiempo total |
|---|---:|---:|
| Seed clean (105 filas) | 105 | ~60 s (incluye arranque de Spark) |
| BYOD Lima v0.1 (4 exports del MEF, 218 filas) | 218 | 112.9 s |
| **BYOD nacional v1.0 (28 exports, 1,939 filas)** | **1,939** | **129.4 s** |
| Volume 1,000 entidades | 73,000 | ~3–5 min según la sesión |
| Volume 12,800 entidades (CI) | ~934,000 | job `volume` de GitHub Actions |

## Desglose del run BYOD nacional

| Fase | ms |
|---|---:|
| Bronze | 34,683 |
| Silver | 30,320 |
| Calidad (12 checks) | 20,939 |
| Gold | 25,609 |
| **Total** | **129,416** |

El costo local está dominado por el arranque del JVM y el tamaño del driver,
no por el volumen: 1,939 filas reales tardan lo mismo que miles de filas
sintéticas en la misma sesión. El salto de 218 a 1,939 filas añadió ~16 s
frente al run de Lima.

## Escala nacional (CI, ubuntu, 7 GB)

El job `volume` de GitHub Actions corre **12,800 entidades ≈ 933,700 filas**
(entidad × genérica × mes + anual) por el medallion completo y publica
`volume_summary.json` como artefacto del run. Ese número es la referencia de
escala del pipeline; se consulta en la pestaña Actions del repositorio.

Nota de honestidad: la escala nacional de municipalidades del Perú es
~1,900 entidades. El modo volumen usa el cruce sintético
entidad × categoría × mes porque la Consulta Amigable **no exporta ese cruce
en bloque** (habría que hacer 25 exportaciones por departamento). El volumen
prueba el medallion a escala; no afirma que exista una fuente con ese detalle.

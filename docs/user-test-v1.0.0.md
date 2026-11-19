# Test con usuario externo — PresupuestoAbiertoPE v1.0.0

> **Estado:** kit listo; pendiente de ejecutar con una persona externa (periodista, analista o estudiante).
> **Duración:** 20–25 minutos.
> **Objetivo:** validar que el dashboard nacional se entiende sin explicación previa y que las cifras se pueden usar para una nota o un análisis.

## Perfil sugerido

- Periodista de datos, analista de políticas públicas o estudiante de últimos ciclos.
- No debe haber participado en el desarrollo.
- No necesita saber Power BI; solo abrir el `.pbix` o mirar las capturas.

## Material

- `dashboard/PresupuestoAbiertoPE.pbip` (o el `.pbix` final).
- Capturas: `docs/screenshots/panorama.png`, `docs/screenshots/ranking.png`.
- `docs/findings-2025.md` para contrastar.

## Guion (no leer las respuestas)

1. **Apertura (2 min):** “Este es un tablero de ejecución presupuestal municipal 2025. Míralo como si fueras a escribir una nota. No hay respuestas correctas.”
2. **Panorama (5 min):** pide que diga en voz alta qué le llama la atención y qué cree que significan los cuatro números grandes.
3. **Bottom-10 (3 min):** “¿Qué municipalidades ejecutan menos? ¿Qué tienen en común?”
4. **Categorías (3 min):** “¿Qué categoría queda atrás? ¿Qué NO concluirías con este gráfico?”
5. **Departamentos (3 min):** “¿Qué departamentos ejecutan menos? ¿Te sorprende alguno?”
6. **Calidad (2 min):** “¿Qué evidencia tienes de que estos números son confiables?”
7. **Ranking (5 min):** pide buscar una municipalidad concreta, filtrar por un departamento y leer su puesto/PIM/devengado.
8. **Cierre (3 min):** “¿Qué te faltó? ¿Qué no entendiste? ¿Lo usarías en una nota?”

## Preguntas de feedback

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Cuál es el mensaje principal del panorama? | |
| 2 | ¿Qué municipalidad es la peor y en qué departamento está? | |
| 3 | ¿Qué categoría queda más atrás y cuánto? | |
| 4 | ¿Qué departamento tiene la menor ejecución? | |
| 5 | ¿Qué evidencia de calidad viste? | |
| 6 | ¿Pudiste encontrar una municipalidad en el ranking? | |
| 7 | ¿Qué término o gráfico no entendiste? | |
| 8 | ¿Qué agregarías para una nota o análisis? | |
| 9 | Del 1 al 5, ¿qué tan confiable te pareció? | |
| 10 | ¿Lo recomendarías a un colega? ¿Por qué? | |

## Registro

| Fecha | Perfil | Entendió el mensaje | Encontró la municipalidad | Confianza 1–5 | Observaciones |
|---|---|---|---|---|---|
| | | | | | |

## Criterios de éxito

- Identifica a **Eleazar Guzmán Barrón (Áncash, 13.2%)** como el peor caso sin ayuda.
- Reconoce **Inversión (72.9%)** como la categoría que queda atrás.
- Encuentra una municipalidad con el buscador y lee su puesto/PIM/devengado.
- Menciona al menos una pieza de evidencia de calidad (12/12, checksums, tabla de calidad).
- No confunde “baja ejecución” con “corrupción”.

## Qué hacer con el feedback

- Si no identifica el mensaje, ajustar títulos/notas, no los datos.
- Si no encuentra una municipalidad, revisar el buscador y el ancho de la tabla.
- Si desconfía de las cifras, reforzar la nota de procedencia y la tabla de calidad.
- Registrar cambios en `CHANGELOG.md` y volver a capturar si cambia la UI.

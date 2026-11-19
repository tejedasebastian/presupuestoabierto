# ADR-001 — BYOD asistido + seed sintético

## Estado

Aceptado (18/11/2026).

## Contexto

El proyecto necesita la ejecución presupuestal municipal del MEF. Verificación real del 17–18/11/2026:

- `www.mef.gob.pe` y `apps.mef.gob.pe` están tras **Incapsula** (WAF anti-bot): toda ruta devuelve un shell de 212 bytes.
- El CKAN nacional no publica el consolidado municipal del MEF.
- La **Consulta Amigable real** vive en `apps5.mineco.gob.pe/transparencia/Navegador/Navegar_7.aspx` (dominio antiguo del MEF, sin WAF), hallada vía Bing.
- La app corre en un iframe; Chrome de la máquina del usuario bloquea su descarga (archivos `.tmp` efímeros que desaparecen).

## Decisión

1. **BYOD asistido:** la captura se hace con el navegador real del usuario (browser MCP), navegando el drill-down oficial: Nivel de Gobierno → GOBIERNOS LOCALES → MUNICIPALIDADES → Departamento → Municipalidad.
2. Cuando Chrome bloquea la descarga del iframe, se permite el **GET puntual de la URL de exportación que el propio navegador generó** (es un GET sin estado, una petición por archivo). Sin crawlers, sin bucles, sin reintentos automáticos, nada contra un WAF.
3. **Seed sintético determinista** para CI y E2E: CI nunca toca la red.
4. Los archivos BYOD no se commitean; `data/raw/README.md` documenta URLs de exportación, parámetros de estado y hashes SHA-256.

## Consecuencias

### Positivas

- Datos oficiales reales sin scraping ni forzar WAFs.
- CI 100% reproducible y sin red.
- Procedencia auditable (hash + URL + fecha por archivo).

### Negativas

- La captura requiere interacción (navegación o GET manual de la URL exportada).
- El cross completo `pliego × genérica × mes` no es exportable en bulk por la app; el set BYOD cubre los tres ejes por separado más una serie mensual de demo (Miraflores).

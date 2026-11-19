# data/raw — Procedencia del BYOD nacional 2025

> Los archivos `.xls` de esta carpeta son exportaciones oficiales de la **Consulta Amigable de Ejecución del Gasto** del MEF (SIAF), año 2025.
> Esta carpeta está **gitignored**: los archivos no se commitean; este README y `byod_manifest.json` sí (son la evidencia de procedencia).

## Cómo se capturaron (18–19/11/2026)

1. Navegación drill-down en la app oficial con el navegador del usuario:
   `https://apps5.mineco.gob.pe/transparencia/Navegador/Navegar_7.aspx`
   Ruta: Nivel de Gobierno → `M: GOBIERNOS LOCALES` → `M: MUNICIPALIDADES` → Departamento.
2. El botón "Exportar" genera una URL GET sin estado con el estado de la consulta codificado en parámetros.
3. Descarga directa de esa URL (una petición por archivo; sin crawling; `apps5.mineco.gob.pe` no tiene WAF). Se descargaron 24 archivos departamentales nuevos el 19/11/2026; Lima se reutilizó del lote del 18/11/2026.

## Cobertura

- **25 departamentos** y **1,892 municipalidades** (universo municipal del Perú en la Consulta Amigable).
- 25 archivos `entity_annual` (uno por departamento), más el agregado departamental, el agregado por genérica y la serie mensual de Miraflores.
- Total: **28 archivos** en `byod_manifest.json`.
- Rango por departamento: Callao 7 municipalidades; Áncash 166.

| Código | Departamento | Archivo | Municipalidades |
|---:|---|---|---:|
| 01 | Amazonas | `consulta_amigable_amazonas_municipalidades_2025.xls` | 84 |
| 02 | Áncash | `consulta_amigable_ancash_municipalidades_2025.xls` | 166 |
| 03 | Apurímac | `consulta_amigable_apurimac_municipalidades_2025.xls` | 85 |
| 04 | Arequipa | `consulta_amigable_arequipa_municipalidades_2025.xls` | 109 |
| 05 | Ayacucho | `consulta_amigable_ayacucho_municipalidades_2025.xls` | 124 |
| 06 | Cajamarca | `consulta_amigable_cajamarca_municipalidades_2025.xls` | 127 |
| 07 | Callao | `consulta_amigable_callao_municipalidades_2025.xls` | 7 |
| 08 | Cusco | `consulta_amigable_cusco_municipalidades_2025.xls` | 116 |
| 09 | Huancavelica | `consulta_amigable_huancavelica_municipalidades_2025.xls` | 102 |
| 10 | Huánuco | `consulta_amigable_huanuco_municipalidades_2025.xls` | 84 |
| 11 | Ica | `consulta_amigable_ica_municipalidades_2025.xls` | 43 |
| 12 | Junín | `consulta_amigable_junin_municipalidades_2025.xls` | 124 |
| 13 | La Libertad | `consulta_amigable_la_libertad_municipalidades_2025.xls` | 84 |
| 14 | Lambayeque | `consulta_amigable_lambayeque_municipalidades_2025.xls` | 38 |
| 15 | Lima | `consulta_amigable_lima_municipalidades_2025.xls` | 171 |
| 16 | Loreto | `consulta_amigable_loreto_municipalidades_2025.xls` | 54 |
| 17 | Madre de Dios | `consulta_amigable_madre_de_dios_municipalidades_2025.xls` | 11 |
| 18 | Moquegua | `consulta_amigable_moquegua_municipalidades_2025.xls` | 21 |
| 19 | Pasco | `consulta_amigable_pasco_municipalidades_2025.xls` | 29 |
| 20 | Piura | `consulta_amigable_piura_municipalidades_2025.xls` | 65 |
| 21 | Puno | `consulta_amigable_puno_municipalidades_2025.xls` | 110 |
| 22 | San Martín | `consulta_amigable_san_martin_municipalidades_2025.xls` | 78 |
| 23 | Tacna | `consulta_amigable_tacna_municipalidades_2025.xls` | 28 |
| 24 | Tumbes | `consulta_amigable_tumbes_municipalidades_2025.xls` | 13 |
| 25 | Ucayali | `consulta_amigable_ucayali_municipalidades_2025.xls` | 19 |
| — | **Total** | **25 archivos** | **1,892** |

## Archivos de contexto

| Archivo | Parámetros de estado | Contenido |
|---|---|---|
| `consulta_amigable_departamentos_2025.xls` | `0=&1=M&37=M&5=&y=2025&cpage=1&psize=400` | Municipalidades del Perú por departamento |
| `consulta_amigable_municipalidades_generica_2025.xls` | `0=&1=M&37=M&24=&y=2025&cpage=1&psize=400` | Municipalidades del Perú por genérica de gasto |
| `consulta_amigable_miraflores_mes_2025.xls` | `0=&1=M&37=M&5=15&7=301271&23=&y=2025&cpage=1&psize=400` | Serie mensual de Miraflores (pliego 301271) |

Los archivos departamentales usan:
`?_tgt=xls&_uhc=yes&0=&1=M&37=M&5=<código>&7=&y=2025&cpage=1&psize=400`

Parámetros: `1` = Nivel de Gobierno (`M` = Gobiernos Locales), `37` = Gob.Loc./Mancom. (`M` = Municipalidades), `5` = Departamento, `7` = Municipalidad (pliego), `23` = Mes, `24` = Genérica, `y` = año, `psize` = tamaño de página.

## Formato

- Archivos `.xls` que en realidad son **tablas HTML** (exportación ASP.NET clásica).
- Fila de datos: `Concepto | PIA | PIM | Certificación | Compromiso Anual | Atención de Compromiso Mensual | Devengado | Girado | Avance %`.
- Entidades: `"150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES"` (UBIGEE-PLIEGO).
- La vista "Mes" exporta devengado **del mes** (no acumulado).
- Encabezado con `Fecha de la Consulta` y `Año de Ejecución: 2025`.
- El nombre del departamento no viaja en cada fila municipal; `byod_manifest.json` lo aporta como `context.department` / `context.department_code`.

## Hashes SHA-256

Los 28 hashes completos se registran en `artifacts/e2e/run_manifest.json` (`source_files_sha256`) cuando el pipeline procesa el lote. El manifest también cubre los 6 payloads con `checksums.sha256`.

## Atribución

Fuente: MEF — Consulta Amigable (SIAF). Datos públicos de ejecución presupuestal. PresupuestoAbiertoPE no está afiliado al MEF.

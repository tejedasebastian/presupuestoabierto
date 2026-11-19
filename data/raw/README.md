# data/raw — Procedencia del BYOD

> Los archivos `.xls` de esta carpeta son exportaciones oficiales de la **Consulta Amigable de Ejecución del Gasto** del MEF (SIAF), año 2025.
> Esta carpeta está **gitignored**: los archivos no se commitean; este README sí (es la evidencia de procedencia).

## Cómo se capturaron (18/11/2026)

1. Navegación drill-down en la app oficial con el navegador del usuario (browser MCP):
   `https://apps5.mineco.gob.pe/transparencia/Navegador/Navegar_7.aspx`
   — Ruta: Nivel de Gobierno → `M: GOBIERNOS LOCALES` → `M: MUNICIPALIDADES` → (Departamento `15: LIMA` donde aplica).
2. El botón "Exportar" de la app genera una URL GET sin estado con el estado de la consulta codificado en parámetros.
3. Descarga directa de esa URL (una petición por archivo; sin crawling; `apps5.mineco.gob.pe` no tiene WAF).

## Archivos y URLs de exportación

Todas las URLs usan la base:

```text
https://apps5.mineco.gob.pe/transparencia/Navegador/Navegar_7.aspx?_tgt=xls&_uhc=yes
```

| Archivo | Parámetros de estado | Contenido |
|---|---|---|
| `consulta_amigable_departamentos_2025.xls` | `0=&1=M&37=M&5=&y=2025&cpage=1&psize=400` | Municipalidades del Perú por departamento |
| `consulta_amigable_lima_municipalidades_2025.xls` | `0=&1=M&37=M&5=15&7=&y=2025&cpage=1&psize=400` | Municipalidades del departamento de Lima (código `UBIGEE-PLIEGO`) |
| `consulta_amigable_miraflores_mes_2025.xls` | `0=&1=M&37=M&5=15&7=301271&23=&y=2025&cpage=1&psize=400` | Serie mensual de la Municipalidad Distrital de Miraflores (pliego 301271) |
| `consulta_amigable_municipalidades_generica_2025.xls` | `0=&1=M&37=M&24=&y=2025&cpage=1&psize=400` | Municipalidades del Perú por genérica de gasto |

Parámetros de estado: `1` = Nivel de Gobierno (`M` = Gobiernos Locales), `37` = Gob.Loc./Mancom. (`M` = Municipalidades), `5` = Departamento (`15` = Lima, vacío = nacional), `7` = Municipalidad (pliego), `23` = Mes, `24` = Genérica, `y` = año, `psize` = tamaño de página.

## Formato

- Archivos `.xls` que en realidad son **tablas HTML** (exportación ASP.NET clásica).
- Fila de datos: `Concepto | PIA | PIM | Certificación | Compromiso Anual | Atención de Compromiso Mensual | Devengado | Girado | Avance %`.
- Entidades: `"150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES"` (UBIGEE-PLIEGO).
- La vista "Mes" exporta devengado **del mes** (no acumulado).
- Encabezado con `Fecha de la Consulta` y `Año de Ejecución: 2025`.

## Hashes SHA-256 (verificados 18/11/2026)

```text
4a4a3dd48f78c511...  consulta_amigable_departamentos_2025.xls          (43,393 bytes)
6e15caaf715d7bda...  consulta_amigable_lima_municipalidades_2025.xls  (266,727 bytes)
506cb9247c68151c...  consulta_amigable_miraflores_mes_2025.xls       (23,358 bytes)
c42339a9781b567e...  consulta_amigable_municipalidades_generica_2025.xls (21,003 bytes)
```

Los hashes completos se registran en `run_manifest.json` cuando el pipeline procesa cada archivo.

## Atribución

Fuente: MEF — Consulta Amigable (SIAF). Datos públicos de ejecución presupuestal. PresupuestoAbiertoPE no está afiliado al MEF.

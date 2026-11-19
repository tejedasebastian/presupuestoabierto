# ADR-002 — Spark local + Delta (Python 3.13 + Spark 4)

## Estado

Aceptado (18/11/2026).

## Contexto

El portafolio original sugiere Databricks Community o Spark local. Restricciones verificadas:

- Databricks Community requiere login manual del usuario, no es reproducible en CI y sus sesiones expiran.
- La máquina tiene Java 17 (requisito de Spark 4) y Python 3.13 como default.
- `pip install --dry-run pyspark delta-spark` en Python 3.13 resuelve `pyspark-4.2.0` + `delta_spark-4.4.1`.
- RAM libre ajustada (~1.3 GB): Spark local necesita driver memory contenido.
- Spark en Windows requiere `winutils.exe` (instalado una vez en `tools/winutils/`, gitignored).

## Decisión

- Motor: **PySpark 4.2 + delta-spark 4.4** instalables por pip, **Python 3.13**.
- La sesión Spark se crea en `presupuesto/shared/spark.py` (único punto), con:
  - `HADOOP_HOME`/`PATH` apuntando a `tools/winutils` si existe (solo Windows),
  - `JAVA_HOME` inferido de `java` en PATH si no está seteado,
  - driver memory configurable (`PRESUPUESTO_DRIVER_MEMORY`, default 768m),
  - Delta configurado vía `configure_spark_with_delta_pip`.
- Databricks queda como **notebook de equivalencia** (wrapper ≤ 20 líneas), no como dependencia.

## Consecuencias

### Positivas

- Reproducible en CI (ubuntu, 7 GB) y local (Windows, driver contenido).
- Sin cuentas externas ni logins manuales.
- Delta Lake real: transacciones ACID, `_delta_log` verificable en los E2E.

### Negativas

- Corridas locales limitadas por RAM (~1.3 GB libres): el modo volumen corre en CI, no local.
- Windows + Spark tiene rugosidad (winutils); CI ubuntu es la validación autoritativa.

## Addendum: fixes de Windows descubiertos al implementar (18/11/2026)

1. **Hostname con guión bajo:** la máquina se llama `PC_ST25.mshome.net`; el guión bajo rompe el validador de URLs RPC de Spark (`Invalid Spark URL`). Fix: `SPARK_LOCAL_HOSTNAME=127.0.0.1` + `spark.driver.host/bindAddress=127.0.0.1` (IP literal, evita también la ambigüedad IPv6/IPv4 de `localhost`).
2. **`hadoop.dll` faltante:** `winutils.exe` solo no basta; Delta da `UnsatisfiedLinkError: NativeIO$Windows.access0`. Fix: `hadoop.dll` junto a winutils en `tools/winutils/bin/`.
3. **Stub de Python de la Microsoft Store:** el JVM lanza workers con `python` a secas, que en esta máquina es el stub de la Store ("Python was not found"). Fix: `PYSPARK_PYTHON=sys.executable`.
4. **Ivy (Maven) se cuelga en esta red:** `configure_spark_with_delta_pip` usa `spark.jars.packages` y la resolución de Ivy nunca termina. Fix: jars de Delta vendored en `tools/jars/` montados con `spark.jars` local (`tools/fetch_jars.ps1` los descarga una vez). CI (runner fresco, sin `tools/jars/`) cae al path de Maven, que en GitHub funciona.
5. **Ruido de shutdown:** el hook del JVM imprime mensajes de `taskkill` en el stdout de la consola; los tests no deben asumir que el JSON es la última línea.

"""Single place where the Spark session is created.

Windows notes (ADR-002): sets HADOOP_HOME to the repo-local winutils if
present, and infers JAVA_HOME from the java binary on PATH when unset.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WINUTILS_DIR = _REPO_ROOT / "tools" / "winutils"
_LOCAL_JARS_DIR = _REPO_ROOT / "tools" / "jars"

# Maven coordinates used only when no local jars are present (CI runners).
_DELTA_MAVEN_PACKAGES = "io.delta:delta-spark_4.2_2.13:4.4.1"


def _ensure_java_home() -> None:
    if os.environ.get("JAVA_HOME"):
        return
    # java on PATH may be a shim (e.g. Oracle javapath); ask the JVM itself
    # where it lives. If we cannot resolve it, leave JAVA_HOME unset: pyspark
    # falls back to the PATH binary, which works.
    try:
        import subprocess

        output = subprocess.run(
            ["java", "-XshowSettings:properties", "-version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in (output.stderr or "").splitlines():
            if "java.home" in line:
                java_home = line.split("=", 1)[1].strip()
                if (Path(java_home) / "bin" / "java.exe").exists():
                    os.environ["JAVA_HOME"] = java_home
                return
    except (OSError, subprocess.TimeoutExpired):
        return


def _ensure_local_hostname() -> None:
    # Windows machine names may contain underscores (e.g. PC_ST25.mshome.net),
    # which Spark's RPC URL validator rejects; "localhost" may resolve to ::1
    # while the driver binds IPv4. A literal loopback IP avoids both problems.
    os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "127.0.0.1")


def _ensure_pyspark_python() -> None:
    # The JVM spawns Python workers with the bare "python" command, which on
    # Windows may be the Microsoft Store stub. Pin the current interpreter.
    import sys

    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


def _ensure_winutils() -> None:
    winutils_bin = _WINUTILS_DIR / "bin"
    if winutils_bin.exists():
        os.environ.setdefault("HADOOP_HOME", str(_WINUTILS_DIR))
        os.environ["PATH"] = str(winutils_bin) + os.pathsep + os.environ.get("PATH", "")


@lru_cache
def get_spark(app_name: str = "presupuesto", driver_memory: str = "768m"):
    """Create (once) and return the local Spark session with Delta Lake."""
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    _ensure_java_home()
    _ensure_winutils()
    _ensure_local_hostname()
    _ensure_pyspark_python()

    builder = (
        SparkSession.builder.appName(app_name)
        .master("local[1]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.driver.memory", driver_memory)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
    )

    # Prefer vendored local jars: Ivy's Maven resolution hangs on some
    # networks. CI (fresh runner, no tools/jars) falls back to packages.
    local_jars = sorted(_LOCAL_JARS_DIR.glob("*.jar")) if _LOCAL_JARS_DIR.exists() else []
    if local_jars:
        builder = builder.config("spark.jars", ",".join(str(jar) for jar in local_jars))
    else:
        from delta import configure_spark_with_delta_pip

        builder = configure_spark_with_delta_pip(builder)

    return builder.getOrCreate()


def delta_package_version() -> str:
    from importlib.metadata import version

    return version("delta-spark")


def spark_version(spark) -> str:
    return spark.version

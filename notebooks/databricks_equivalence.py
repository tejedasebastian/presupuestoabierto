"""Databricks equivalence wrapper.

The medallion logic lives in the `presupuesto` package, not here.
Databricks Runtime 17+ (Spark 4 / Delta 4) is functionally equivalent to the
local stack. Upload the BYOD exports to a Unity Catalog Volume, point
`PRESUPUESTO_RAW_DIR` and `PRESUPUESTO_MEDALLION_DIR` at that Volume, then run
the same entrypoint. This file intentionally contains no pipeline logic.
"""

from presupuesto.config import get_settings
from presupuesto.pipeline import run_byod

summary = run_byod(get_settings())
print(summary)

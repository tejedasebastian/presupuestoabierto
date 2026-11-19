"""Deterministic synthetic seed for the Consulta Amigable export format.

Generates HTML files byte-compatible with the real SIAF exports so the
BYOD parser is the only ingestion path (verified in CI without network).

Modes:
- clean: 25 departments, 50 entities (annual), 2 monthly entities, 6 categories.
- dirty: clean + exactly one violation per validation (12 total).
- volume: canonical rows generated directly (no HTML): the medallion stress
  test. The real source cannot export the entity x category x month cross in
  bulk, so volume uses the synthetic cross and is clearly labeled as such.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

YEAR = 2025
QUERY_DATE = "18-noviembre-2026"
SEED_QUERY_DATE = "01-noviembre-2026"  # fixed for determinism

# Real genérica names from the official export (data/raw/README.md).
CATEGORIES = [
    ("5-21", "PERSONAL Y OBLIGACIONES SOCIALES"),
    ("5-22", "PENSIONES Y OTRAS PRESTACIONES SOCIALES"),
    ("5-23", "BIENES Y SERVICIOS"),
    ("5-24", "DONACIONES Y TRANSFERENCIAS"),
    ("6-26", "ADQUISICION DE ACTIVOS NO FINANCIEROS"),
    ("7-28", "SERVICIO DE LA DEUDA PUBLICA"),
]

DEPARTMENTS = [
    "AMAZONAS",
    "ANCASH",
    "APURIMAC",
    "AREQUIPA",
    "AYACUCHO",
    "CAJAMARCA",
    "PROVINCIA CONSTITUCIONAL DEL CALLAO",
    "CUSCO",
    "HUANCAVELICA",
    "HUANUCO",
    "ICA",
    "JUNIN",
    "LA LIBERTAD",
    "LAMBAYEQUE",
    "LIMA",
    "LORETO",
    "MADRE DE DIOS",
    "MOQUEGUA",
    "PASCO",
    "PIURA",
    "PUNO",
    "SAN MARTIN",
    "TACNA",
    "TUMBES",
    "UCAYALI",
]

MONTHS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


@dataclass(slots=True)
class FileSpec:
    """One export file to ingest: path, grain and optional entity context."""

    path: Path
    grain: str
    context: dict = field(default_factory=dict)


def _fmt(amount: int | float | None) -> str:
    if amount is None:
        return " "
    return f"{int(round(amount)):,}"


def _render_export(
    dimension_label: str,
    rows_html: list[str],
    include_devengado: bool = True,
    year: int = YEAR,
    query_date: str = SEED_QUERY_DATE,
) -> str:
    """Render one HTML export in the SIAF structure (hd + MapTable + Data)."""
    devengado_cells = (
        (
            '<td title="Atencion de Compromiso Mensual">Atención de Compromiso Mensual</td>'
            '<td title="DEVENGADO">Devengado</td>'
            '<td title="GIRADO">Girado</td>'
            '<td title="Avance %">Avance %</td>'
        )
        if include_devengado
        else ""
    )
    return f"""<html><head><style>body {{ font-family: Arial; }}</style></head><body>
<table id="hd"><tr><td colspan="9">
<div class='title'>Consulta Amigable</div>
<div class='subtitle'>Consulta de Ejecución del Gasto</div><br />
<div class='fecha'>Fecha de la Consulta: {query_date}</div><br />
<b>Año de Ejecución: <span class='value'>{year}</span><br />
Incluye: <span class='value'>Actividades y Proyectos</span></b>
</td></tr></table>
<table class="MapTable"><tr>
<td title="Concepto" rowspan="2">{dimension_label}</td>
<td title="Presupuesto Institucional de Apertura" rowspan="2">PIA</td>
<td title="Presupuesto Institucional Modificado" rowspan="2">PIM</td>
<td title="Certificacion" rowspan="2">Certificación</td>
<td title="Compromiso Anual" rowspan="2">Compromiso Anual</td>
{devengado_cells}
</tr></table>
<table class="Data">
{"".join(rows_html)}
</table>
</body></html>
"""


def _data_row(concept: str, cells: list[str]) -> str:
    tds = "".join(f"<td> {cell} </td>" for cell in cells)
    return f"<tr><td align='left'> {concept} </td>{tds}</tr>\n"


def _entity_amounts(index: int) -> dict:
    """Deterministic, varied amounts per entity index."""
    base = 1_000_000 + index * 123_457
    pia = base
    pim = int(base * 1.08)
    # Execution profile between ~57% and ~95%, varying by index.
    pct = 0.57 + (index % 7) * 0.065
    accrued = int(pim * pct)
    return {
        "pia": pia,
        "pim": pim,
        "certification": int(accrued * 1.04),
        "annual_commitment": int(accrued * 1.02),
        "monthly_commitment": accrued,
        "accrued": accrued,
        "paid": int(accrued * 0.995),
        "execution_pct": round(accrued / pim * 100, 1),
    }


def _entity_concept(index: int, name_suffix: str = "DEMO") -> tuple[str, str, str]:
    ubigee = f"1501{(index % 90) + 1:02d}"
    code = f"301{(index + 1):03d}"
    name = f"MUNICIPALIDAD DISTRITAL DE {name_suffix} {index + 1:02d}"
    return ubigee, code, name


def _annual_rows(entities: int, dirty: bool) -> list[str]:
    rows: list[str] = []
    for index in range(entities):
        ubigee, code, name = _entity_concept(index)
        amounts = _entity_amounts(index)
        concept = f"{ubigee}-{code}: {name}"
        cells = [
            _fmt(amounts["pia"]),
            _fmt(amounts["pim"]),
            _fmt(amounts["certification"]),
            _fmt(amounts["annual_commitment"]),
            _fmt(amounts["monthly_commitment"]),
            _fmt(amounts["accrued"]),
            _fmt(amounts["paid"]),
            f"{amounts['execution_pct']}",
        ]
        rows.append(_data_row(concept, cells))

    if dirty:
        # One violation per validation, rows only (files handled separately):
        # V6 duplicate row: exact copy of entity 0.
        ubigee, code, name = _entity_concept(0)
        amounts = _entity_amounts(0)
        rows.append(
            _data_row(
                f"{ubigee}-{code}: {name}",
                [
                    _fmt(amounts["pia"]),
                    _fmt(amounts["pim"]),
                    _fmt(amounts["certification"]),
                    _fmt(amounts["annual_commitment"]),
                    _fmt(amounts["monthly_commitment"]),
                    _fmt(amounts["accrued"]),
                    _fmt(amounts["paid"]),
                    f"{amounts['execution_pct']}",
                ],
            )
        )
        # V3 unparseable PIM (pliego outside the clean seed range 301001-301050).
        rows.append(
            _data_row(
                "150150-301051: MUNICIPALIDAD DISTRITAL DE PARSE BAD",
                [_fmt(100), "12,3x4", _fmt(90), _fmt(80), _fmt(70), _fmt(60), _fmt(50), "60.0"],
            )
        )
        # V5 null entity code (missing pliego).
        rows.append(
            _data_row(
                "150151-: MUNICIPALIDAD SIN PLIEGO",
                [_fmt(100), _fmt(110), _fmt(90), _fmt(80), _fmt(70), _fmt(60), _fmt(50), "55.0"],
            )
        )
        # V8 placeholder entity name.
        rows.append(
            _data_row(
                "150152-301052: SIN DATO",
                [_fmt(100), _fmt(110), _fmt(90), _fmt(80), _fmt(70), _fmt(60), _fmt(50), "55.0"],
            )
        )
        # V9 devengado above PIM.
        rows.append(
            _data_row(
                "150153-301053: MUNICIPALIDAD DISTRITAL DE OVER EXEC",
                [
                    _fmt(100),
                    _fmt(200),
                    _fmt(190),
                    _fmt(180),
                    _fmt(170),
                    _fmt(300),
                    _fmt(290),
                    "150.0",
                ],
            )
        )
        # V10 negative PIM.
        rows.append(
            _data_row(
                "150154-301054: MUNICIPALIDAD DISTRITAL DE NEGATIVE",
                [_fmt(100), "-5,000", _fmt(90), _fmt(80), _fmt(70), _fmt(60), _fmt(50), "55.0"],
            )
        )
        # Structurally dead row: null accrued (silver quarantine case).
        rows.append(
            _data_row(
                "150155-301055: MUNICIPALIDAD SIN DEVENGADO",
                [_fmt(100), _fmt(110), _fmt(90), _fmt(80), _fmt(70), " ", _fmt(50), "55.0"],
            )
        )
    return rows


def _monthly_rows(entity_index: int, dirty: bool, drop_months: int = 0) -> list[str]:
    """12 monthly rows whose accrued sums to the entity's annual accrued."""
    amounts = _entity_amounts(entity_index)
    annual_accrued = amounts["accrued"]
    months = list(range(1, 13))
    if drop_months:
        months = months[: 12 - drop_months]
    per_month = annual_accrued // len(months)
    rows: list[str] = []
    remaining = annual_accrued
    for position, month in enumerate(months):
        accrued = per_month if position < len(months) - 1 else remaining
        remaining -= accrued
        rows.append(
            _data_row(
                f"{month}: '{MONTHS[month - 1]}",
                [
                    " ",
                    " ",
                    _fmt(accrued * 2),
                    _fmt(int(accrued * 1.2)),
                    _fmt(int(accrued * 1.1)),
                    _fmt(accrued),
                    _fmt(int(accrued * 0.98)),
                    " ",
                ],
            )
        )
    if dirty and entity_index == 0:
        # V11 break the monthly-sums-to-annual invariant: replace December
        # (index 11 for a full 12-month entity) with an inconsistent amount.
        rows[11] = _data_row(
            "12: 'Diciembre",
            [" ", " ", _fmt(2000), _fmt(1600), _fmt(1400), _fmt(999), _fmt(900), " "],
        )
        # V4 month 13 (out of range), appended after so V11 cannot destroy it.
        rows.append(
            _data_row(
                "13: 'Tridecimbre",
                [" ", " ", _fmt(1000), _fmt(800), _fmt(700), _fmt(500), _fmt(400), " "],
            )
        )
    return rows


def generate_seed_files(base_dir: Path, mode: str, entities: int = 50) -> list[FileSpec]:
    """Write the seed export files and return their ingestion specs."""
    dirty = mode == "dirty"
    if mode not in {"clean", "dirty"}:
        raise ValueError(f"unsupported seed file mode: {mode}")
    out_dir = base_dir / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    specs: list[FileSpec] = []

    # Departments (national context).
    dept_rows = [
        _data_row(
            f"{i + 1:02d}: {name}",
            [
                _fmt(10_000_000 + i * 500_000),
                _fmt(12_000_000 + i * 500_000),
                _fmt(11_000_000 + i * 400_000),
                _fmt(10_500_000 + i * 400_000),
                _fmt(10_200_000 + i * 400_000),
                _fmt(10_000_000 + i * 390_000),
                _fmt(9_900_000 + i * 385_000),
                f"{83.0 + (i % 5)}",
            ],
        )
        for i, name in enumerate(DEPARTMENTS)
    ]
    dept_path = out_dir / f"seed_departamentos_{YEAR}.xls"
    dept_path.write_text(_render_export("Departamento", dept_rows), encoding="utf-8")
    specs.append(FileSpec(path=dept_path, grain="department"))

    # Entities, annual (the analytical core).
    munis_path = out_dir / f"seed_lima_municipalidades_{YEAR}.xls"
    munis_path.write_text(
        _render_export("Municipalidad", _annual_rows(entities, dirty)), encoding="utf-8"
    )
    specs.append(FileSpec(path=munis_path, grain="entity_annual"))

    # Monthly entities 1 and 2 (index 0 and 1), like the real Miraflores export.
    for entity_index, _context_code in ((0, "301001"), (1, "301002")):
        ubigee, code, name = _entity_concept(entity_index)
        # V12 coverage gap: 10 months passes the file-level minimum (10 rows)
        # but fails the coverage validation (12 required months).
        drop = 2 if dirty and entity_index == 1 else 0
        monthly_path = out_dir / f"seed_municipio_{code}_mes_{YEAR}.xls"
        monthly_path.write_text(
            _render_export("Mes", _monthly_rows(entity_index, dirty, drop_months=drop)),
            encoding="utf-8",
        )
        specs.append(
            FileSpec(
                path=monthly_path,
                grain="entity_monthly",
                context={
                    "entity_code": code,
                    "entity_ubigee": ubigee,
                    "entity_name": name,
                },
            )
        )

    # National categories.
    cat_rows = [
        _data_row(
            f"{cat_code}: {cat_name}",
            [
                _fmt(1_000_000_000 + i * 250_000_000),
                _fmt(1_100_000_000 + i * 250_000_000),
                _fmt(1_050_000_000 + i * 200_000_000),
                _fmt(1_020_000_000 + i * 200_000_000),
                _fmt(1_000_000_000 + i * 190_000_000),
                _fmt(980_000_000 + i * 185_000_000),
                _fmt(960_000_000 + i * 180_000_000),
                f"{89.0 + i}",
            ],
        )
        for i, (cat_code, cat_name) in enumerate(CATEGORIES)
    ]
    cat_path = out_dir / f"seed_municipalidades_generica_{YEAR}.xls"
    cat_path.write_text(_render_export("Genérica", cat_rows), encoding="utf-8")
    specs.append(FileSpec(path=cat_path, grain="category_national"))

    if dirty:
        # V1: export missing the DEVENGADO column (schema violation).
        bad_schema_rows = [
            _data_row("150160-301060: MUNICIPALIDAD DISTRITAL DE SCHEMA", [_fmt(100), _fmt(110)])
        ]
        schema_path = out_dir / f"seed_dirty_schema_{YEAR}.xls"
        schema_path.write_text(
            _render_export("Municipalidad", bad_schema_rows, include_devengado=False),
            encoding="utf-8",
        )
        specs.append(FileSpec(path=schema_path, grain="entity_annual"))

        # V2: export below the minimum row count for entity grains.
        tiny_rows = [
            _data_row(
                "150161-301061: MUNICIPALIDAD DISTRITAL DE TINY",
                [_fmt(100), _fmt(110), _fmt(90), _fmt(80), _fmt(70), _fmt(60), _fmt(50), "55.0"],
            )
        ]
        tiny_path = out_dir / f"seed_dirty_rowcount_{YEAR}.xls"
        tiny_path.write_text(_render_export("Municipalidad", tiny_rows), encoding="utf-8")
        specs.append(FileSpec(path=tiny_path, grain="entity_annual"))

        # V7: monthly export for an unknown pliego (referential violation).
        ref_rows = _monthly_rows(2, dirty=False)
        ref_path = out_dir / f"seed_municipio_301999_mes_{YEAR}.xls"
        ref_path.write_text(_render_export("Mes", ref_rows), encoding="utf-8")
        specs.append(
            FileSpec(
                path=ref_path,
                grain="entity_monthly",
                context={
                    "entity_code": "301999",
                    "entity_ubigee": "150199",
                    "entity_name": "MUNICIPALIDAD DISTRITAL DE UNKNOWN",
                },
            )
        )

    return specs


def generate_volume_rows(entities: int, categories: int = 6) -> list[dict]:
    """Canonical rows for the volume stress test (direct, no HTML).

    The real Consulta Amigable cannot export the entity x category x month
    cross in bulk, so this cross is synthetic by definition; it exists to
    measure the medallion layers at scale.
    """
    rows: list[dict] = []
    for entity_index in range(entities):
        ubigee, code, name = _entity_concept(entity_index)
        amounts = _entity_amounts(entity_index)
        entity_rows: list[dict] = []
        annual_accrued = 0
        base_share = amounts["pim"] // categories
        remainder = amounts["pim"] - base_share * categories
        for cat_index, (cat_code, cat_name) in enumerate(CATEGORIES[:categories]):
            # Keep the synthetic annual accrued within PIM: validation #9
            # (devengado <= PIM) must hold for the volume dataset too.
            share = base_share + (remainder if cat_index == categories - 1 else 0)
            monthly = share // 12
            annual_accrued += monthly * 12
            for month in range(1, 13):
                entity_rows.append(
                    {
                        "grain": "entity_monthly",
                        "entity_ubigee": ubigee,
                        "entity_code": code,
                        "entity_name": name,
                        "year": YEAR,
                        "month": month,
                        "category": cat_name,
                        "category_code": cat_code,
                        "department": None,
                        "department_code": None,
                        "pia": None,
                        "pim": None,
                        "certification": None,
                        "annual_commitment": None,
                        "monthly_commitment": None,
                        "accrued": float(monthly),
                        "paid": float(monthly * 0.98),
                        "execution_pct": None,
                        "query_date": SEED_QUERY_DATE,
                        "source_file": f"volume_{entity_index}",
                        "concept_raw": f"{month}: '{MONTHS[month - 1]}",
                    }
                )
        # Annual row consistent with the monthly sum (validation 11 passes).
        entity_rows.append(
            {
                "grain": "entity_annual",
                "entity_ubigee": ubigee,
                "entity_code": code,
                "entity_name": name,
                "year": YEAR,
                "month": None,
                "category": None,
                "category_code": None,
                "department": None,
                "department_code": None,
                "pia": float(amounts["pia"]),
                "pim": float(amounts["pim"]),
                "certification": None,
                "annual_commitment": None,
                "monthly_commitment": None,
                "accrued": float(annual_accrued),
                "paid": None,
                "execution_pct": None,
                "query_date": SEED_QUERY_DATE,
                "source_file": f"volume_{entity_index}",
                "concept_raw": f"{ubigee}-{code}: {name}",
            }
        )
        rows.extend(entity_rows)
    return rows

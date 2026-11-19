"""BYOD parser for Consulta Amigable HTML exports.

The MEF exports are HTML tables saved with an .xls extension (classic
ASP.NET). Structure (verified against real files, see data/raw/README.md):

- ``<table id="hd">``: title, "Fecha de la Consulta", "Año de Ejecución".
- ``<table class="MapTable">``: column headers with tooltips (PIA, PIM,
  Certificación, Compromiso Anual, Atención de Compromiso Mensual,
  Devengado, Girado, Avance %).
- ``<table class="Data">``: data rows, 9 cells:
  concept | PIA | PIM | Cert | CompromisoAnual | ACM | Devengado | Girado | Avance%.

Concept patterns:
- ``150122-301271: MUNICIPALIDAD DISTRITAL DE MIRAFLORES`` -> entity annual
- ``1: 'Enero``                                          -> monthly row
- ``5-21: PERSONAL Y OBLIGACIONES SOCIALES``             -> category
- ``01: AMAZONAS``                                       -> department
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from presupuesto.domain.errors import ValidationError

REQUIRED_COLUMNS = ("PIA", "PIM", "DEVENGADO", "GIRADO")

_ENTITY_RE = re.compile(r"^\s*(\d{6})-(\d{0,6}):\s*(.*?)\s*$")
_MONTH_RE = re.compile(r"^\s*(\d{1,2}):\s*'?(\w+)\s*$")
_CATEGORY_RE = re.compile(r"^\s*(\d+-\d+):\s*(.*?)\s*$")
_DEPARTMENT_RE = re.compile(r"^\s*(\d{2}):\s*(.*?)\s*$")
_YEAR_RE = re.compile(
    # Tolerant match: real exports carry mangled accents ("Ejecuci?n") and
    # fixtures use HTML entities ("Ejecuci&oacute;n").
    r"Ejecuci.{0,120}?(\d{4})",
    re.IGNORECASE | re.DOTALL,
)
_QUERY_DATE_RE = re.compile(r"Fecha de la Consulta:\s*([^<]+)")
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass(slots=True)
class ExportContext:
    """Metadata the export cannot carry (e.g. the entity of a monthly file)."""

    grain: str
    entity_code: str | None = None
    entity_ubigee: str | None = None
    entity_name: str | None = None


def _read_html(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Real exports ship latin-1-ish bytes with mangled accents; the
        # numeric data is ASCII-safe either way.
        return raw.decode("latin-1", errors="replace")


def _parse_amount(text: str) -> float | None:
    cleaned = (text or "").replace(",", "").replace("\xa0", "").strip()
    if not cleaned or cleaned in {"-", "&nbsp;"}:
        return None
    if not _NUMBER_RE.match(cleaned):
        return None
    return float(cleaned)


def _cell_texts(row) -> list[str]:
    return [cell.get_text(strip=True) for cell in row.find_all("td")]


def _extract_year(html: str, file_name: str) -> int:
    match = _YEAR_RE.search(html)
    if not match:
        raise ValidationError(
            "Export does not declare its execution year.",
            {"file": file_name, "required": "Año de Ejecución"},
        )
    return int(match.group(1))


def _extract_query_date(html: str) -> str | None:
    match = _QUERY_DATE_RE.search(html)
    return match.group(1).strip() if match else None


def _require_columns(soup: BeautifulSoup, file_name: str) -> None:
    header = soup.find("table", class_="MapTable")
    if header is None:
        raise ValidationError(
            "Export is missing the header table (MapTable).",
            {"file": file_name},
        )
    labels = {cell.get_text(strip=True).upper() for cell in header.find_all("td")}
    labels |= {(cell.get("title") or "").upper() for cell in header.find_all("td")}
    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in labels and column not in " ".join(labels)
    ]
    if missing:
        raise ValidationError(
            "Export is missing required columns.",
            {"file": file_name, "missing": missing},
        )


def _classify_concept(concept: str) -> dict:
    """Split a concept cell into its canonical parts by pattern."""
    entity = _ENTITY_RE.match(concept)
    if entity:
        return {
            "entity_ubigee": entity.group(1) or None,
            "entity_code": entity.group(2) or None,
            "entity_name": entity.group(3) or None,
        }
    category = _CATEGORY_RE.match(concept)
    if category:
        return {"category_code": category.group(1), "category": category.group(2)}
    month = _MONTH_RE.match(concept)
    if month and not month.group(2).replace(" ", "").isdigit():
        return {"month": int(month.group(1))}
    department = _DEPARTMENT_RE.match(concept)
    if department:
        return {"department_code": department.group(1), "department": department.group(2)}
    return {}


def parse_export(
    path: Path,
    grain: str,
    entity_context: dict | None = None,
) -> list[dict]:
    """Parse one Consulta Amigable export into canonical bronze rows."""
    file_name = path.name
    html = _read_html(path)
    soup = BeautifulSoup(html, "html.parser")

    year = _extract_year(html, file_name)
    query_date = _extract_query_date(html)
    _require_columns(soup, file_name)

    data_table = soup.find("table", class_="Data")
    if data_table is None:
        raise ValidationError(
            "Export is missing the data table.",
            {"file": file_name},
        )

    rows: list[dict] = []
    for tr in data_table.find_all("tr"):
        cells = _cell_texts(tr)
        if len(cells) < 2:
            continue
        concept = cells[0]
        if not concept or concept.strip().upper() == "TOTAL":
            continue
        classified = _classify_concept(concept)

        row = {
            "grain": grain,
            "entity_ubigee": None,
            "entity_code": None,
            "entity_name": None,
            "year": year,
            "month": None,
            "category": None,
            "category_code": None,
            "department": None,
            "department_code": None,
            "pia": None,
            "pim": None,
            "certification": None,
            "annual_commitment": None,
            "monthly_commitment": None,
            "accrued": None,
            "paid": None,
            "execution_pct": None,
            "query_date": query_date,
            "source_file": file_name,
            "concept_raw": concept,
        }

        if grain == "entity_monthly":
            if "month" not in classified:
                continue
            row["month"] = classified["month"]
            if not entity_context:
                raise ValidationError(
                    "Monthly export requires entity context (the file does not "
                    "declare which municipality it belongs to).",
                    {"file": file_name, "grain": grain},
                )
            row["entity_code"] = entity_context.get("entity_code")
            row["entity_ubigee"] = entity_context.get("entity_ubigee")
            row["entity_name"] = entity_context.get("entity_name")
        else:
            if (
                "entity_code" in classified
                or "category_code" in classified
                or "department_code" in classified
            ):
                row.update(classified)
            else:
                # Unrecognized concept: keep the row for the quality layer
                # to judge; never silently drop data.
                row["entity_name"] = concept

        if len(cells) >= 9:
            row["pia"] = _parse_amount(cells[1])
            row["pim"] = _parse_amount(cells[2])
            row["certification"] = _parse_amount(cells[3])
            row["annual_commitment"] = _parse_amount(cells[4])
            row["monthly_commitment"] = _parse_amount(cells[5])
            row["accrued"] = _parse_amount(cells[6])
            row["paid"] = _parse_amount(cells[7])
            row["execution_pct"] = _parse_amount(cells[8])
        elif len(cells) >= 7:
            # Tolerate exports without the Avance % column.
            row["pia"] = _parse_amount(cells[1])
            row["pim"] = _parse_amount(cells[2])
            row["certification"] = _parse_amount(cells[3])
            row["annual_commitment"] = _parse_amount(cells[4])
            row["monthly_commitment"] = _parse_amount(cells[5])
            row["accrued"] = _parse_amount(cells[6])

        rows.append(row)

    if not rows:
        raise ValidationError(
            "Export contains no data rows.",
            {"file": file_name, "grain": grain},
        )
    return rows

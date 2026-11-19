/**
 * Builds the PBIR pages and visuals for PresupuestoAbiertoPE.
 *
 * The report is a local PBIP: the semantic model is TMDL, the report is PBIR.
 * This script only writes report-side JSON; it never touches the model or the
 * pipeline artifacts. Run `node dashboard/build_report.mjs` after changing the
 * design contract, then validate with `powerbi-report-author validate`.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve("dashboard/PresupuestoAbiertoPE.Report/definition");
const P1 = "31269c4d5e4e4b0090c9";
const P2 = "c5d6e7f8091a2b3c4d5e";

const SCHEMA_VISUAL =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json";
const SCHEMA_PAGE =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json";
const SCHEMA_PAGES =
  "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json";

const C = {
  canvas: "#F3F2F1",
  white: "#FFFFFF",
  navy: "#0F172A",
  teal: "#0F766E",
  tealDark: "#0F5F59",
  amber: "#B45309",
  amberDark: "#92400E",
  gray: "#94A3B8",
  inkSecondary: "#475569",
  border: "#E2E8F0",
  rowAlt: "#F8FAFC",
  headerBg: "#F1F5F9",
};

const lit = (value) => ({ expr: { Literal: { Value: value } } });
const raw = (value) => ({ Literal: { Value: value } });
const str = (value) => lit(`'${String(value).replaceAll("'", "''")}'`);
const num = (value) => lit(`${value}D`);
const int = (value) => lit(`${value}L`);
const bool = (value) => lit(value ? "true" : "false");
const solid = (hex) => ({ solid: { color: str(hex) } });

const column = (entity, property) => ({
  Column: { Expression: { SourceRef: { Entity: entity } }, Property: property },
});
const measure = (entity, property) => ({
  Measure: { Expression: { SourceRef: { Entity: entity } }, Property: property },
});
const projection = (field, queryRef, nativeQueryRef) => ({ field, queryRef, nativeQueryRef });

const background = (show, hex = C.white) => [
  { properties: { show: bool(show), color: solid(hex), transparency: num(0) } },
];
const border = (show, hex = C.border) => [
  { properties: { show: bool(show), color: solid(hex), radius: num(8), width: num(1) } },
];
const padding = (top, bottom, left, right) => [
  { properties: { top: num(top), bottom: num(bottom), left: num(left), right: num(right) } },
];
const visualHeader = (show = false) => [{ properties: { show: bool(show) } }];
const titleVco = (text, size = 13) => [
  {
    properties: {
      show: bool(true),
      text: str(text),
      fontSize: num(size),
      fontColor: solid(C.navy),
      bold: bool(true),
      alignment: str("left"),
    },
  },
];
const subtitleVco = () => [{ properties: { show: bool(false) } }];
const altText = (text) => [{ properties: { altText: str(text) } }];

function paragraph(text, sizePx, hex, options = {}) {
  return {
    textRuns: [
      {
        value: text,
        textStyle: {
          fontFamily: options.family ?? "Segoe UI",
          fontSize: `${sizePx}px`,
          color: hex,
          ...(options.bold ? { fontWeight: "bold" } : {}),
        },
      },
    ],
    horizontalTextAlignment: options.align ?? "left",
  };
}

function writeVisual(pageId, visual) {
  const directory = path.join(ROOT, "pages", pageId, "visuals", visual.name);
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(
    path.join(directory, "visual.json"),
    `${JSON.stringify(visual, null, 2)}\n`,
    "utf8",
  );
}

function textbox({ name, x, y, width, height, paragraphs, tabOrder = 1000 }) {
  return {
    $schema: SCHEMA_VISUAL,
    name,
    position: { x, y, z: 1000, height, width, tabOrder },
    visual: {
      visualType: "textbox",
      objects: { general: [{ properties: { paragraphs } }] },
      visualContainerObjects: {
        background: background(false),
        border: border(false),
        padding: padding(0, 0, 0, 0),
      },
    },
  };
}

function navButton({
  name,
  x,
  y,
  width,
  height,
  label,
  targetPageId,
  tooltip,
  icon,
  iconPlacement,
  alt,
}) {
  const textProperties = {
    text: str(label),
    fontSize: num(11),
    fontColor: solid(C.white),
    bold: bool(true),
    horizontalAlignment: str("center"),
  };
  if (iconPlacement === "right") {
    textProperties.leftMargin = int(12);
    textProperties.rightMargin = int(28);
  } else {
    textProperties.leftMargin = int(28);
    textProperties.rightMargin = int(12);
  }

  return {
    $schema: SCHEMA_VISUAL,
    name,
    position: { x, y, z: 1000, height, width, tabOrder: 1000 },
    visual: {
      visualType: "actionButton",
      objects: {
        text: [
          { properties: { show: bool(true) } },
          { properties: textProperties, selector: { id: "default" } },
        ],
        icon: [
          { properties: { show: bool(true) } },
          {
            properties: {
              shapeType: str(icon),
              placement: str(iconPlacement),
              lineColor: solid(C.white),
              lineWeight: int(2),
              iconSize: num(14),
            },
            selector: { id: "default" },
          },
        ],
        fill: [
          { properties: { show: bool(true) } },
          { properties: { fillColor: solid(C.teal) }, selector: { id: "default" } },
          { properties: { fillColor: solid(C.tealDark) }, selector: { id: "hover" } },
        ],
        outline: [{ properties: { show: bool(false) } }],
        shape: [
          {
            properties: { tileShape: str("rectangleRounded"), roundEdge: int(8) },
          },
          {
            properties: { tileShape: str("rectangleRounded") },
            selector: { id: "default" },
          },
        ],
      },
      visualContainerObjects: {
        background: background(false),
        border: border(false),
        padding: padding(0, 0, 0, 0),
        visualHeader: visualHeader(false),
        visualLink: [
          {
            properties: {
              show: bool(true),
              type: str("PageNavigation"),
              navigationSection: str(targetPageId),
              tooltip: str(tooltip),
            },
          },
        ],
        general: altText(alt),
      },
    },
    howCreated: "InsertVisualButton",
  };
}

function cardVisual({ name, x, y, width, height, entity, measureName, label, valueHex, accentHex, alt, displayUnits = null }) {
  const valueProperties = {
    fontSize: num(28),
    fontColor: solid(valueHex),
    bold: bool(true),
  };
  if (displayUnits) {
    valueProperties.labelDisplayUnits = str(displayUnits);
    valueProperties.labelPrecision = int(0);
  }
  return {
    $schema: SCHEMA_VISUAL,
    name,
    position: { x, y, z: 1000, height, width, tabOrder: 1000 },
    visual: {
      visualType: "cardVisual",
      query: {
        queryState: {
          Data: {
            projections: [
              projection(measure(entity, measureName), `${entity}.${measureName}`, measureName),
            ],
          },
        },
      },
      objects: {
        value: [
          {
            properties: valueProperties,
            selector: { id: "default" },
          },
        ],
        label: [
          {
            properties: {
              show: bool(true),
              text: str(label),
              fontSize: num(14),
              fontColor: solid(C.inkSecondary),
            },
            selector: { id: "default" },
          },
        ],
        padding: [{ properties: { paddingUniform: num(8) }, selector: { id: "default" } }],
        layout: [{ properties: { paddingUniform: num(0) }, selector: { id: "default" } }],
        accentBar: [
          {
            properties: {
              show: bool(true),
              position: str("Left"),
              color: solid(accentHex),
              width: num(4),
            },
            selector: { id: "default" },
          },
        ],
      },
      visualContainerObjects: {
        background: background(true),
        border: border(true),
        padding: [
          {
            properties: {
              top: num(8),
              bottom: num(8),
              left: num(8),
              right: num(8),
            },
            selector: { id: "default" },
          },
        ],
        visualHeader: visualHeader(false),
        title: [{ properties: { show: bool(false) } }],
        general: altText(alt),
      },
    },
  };
}

function topNFilter({ visualName, entity, fieldProperty, orderProperty, top, direction }) {
  const filterName =
    "Filter" + crypto.createHash("sha256").update(visualName).digest("hex").slice(0, 24);
  return {
    name: filterName,
    field: column(entity, fieldProperty),
    type: "TopN",
    filter: {
      Version: 2,
      From: [
        {
          Name: "subquery",
          Expression: {
            Subquery: {
              Query: {
                Version: 2,
                From: [{ Name: "c", Entity: entity, Type: 0 }],
                Select: [
                  {
                    Column: { Expression: { SourceRef: { Source: "c" } }, Property: fieldProperty },
                    Name: "field",
                  },
                ],
                OrderBy: [
                  {
                    Direction: direction,
                    Expression: {
                      Aggregation: {
                        Expression: {
                          Column: {
                            Expression: { SourceRef: { Source: "c" } },
                            Property: orderProperty,
                          },
                        },
                        Function: 1,
                      },
                    },
                  },
                  {
                    Direction: 1,
                    Expression: {
                      Column: {
                        Expression: { SourceRef: { Source: "c" } },
                        Property: fieldProperty,
                      },
                    },
                  },
                ],
                Top: top,
              },
            },
          },
          Type: 2,
        },
        { Name: "outer", Entity: entity, Type: 0 },
      ],
      Where: [
        {
          Condition: {
            In: {
              Expressions: [
                {
                  Column: {
                    Expression: { SourceRef: { Source: "outer" } },
                    Property: fieldProperty,
                  },
                },
              ],
              Table: { SourceRef: { Source: "subquery" } },
            },
          },
        },
      ],
    },
    howCreated: "User",
  };
}

function categoricalFilter({ visualName, entity, property, values }) {
  const filterName =
    "Filter" + crypto.createHash("sha256").update(`${visualName}-categorical`).digest("hex").slice(0, 24);
  return {
    name: filterName,
    field: column(entity, property),
    type: "Categorical",
    filter: {
      Version: 2,
      From: [{ Name: "c", Entity: entity, Type: 0 }],
      Where: [
        {
          Condition: {
            In: {
              Expressions: [
                {
                  Column: {
                    Expression: { SourceRef: { Source: "c" } },
                    Property: property,
                  },
                },
              ],
              Values: values.map((value) => [raw(`'${value}'`)]),
            },
          },
        },
      ],
    },
    howCreated: "User",
  };
}

function conditionalFill(entity, measureName) {
  const field = measure(entity, measureName);
  return {
    properties: {
      fill: {
        solid: {
          color: {
            expr: {
              Conditional: {
                Cases: [
                  {
                    Condition: {
                      Comparison: {
                        ComparisonKind: 3,
                        Left: field,
                        Right: raw("60D"),
                      },
                    },
                    Value: raw(`'${C.amber}'`),
                  },
                  {
                    Condition: {
                      Comparison: {
                        ComparisonKind: 2,
                        Left: field,
                        Right: raw("60D"),
                      },
                    },
                    Value: raw(`'${C.teal}'`),
                  },
                ],
              },
            },
          },
        },
      },
    },
    selector: { data: [{ dataViewWildcard: { matchingOption: 1 } }] },
  };
}

function barChart({
  name,
  x,
  y,
  width,
  height,
  title,
  categoryEntity,
  categoryProperty,
  yEntity,
  yMeasure,
  yNative,
  alt,
  topN,
  conditional,
  scopeColors,
  referenceLine,
  maxMargin = 45,
  categoryFontSize = 9,
  labelFontSize = 10,
  innerPadding = 12,
  preferredCategoryWidth = 18,
  subtitle = null,
  categoryFilterValues = null,
}) {
  const visual = {
    visualType: "barChart",
    query: {
      queryState: {
        Category: {
          projections: [
            projection(
              column(categoryEntity, categoryProperty),
              `${categoryEntity}.${categoryProperty}`,
              categoryProperty,
            ),
          ],
        },
        Y: {
          projections: [
            projection(measure(yEntity, yMeasure), `${yEntity}.${yMeasure}`, yNative),
          ],
        },
      },
      sortDefinition: {
        sort: [{ field: measure(yEntity, yMeasure), direction: "Ascending" }],
        isDefaultSort: false,
      },
    },
    objects: {
      labels: [
        {
          properties: {
            show: bool(true),
            fontSize: num(labelFontSize),
            bold: bool(true),
            color: solid(C.navy),
            labelPosition: str("OutsideEnd"),
          },
        },
      ],
      valueAxis: [
        { properties: { show: bool(false), gridlineShow: bool(false), showAxisTitle: bool(false) } },
      ],
      categoryAxis: [
        {
          properties: {
            show: bool(true),
            fontSize: num(categoryFontSize),
            labelColor: solid(C.inkSecondary),
            showAxisTitle: bool(false),
            gridlineShow: bool(false),
            maxMarginFactor: int(maxMargin),
            preferredCategoryWidth: int(preferredCategoryWidth),
            innerPadding: int(innerPadding),
          },
        },
      ],
      legend: [{ properties: { show: bool(false) } }],
    },
    visualContainerObjects: {
      background: background(true),
      border: border(true),
      padding: padding(8, 8, 8, 8),
      visualHeader: visualHeader(false),
      title: titleVco(title, 13),
      subTitle: subtitle
        ? [
            {
              properties: {
                show: bool(true),
                text: str(subtitle),
                fontSize: num(9),
                fontColor: solid(C.inkSecondary),
                alignment: str("left"),
              },
            },
          ]
        : subtitleVco(),
      general: altText(alt),
    },
  };

  const result = {
    $schema: SCHEMA_VISUAL,
    name,
    position: { x, y, z: 1000, height, width, tabOrder: 1000 },
    visual,
  };

  const filters = [];
  if (topN) {
    filters.push(
      topNFilter({
        visualName: name,
        entity: topN.entity,
        fieldProperty: topN.fieldProperty,
        orderProperty: topN.orderProperty,
        top: topN.top,
        direction: topN.direction,
      }),
    );
  }
  if (categoryFilterValues) {
    filters.push(
      categoricalFilter({
        visualName: name,
        entity: categoryEntity,
        property: categoryProperty,
        values: categoryFilterValues,
      }),
    );
  }
  if (filters.length) {
    result.filterConfig = { filters };
  }

  if (conditional) {
    visual.objects.dataPoint = [conditionalFill(yEntity, yMeasure)];
  } else if (scopeColors) {
    visual.objects.dataPoint = [
      { properties: { fill: solid(C.teal) } },
      ...scopeColors.map(([value, hex]) => ({
        properties: { fill: solid(hex) },
        selector: {
          data: [
            {
              scopeId: {
                Comparison: {
                  ComparisonKind: 0,
                  Left: column(categoryEntity, categoryProperty),
                  Right: raw(`'${value}'`),
                },
              },
            },
          ],
        },
      })),
    ];
  } else {
    visual.objects.dataPoint = [{ properties: { fill: solid(C.teal) } }];
  }

  if (referenceLine) {
    visual.objects.y1AxisReferenceLine = [
      {
        properties: {
          show: bool(true),
          displayName: str("Umbral 60%"),
          value: num(60),
          position: str("front"),
          width: num(1),
          lineColor: solid(C.amberDark),
          transparency: num(0),
          style: str("dashed"),
          dataLabelShow: bool(true),
          dataLabelText: str("Name"),
          dataLabelColor: solid(C.amberDark),
          dataLabelHorizontalPosition: str("right"),
          dataLabelVerticalPosition: str("above"),
        },
      },
    ];
  }

  return result;
}

function tableVisual({
  name,
  x,
  y,
  width,
  height,
  title,
  values,
  widths,
  sortBy,
  alt,
  fontSize = 10,
  titleSize = 13,
  outerPadding = 16,
  columnAlignments = [],
}) {
  const visual = {
    visualType: "tableEx",
    query: {
      queryState: {
        Values: {
          projections: values.map((value) =>
            projection(value.field, value.queryRef, value.native),
          ),
        },
      },
    },
    objects: {
      columnHeaders: [
        {
          properties: {
            autoSizeColumnWidth: bool(!widths),
            columnAdjustment: str(widths ? "fixedWidth" : "growToFit"),
            customColumnWidth: bool(Boolean(widths)),
            backColor: solid(C.headerBg),
            fontColor: solid(C.navy),
            fontSize: num(fontSize),
            bold: bool(true),
            alignment: str("Auto"),
          },
        },
      ],
      values: [
        {
          properties: {
            backColorPrimary: solid(C.white),
            backColorSecondary: solid(C.rowAlt),
            fontColorPrimary: solid(C.navy),
            fontColorSecondary: solid(C.navy),
            fontSize: num(fontSize),
            wordWrap: bool(false),
          },
        },
      ],
      grid: [
        {
          properties: {
            gridHorizontal: bool(true),
            gridHorizontalColor: solid(C.border),
            gridHorizontalWeight: num(1),
            gridVertical: bool(false),
            rowPadding: num(2),
          },
        },
      ],
      total: [{ properties: { totals: bool(false) } }],
    },
    visualContainerObjects: {
      background: background(true),
      border: border(true),
      padding: padding(outerPadding, outerPadding, outerPadding, outerPadding),
      visualHeader: visualHeader(false),
      title: titleVco(title, titleSize),
      subTitle: subtitleVco(),
      stylePreset: [{ properties: { name: str("None") } }],
      general: altText(alt),
    },
  };

  if (widths) {
    visual.objects.columnWidth = widths.map(({ queryRef, width: columnWidth }) => ({
      properties: { value: num(columnWidth) },
      selector: { metadata: queryRef },
    }));
  }
  if (columnAlignments.length) {
    visual.objects.columnFormatting = columnAlignments.map(({ queryRef, alignment }) => ({
      properties: {
        alignment: str(alignment),
        styleHeader: bool(true),
        styleValues: bool(true),
      },
      selector: { metadata: queryRef },
    }));
  }
  if (sortBy) {
    visual.query.sortDefinition = {
      sort: [{ field: sortBy, direction: "Ascending" }],
      isDefaultSort: false,
    };
  }

  return {
    $schema: SCHEMA_VISUAL,
    name,
    position: { x, y, z: 1000, height, width, tabOrder: 1000 },
    visual,
  };
}

function slicerVisual({ name, x, y, width, height, entity, property, header, alt }) {
  return {
    $schema: SCHEMA_VISUAL,
    name,
    position: { x, y, z: 1000, height, width, tabOrder: 1000 },
    visual: {
      visualType: "slicer",
      query: {
        queryState: {
          Values: {
            projections: [
              projection(column(entity, property), `${entity}.${property}`, property),
            ],
          },
        },
      },
      objects: {
        data: [{ properties: { mode: str("Dropdown") } }],
        header: [
          {
            properties: {
              show: bool(true),
              text: str(header),
              showRestatement: bool(false),
            },
          },
        ],
      },
      visualContainerObjects: {
        background: background(true),
        border: border(true),
        padding: padding(8, 8, 8, 8),
        visualHeader: visualHeader(false),
        general: altText(alt),
      },
    },
  };
}

function writePage(pageId, displayName) {
  const directory = path.join(ROOT, "pages", pageId);
  fs.mkdirSync(path.join(directory, "visuals"), { recursive: true });
  fs.writeFileSync(
    path.join(directory, "page.json"),
    `${JSON.stringify(
      {
        $schema: SCHEMA_PAGE,
        name: pageId,
        displayName,
        displayOption: "FitToPage",
        height: 1080,
        width: 1920,
        objects: {
          background: [
            { properties: { color: solid(C.canvas), transparency: num(0) } },
          ],
          outspace: [
            { properties: { color: solid(C.canvas), transparency: num(0) } },
          ],
        },
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
}

function resetVisuals(pageId) {
  fs.rmSync(path.join(ROOT, "pages", pageId, "visuals"), { recursive: true, force: true });
  fs.mkdirSync(path.join(ROOT, "pages", pageId, "visuals"), { recursive: true });
}

// ---------------------------------------------------------------------------
// Page 1 — Panorama
// ---------------------------------------------------------------------------

writePage(P1, "Panorama");
resetVisuals(P1);

writeVisual(
  P1,
  textbox({
    name: "1a2b3c4d5e6f708192a3",
    x: 32,
    y: 32,
    width: 1080,
    height: 64,
    paragraphs: [
      paragraph("La inversión municipal se queda atrás de las planillas", 32, C.navy, {
        family: "Segoe UI Semibold",
        bold: true,
      }),
    ],
  }),
);

writeVisual(
  P1,
  textbox({
    name: "2b3c4d5e6f708192a3b4",
    x: 1136,
    y: 32,
    width: 480,
    height: 64,
    paragraphs: [
      paragraph("Fuente: MEF · Consulta Amigable 2025", 11, C.inkSecondary, {
        align: "right",
      }),
      paragraph("1,892 municipalidades (25 departamentos) · 12/12 validaciones", 11, C.inkSecondary, {
        align: "right",
      }),
      paragraph("Barras en ámbar: ejecución menor al umbral de 60%", 11, C.inkSecondary, {
        align: "right",
      }),
    ],
  }),
);

writeVisual(
  P1,
  navButton({
    name: "3c4d5e6f708192a3b4c5",
    x: 1640,
    y: 40,
    width: 248,
    height: 44,
    label: "Ranking completo",
    targetPageId: P2,
    tooltip: "Ir al ranking completo de municipalidades",
    icon: "rightArrow",
    iconPlacement: "right",
    alt: "Botón para abrir el ranking completo de las 1,892 municipalidades",
  }),
);

writeVisual(
  P1,
  cardVisual({
    name: "4d5e6f708192a3b4c5d6",
    x: 32,
    y: 140,
    width: 440,
    height: 112,
    entity: "ExecutionByEntity",
    measureName: "Municipalidades",
    label: "Municipalidades analizadas",
    valueHex: C.navy,
    accentHex: C.teal,
    alt: "Tarjeta con 1,892 municipalidades analizadas",
    displayUnits: "0",
  }),
);

writeVisual(
  P1,
  cardVisual({
    name: "5e6f708192a3b4c5d6e7",
    x: 496,
    y: 140,
    width: 440,
    height: 112,
    entity: "ExecutionByEntity",
    measureName: "Ejecución promedio",
    label: "Ejecución promedio",
    valueHex: C.teal,
    accentHex: C.teal,
    alt: "Tarjeta con la ejecución promedio nacional de 79.5 por ciento",
  }),
);

writeVisual(
  P1,
  cardVisual({
    name: "6f708192a3b4c5d6e7f8",
    x: 960,
    y: 140,
    width: 440,
    height: 112,
    entity: "ExecutionByEntity",
    measureName: "Alertas <60%",
    label: "Alertas (< 60%)",
    valueHex: C.amber,
    accentHex: C.amber,
    alt: "Tarjeta con 196 municipalidades por debajo del umbral de alerta de 60 por ciento",
  }),
);

writeVisual(
  P1,
  cardVisual({
    name: "708192a3b4c5d6e7f809",
    x: 1424,
    y: 140,
    width: 464,
    height: 112,
    entity: "CategorySummary",
    measureName: "Brecha planillas-inversión",
    label: "Brecha planillas vs. inversión",
    valueHex: C.amber,
    accentHex: C.amber,
    alt: "Tarjeta con la brecha de 21.2 puntos entre planillas e inversión",
  }),
);

writeVisual(
  P1,
  barChart({
    name: "8192a3b4c5d6e7f8091a",
    x: 32,
    y: 296,
    width: 916,
    height: 496,
    title: "Las 10 municipalidades con menor ejecución",
    categoryEntity: "ExecutionByEntity",
    categoryProperty: "Municipalidad",
    yEntity: "ExecutionByEntity",
    yMeasure: "Ejecución % entidad",
    yNative: "Ejecución % entidad",
    alt: "Barras horizontales de las 10 municipalidades con menor ejecución a nivel nacional; Eleazar Guzmán Barrón 13.2%, Tapacocha 16.4%, Coris 20.2%, con umbral de alerta de 60%.",
    topN: {
      entity: "ExecutionByEntity",
      fieldProperty: "Municipalidad",
      orderProperty: "execution_pct",
      top: 10,
      direction: 1,
    },
    conditional: true,
    maxMargin: 45,
    categoryFontSize: 9,
    labelFontSize: 9,
    innerPadding: 8,
    preferredCategoryWidth: 20,
  }),
);

writeVisual(
  P1,
  barChart({
    name: "92a3b4c5d6e7f8091a2b",
    x: 972,
    y: 296,
    width: 916,
    height: 232,
    title: "Ejecución por genérica del gasto (6 principales)",
    categoryEntity: "CategorySummary",
    categoryProperty: "Categoría",
    yEntity: "CategorySummary",
    yMeasure: "Ejecución %",
    yNative: "Ejecución %",
    alt: "Barras por genérica del gasto; inversión en 72.9%, planillas en 94.1%, transferencias en 90.2%.",
    scopeColors: [
      ["Inversión", C.tealDark],
      ["Activos financieros", C.gray],
    ],
    maxMargin: 42,
    categoryFontSize: 8,
    labelFontSize: 8,
    innerPadding: 0,
    preferredCategoryWidth: 10,
    categoryFilterValues: [
      "Personal",
      "Inversión",
      "Transferencias",
      "Bienes y servicios",
      "Otros gastos",
      "Deuda pública",
    ],
  }),
);

writeVisual(
  P1,
  barChart({
    name: "a3b4c5d6e7f8091a2b3c",
    x: 972,
    y: 552,
    width: 916,
    height: 240,
    title: "Departamentos con menor ejecución (7 de 25)",
    categoryEntity: "DepartmentSummary",
    categoryProperty: "Departamento",
    yEntity: "DepartmentSummary",
    yMeasure: "Ejecución % departamento",
    yNative: "Ejecución % departamento",
    alt: "Barras con los 7 departamentos de menor ejecución; Áncash 68.7%, Pasco 71.1%, Ica 71.2%.",
    topN: {
      entity: "DepartmentSummary",
      fieldProperty: "Departamento",
      orderProperty: "execution_pct",
      top: 7,
      direction: 1,
    },
    maxMargin: 45,
    categoryFontSize: 9,
    labelFontSize: 9,
    innerPadding: 4,
    preferredCategoryWidth: 14,
  }),
);

writeVisual(
  P1,
  tableVisual({
    name: "b4c5d6e7f8091a2b3c4d",
    x: 32,
    y: 816,
    width: 1856,
    height: 232,
    title: "Evidencia de calidad del run",
    values: [
      {
        field: column("QualitySummary", "Métrica"),
        queryRef: "QualitySummary.Métrica",
        native: "Métrica",
      },
      {
        field: measure("QualitySummary", "Valor"),
        queryRef: "QualitySummary.Valor",
        native: "Valor",
      },
    ],
    alt: "Tabla de evidencia de calidad del run nacional: 1,892 municipalidades, 12/12 validaciones, 196 alertas.",
    fontSize: 9,
    titleSize: 12,
    outerPadding: 12,
    columnAlignments: [{ queryRef: "QualitySummary.Valor", alignment: "Right" }],
  }),
);

// ---------------------------------------------------------------------------
// Page 2 — Ranking completo
// ---------------------------------------------------------------------------

writePage(P2, "Ranking completo");
resetVisuals(P2);

writeVisual(
  P2,
  textbox({
    name: "d6e7f8091a2b3c4d5e6f",
    x: 32,
    y: 32,
    width: 1080,
    height: 64,
    paragraphs: [
      paragraph("Ranking completo: las 1,892 municipalidades del Perú", 32, C.navy, {
        family: "Segoe UI Semibold",
        bold: true,
      }),
    ],
  }),
);

writeVisual(
  P2,
  textbox({
    name: "e7f8091a2b3c4d5e6f70",
    x: 1136,
    y: 32,
    width: 480,
    height: 64,
    paragraphs: [
      paragraph("Ordenado por puesto (1 = mayor ejecución)", 11, C.inkSecondary, {
        align: "right",
      }),
      paragraph("Fuente: MEF · Consulta Amigable 2025", 11, C.inkSecondary, {
        align: "right",
      }),
    ],
  }),
);

writeVisual(
  P2,
  navButton({
    name: "f8091a2b3c4d5e6f7081",
    x: 1712,
    y: 40,
    width: 176,
    height: 44,
    label: "Panorama",
    targetPageId: P1,
    tooltip: "Volver al panorama",
    icon: "leftArrow",
    iconPlacement: "left",
    alt: "Botón para volver al panorama",
  }),
);

writeVisual(
  P2,
  slicerVisual({
    name: "3a4b5c6d7e8f90123456",
    x: 32,
    y: 120,
    width: 360,
    height: 80,
    entity: "ExecutionByEntity",
    property: "Departamento",
    header: "Departamento",
    alt: "Selector desplegable para filtrar el ranking por departamento",
  }),
);

writeVisual(
  P2,
  slicerVisual({
    name: "091a2b3c4d5e6f708192",
    x: 416,
    y: 120,
    width: 480,
    height: 80,
    entity: "ExecutionByEntity",
    property: "Municipalidad",
    header: "Buscar municipalidad",
    alt: "Selector desplegable para buscar una municipalidad entre las 1,892 del ranking",
  }),
);

writeVisual(
  P2,
  textbox({
    name: "1a2b3c4d5e6f708192a4",
    x: 920,
    y: 136,
    width: 800,
    height: 48,
    paragraphs: [
      paragraph("Selecciona un departamento o busca una municipalidad.", 11, C.inkSecondary),
      paragraph("El ranking está ordenado por puesto: 1 = mayor ejecución.", 11, C.inkSecondary),
    ],
  }),
);

writeVisual(
  P2,
  tableVisual({
    name: "2b3c4d5e6f708192a3b5",
    x: 32,
    y: 224,
    width: 1856,
    height: 824,
    title: "Detalle por municipalidad",
    values: [
      {
        field: measure("ExecutionByEntity", "Puesto"),
        queryRef: "ExecutionByEntity.Puesto",
        native: "Puesto",
      },
      {
        field: column("ExecutionByEntity", "Municipalidad"),
        queryRef: "ExecutionByEntity.Municipalidad",
        native: "Municipalidad",
      },
      {
        field: column("ExecutionByEntity", "Departamento"),
        queryRef: "ExecutionByEntity.Departamento",
        native: "Departamento",
      },
      {
        field: measure("ExecutionByEntity", "PIM total"),
        queryRef: "ExecutionByEntity.PIM total",
        native: "PIM total",
      },
      {
        field: measure("ExecutionByEntity", "Devengado total"),
        queryRef: "ExecutionByEntity.Devengado total",
        native: "Devengado total",
      },
      {
        field: measure("ExecutionByEntity", "Ejecución % entidad"),
        queryRef: "ExecutionByEntity.Ejecución % entidad",
        native: "Ejecución % entidad",
      },
    ],
    widths: [
      { queryRef: "ExecutionByEntity.Puesto", width: 72 },
      { queryRef: "ExecutionByEntity.Municipalidad", width: 760 },
      { queryRef: "ExecutionByEntity.Departamento", width: 200 },
      { queryRef: "ExecutionByEntity.PIM total", width: 260 },
      { queryRef: "ExecutionByEntity.Devengado total", width: 260 },
      { queryRef: "ExecutionByEntity.Ejecución % entidad", width: 240 },
    ],
    sortBy: measure("ExecutionByEntity", "Puesto"),
    alt: "Tabla del ranking completo de 1,892 municipalidades del Perú con puesto, departamento, PIM, devengado y porcentaje de ejecución.",
    fontSize: 10,
    titleSize: 13,
    outerPadding: 16,
    columnAlignments: [
      { queryRef: "ExecutionByEntity.Puesto", alignment: "Right" },
      { queryRef: "ExecutionByEntity.PIM total", alignment: "Right" },
      { queryRef: "ExecutionByEntity.Devengado total", alignment: "Right" },
      { queryRef: "ExecutionByEntity.Ejecución % entidad", alignment: "Right" },
    ],
  }),
);

fs.writeFileSync(
  path.join(ROOT, "pages", "pages.json"),
  `${JSON.stringify(
    {
      $schema: SCHEMA_PAGES,
      pageOrder: [P1, P2],
      activePageName: P1,
    },
    null,
    2,
  )}\n`,
  "utf8",
);

console.log("Report pages and visuals written.");

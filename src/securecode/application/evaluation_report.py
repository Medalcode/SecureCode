from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from securecode.api.normative_transparency import CONTROL_METADATA, SCOPE_WARNING

_PAGE_WIDTH = 595
_PAGE_HEIGHT = 792
_MARGIN_X = 48
_TOP_Y = 744
_BOTTOM_Y = 64
_WRAP_LIMIT = 96

_REPLACEMENTS = {
    "—": "-",
    "–": "-",
    "≥": ">=",
    "≤": "<=",
    "→": "->",
    "·": "-",
    "“": '"',
    "”": '"',
    "’": "'",
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "ñ": "n",
    "Á": "A",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "Ñ": "N",
}


def _safe_text(value: Any) -> str:
    text = str(value)
    for source, target in _REPLACEMENTS.items():
        text = text.replace(source, target)
    text = text.encode("cp1252", errors="replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", " ").replace("\n", " ")


def _wrap(value: Any, limit: int = _WRAP_LIMIT) -> list[str]:
    text = str(value)
    if not text.strip():
        return [""]
    lines: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > limit:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:limit])
            word = word[limit:]
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= limit:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _display_value(value: Any) -> str:
    if value is None:
        return "No disponible"
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _pdf_date(value: datetime) -> str:
    return value.strftime("D:%Y%m%d%H%M%SZ")


class _PdfBuilder:
    def __init__(self, title: str, footer: str):
        self._title = title
        self._footer = footer
        self._pages: list[list[str]] = []
        self._lines: list[str] = []
        self._y = _TOP_Y

    def _new_page(self) -> None:
        if self._lines:
            self._pages.append(self._lines)
        self._lines = []
        self._y = _TOP_Y

    def _write(self, text: str, *, size: int = 10, bold: bool = False, leading: int | None = None) -> None:
        if self._y < _BOTTOM_Y:
            self._new_page()
        font = "/F2" if bold else "/F1"
        self._lines.append(
            f"BT {font} {size} Tf 0 0 0 rg 1 0 0 1 {_MARGIN_X} {self._y} Tm ({_safe_text(text)}) Tj ET"
        )
        self._y -= leading or size + 4

    def _separator(self) -> None:
        if self._y < _BOTTOM_Y:
            self._new_page()
        self._lines.append(
            f"0.6 w 0.75 0.75 0.75 RG {_MARGIN_X} {self._y + 4} m {_PAGE_WIDTH - _MARGIN_X} {self._y + 4} l S"
        )
        self._y -= 10

    def title(self, value: str) -> None:
        self._write(value, size=17, bold=True, leading=22)
        self._separator()

    def heading(self, value: str) -> None:
        self._y -= 6
        self._write(value, size=12, bold=True, leading=18)
        self._separator()

    def paragraph(self, value: str, *, size: int = 10) -> None:
        for line in _wrap(value):
            self._write(line, size=size)

    def key_value(self, label: str, value: Any) -> None:
        prefix = f"{label}: "
        available = _WRAP_LIMIT - len(prefix)
        lines = _wrap(value, max(24, available))
        self._write(f"{prefix}{lines[0]}", bold=True)
        for line in lines[1:]:
            self._write(line)

    def bullet(self, value: str) -> None:
        lines = _wrap(value, _WRAP_LIMIT - 3)
        self._write(f"- {lines[0]}")
        for line in lines[1:]:
            self._write(f"  {line}")

    def build(self, *, generated_at: datetime) -> bytes:
        self._new_page()
        page_count = len(self._pages)
        for index, lines in enumerate(self._pages, start=1):
            lines.append(
                f"BT /F1 8 Tf 0.35 0.35 0.35 rg 1 0 0 1 {_MARGIN_X} 34 Tm "
                f"({_safe_text(self._footer)}) Tj ET"
            )
            lines.append(
                f"BT /F1 8 Tf 0.35 0.35 0.35 rg 1 0 0 1 520 34 Tm "
                f"({_safe_text(f'{index}/{page_count}')}) Tj ET"
            )

        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]

        stream_ids: list[int] = []
        for lines in self._pages:
            stream = ("\n".join(lines) + "\n").encode("cp1252", errors="replace")
            stream_ids.append(len(objects) + 1)
            objects.append(
                f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
                + stream
                + b"endstream"
            )

        page_ids: list[int] = []
        for stream_id in stream_ids:
            page_ids.append(len(objects) + 1)
            objects.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE_WIDTH} {_PAGE_HEIGHT}] "
                    f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {stream_id} 0 R >>"
                ).encode("ascii")
            )

        objects[1] = (
            f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>"
        ).encode("ascii")

        info_id = len(objects) + 1
        objects.append(
            (
                f"<< /Title ({_safe_text(self._title)}) /Producer (SecureCode) /Creator (SecureCode) "
                f"/CreationDate ({_pdf_date(generated_at)}) >>"
            ).encode("ascii")
        )

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for number, payload in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{number} 0 obj\n".encode("ascii"))
            output.extend(payload)
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        return bytes(output)


def build_evaluation_report_pdf(
    *,
    evaluation_id: str,
    control_id: str,
    status: str,
    source_repository: str,
    source_branch: str,
    collected_at: str,
    evaluated_at: str,
    explanation: dict[str, Any],
    generated_at: datetime,
) -> bytes:
    metadata = CONTROL_METADATA.get(control_id, {})
    title = f"Informe de evaluacion {control_id}"
    builder = _PdfBuilder(
        title=title,
        footer=f"SecureCode | Generado {generated_at.isoformat()} | Informe de alcance parcial",
    )

    builder.title("SecureCode - Resultado Explicable")
    builder.paragraph(
        "Documento generado exclusivamente a partir de la evidencia persistida de una evaluacion. "
        "No consulta GitHub, no modifica repositorios y no certifica cumplimiento NIST, ISO ni de otro marco."
    )

    builder.heading("1. Identificacion de la evaluacion")
    builder.key_value("ID de evaluacion", evaluation_id)
    builder.key_value("Control", control_id)
    builder.key_value("Dictamen almacenado", status)
    builder.key_value("Repositorio", source_repository)
    builder.key_value("Rama", source_branch)
    builder.key_value("Evidencia recopilada", collected_at)
    builder.key_value("Evaluacion realizada", evaluated_at)
    builder.key_value("Informe generado", generated_at.isoformat())

    summary = explanation.get("summary", {})
    builder.heading("2. Dictamen y lectura")
    builder.key_value("Motivo", str(summary.get("reason", "")))
    builder.key_value("Significado", str(summary.get("meaning", "")))
    builder.key_value("Precision", str(summary.get("note", "")))
    builder.paragraph(str(summary.get("scope_warning", SCOPE_WARNING)))

    rule = explanation.get("rule", {})
    builder.heading("3. Regla aplicada")
    builder.key_value("Identificador", str(rule.get("id") or "No informado"))
    builder.key_value("Version", _display_value(rule.get("version")))
    builder.key_value("Expresion exacta", str(rule.get("expression", "")))
    builder.paragraph(
        "Los campos evaluados estan restringidos a la lista permitida por la regla. "
        "El motor no interpreta texto libre ni consulta fuentes externas durante este informe."
    )

    builder.heading("4. Condiciones contrastadas")
    conditions = explanation.get("conditions", [])
    if conditions:
        for index, condition in enumerate(conditions, start=1):
            builder.key_value(
                f"Condicion {index}",
                f"{condition.get('label')} | Politica: {condition.get('expected_display')} | "
                f"Observado: {condition.get('observed_display')} | Resultado: {condition.get('status')}",
            )
            builder.paragraph(str(condition.get("explanation", "")))
    else:
        builder.paragraph("No fue posible reconstruir el detalle de condiciones desde el catalogo de reglas disponible.")

    evidence = explanation.get("evidence", {})
    builder.heading("5. Evidencia e integridad")
    for field, value in evidence.get("fields", {}).items():
        builder.key_value(field, _display_value(value))
    builder.key_value("Huella almacenada", str(evidence.get("stored_hash", "")))
    builder.key_value("Huella reconstruida", str(evidence.get("recomputed_hash", "")))
    builder.key_value("Integridad valida", "Si" if evidence.get("integrity_valid") else "No")

    traceability = explanation.get("normative_traceability", {})
    builder.heading("6. Trazabilidad normativa parcial")
    builder.key_value("Marco", str(traceability.get("framework", "")))
    builder.key_value("Metodologia", str(traceability.get("methodology", "")))
    builder.key_value("Objetivo", str(traceability.get("objective", "")))
    controls = traceability.get("controls", [])
    if controls:
        builder.key_value(
            "Controles seleccionados",
            ", ".join(f"{item.get('id')} ({item.get('relationship')})" for item in controls),
        )
    builder.key_value("Correspondencia", str(traceability.get("correspondence", "parcial")))
    builder.paragraph(str(traceability.get("limitations", "")))
    builder.paragraph(str(traceability.get("disclaimer", SCOPE_WARNING)))

    builder.heading("7. Recomendaciones")
    recommendations = explanation.get("recommendations", [])
    if recommendations:
        for recommendation in recommendations:
            builder.bullet(str(recommendation))
    else:
        builder.paragraph("No hay recomendaciones adicionales para el dictamen almacenado.")

    builder.heading("8. Reconstruccion y advertencias")
    reconstruction = explanation.get("reconstruction", {})
    builder.key_value("Resultado reconstruido", _display_value(reconstruction.get("computed_status")))
    builder.key_value(
        "Consistente con el dictamen almacenado",
        "Si" if reconstruction.get("consistent_with_stored_status") else "No",
    )
    warnings = reconstruction.get("warnings", [])
    if warnings:
        for warning in warnings:
            builder.bullet(str(warning))
    else:
        builder.paragraph("No se registraron advertencias de reconstruccion.")

    builder.heading("9. Alcance del informe")
    builder.paragraph(
        f"Este informe cubre unicamente el control {control_id} y la evidencia tecnica observable registrada "
        f"en la evaluacion {evaluation_id}. No cubre personas, procesos, politicas organizacionales completas "
        "ni otros controles del marco de referencia."
    )
    builder.paragraph(str(metadata.get("evidence", "")))
    builder.paragraph(SCOPE_WARNING)

    builder.heading("10. Verificacion")
    builder.paragraph(
        "La huella SHA-256 permite comprobar que la evidencia no fue alterada. El enlace publico de verificacion "
        "no revela repositorio, rama ni identidad del solicitante."
    )

    return builder.build(generated_at=generated_at)

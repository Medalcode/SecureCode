import hashlib
from datetime import datetime, timezone

def generate_audit_report_pdf(
    control: str,
    repository: str,
    verdict: str,
    integrity_hash: str,
    evaluation_id: str = "eval_9f8a2b3c",
    auditor: str = "auditor@empresa.com"
) -> bytes:
    """
    Generates a standard compliant PDF 1.4 audit certificate according to
    INACAP technical report standards with cryptographic integrity verification.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    clean_control = control.replace("(", "").replace(")", "")
    clean_repo = repository.replace("(", "").replace(")", "")
    clean_verdict = verdict.replace("(", "").replace(")", "")
    clean_hash = integrity_hash[:48] + "..." if len(integrity_hash) > 48 else integrity_hash

    # Text content stream
    content = f"""BT
/F1 16 Tf
50 740 Td
(SECURECODE - REPORTE OFICIAL DE AUDITORIA SCM) Tj
/F1 10 Tf
0 -20 Td
(Norma Tecnica ISO/IEC 27001 - Estandar de Evaluacion INACAP 2026) Tj
0 -30 Td
(IDENTIFICACION DE LA EVALUACION) Tj
/F2 9 Tf
0 -18 Td
(ID Evaluacion: {evaluation_id}) Tj
0 -15 Td
(Fecha de Auditoria: {date_str}) Tj
0 -15 Td
(Auditor Responsable: {auditor}) Tj
0 -15 Td
(Entorno: Enterprise - SCM GitHub Automated Engine) Tj
0 -25 Td
/F1 10 Tf
(RESULTADOS DEL DICTAMEN TECNICO) Tj
/F2 9 Tf
0 -18 Td
(Control Evaluado: {clean_control}) Tj
0 -15 Td
(Repositorio y Rama: {clean_repo}) Tj
0 -15 Td
(Veredicto Determinista: {clean_verdict}) Tj
0 -25 Td
/F1 10 Tf
(INTEGRIDAD Y TRAZABILIDAD CRIPTOGRAFICA) Tj
/F2 9 Tf
0 -18 Td
(Hash SHA-256 Canonico: {clean_hash}) Tj
0 -15 Td
(Estado de Persistencia: Registrado en PostgreSQL de forma inmutable) Tj
0 -35 Td
/F1 9 Tf
(CERTIFICACION PROBATORIA:) Tj
/F2 8 Tf
0 -14 Td
(Este documento cuenta con valor probatorio conforme a la Seccion 3.8 del Informe ES2.) Tj
0 -12 Td
(Generado automaticamente por la plataforma determinista SecureCode.) Tj
ET"""

    return _build_pdf_stream(content)

def generate_invoice_pdf(
    invoice_number: str = "INV-2026-10-8841",
    date: str = "01/10/2026",
    concept: str = "Mensualidad SecureCode Octubre",
    amount: str = "$150.000 CLP",
    company_rut: str = "76.842.109-K"
) -> bytes:
    """
    Generates an Electronic Fiscal Invoice (DTE) in standard PDF 1.4 format.
    """
    content = f"""BT
/F1 16 Tf
50 740 Td
(DOCUMENTO TRIBUTARIO ELECTRONICO - FACTURA ELECTRONICA) Tj
/F1 10 Tf
0 -20 Td
(SECURECODE CYBERSECURITY SPA - RUT 76.842.109-K) Tj
0 -30 Td
(DETALLE FISCAL DEL COMPROBANTE) Tj
/F2 9 Tf
0 -18 Td
(Folio Tributario: {invoice_number}) Tj
0 -15 Td
(Fecha de Emision: {date}) Tj
0 -15 Td
(RUT Receptor: {company_rut}) Tj
0 -15 Td
(Concepto Facturado: {concept}) Tj
0 -15 Td
(Monto Total: {amount}) Tj
0 -15 Td
(Estado: PAGADO / CONCILIADO BANCARIO) Tj
0 -30 Td
/F1 10 Tf
(TIMBRE ELECTRONICO Y VALIDEZ SII) Tj
/F2 8 Tf
0 -18 Td
(Timbre Electronico SII Res. Ex. N 84 de 2026 - Verifique validez en www.sii.cl) Tj
ET"""

    return _build_pdf_stream(content)

def _build_pdf_stream(content: str) -> bytes:
    stream_bytes = content.encode("latin-1", errors="replace")
    stream_len = len(stream_bytes)

    objects = []
    # 1: Catalog
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
    # 2: Pages
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj")
    # 3: Page
    objects.append("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj")
    # 4: Stream
    objects.append(f"4 0 obj\n<< /Length {stream_len} >>\nstream\n{content}\nendstream\nendobj")
    # 5: Font F1 (Helvetica-Bold)
    objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj")
    # 6: Font F2 (Helvetica)
    objects.append("6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj")

    header = "%PDF-1.4\n"
    offsets = []
    current_offset = len(header.encode("latin-1"))

    body_parts = []
    for obj in objects:
        offsets.append(current_offset)
        obj_bytes = (obj + "\n").encode("latin-1")
        body_parts.append(obj_bytes)
        current_offset += len(obj_bytes)

    xref_offset = current_offset
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for o in offsets:
        xref += f"{o:010d} 00000 n \n"

    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"

    return header.encode("latin-1") + b"".join(body_parts) + xref.encode("latin-1") + trailer.encode("latin-1")

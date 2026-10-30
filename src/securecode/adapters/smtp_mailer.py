import os
import smtplib
import logging
from email.message import EmailMessage
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def dispatch_email(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: str = "Dictamen_Auditoria.pdf"
) -> Dict[str, Any]:
    """
    Dispatches an email with optional PDF attachment.
    If SMTP_USER and SMTP_PASSWORD are not configured in environment,
    it operates in auditable Sandbox mode without failing.
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        logger.info(
            f"[SMTP Sandbox] Despacho simulado para {to_email}. "
            "Credenciales SMTP_USER / SMTP_PASSWORD no configuradas en el entorno."
        )
        return {
            "sent": False,
            "mode": "sandbox",
            "message": (
                f"Despacho registrado en trazabilidad local (Modo Sandbox). "
                f"Para entrega directa a {to_email} se requiere configurar servidor SMTP saliente."
            )
        }

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg.set_content(body)

        if attachment_bytes:
            msg.add_attachment(
                attachment_bytes,
                maintype="application",
                subtype="pdf",
                filename=attachment_filename
            )

        with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"[SMTP Live] Correo enviado exitosamente a {to_email}")
        return {
            "sent": True,
            "mode": "live",
            "message": f"Correo despachado y entregado exitosamente a {to_email}"
        }
    except Exception as e:
        logger.error(f"[SMTP Error] Fallo al despachar correo a {to_email}: {e}")
        return {
            "sent": False,
            "mode": "error",
            "message": f"Fallo de conexión SMTP ({type(e).__name__}): {str(e)}"
        }


"""Public pages, isolated from the authenticated SecureCode console."""

from __future__ import annotations

from html import escape

SITE_UPDATED_AT = "15 de noviembre de 2026"
LEGAL_NOTICE = (
    "Borrador académico: este texto debe ser revisado por asesoría jurídica y "
    "completado con la identidad, domicilio y canal de contacto del proveedor "
    "antes de cualquier operación comercial."
)

NAVIGATION = (
    ("/", "Inicio"),
    ("/nosotros", "Nosotros"),
    ("/preguntas-frecuentes", "FAQ"),
    ("/contacto", "Contacto"),
)
LEGAL_LINKS = (
    ("/legal/terminos", "Términos de servicio"),
    ("/legal/privacidad", "Privacidad"),
    ("/legal/cookies", "Cookies"),
    ("/legal/eula", "EULA"),
    ("/legal/contratacion", "Contratación y reembolsos"),
    ("/legal/sla", "Acuerdo de nivel de servicio"),
)


def _navigation(active_path: str) -> str:
    links = "".join(
        '<a href="' + href + ('" aria-current="page"' if href == active_path else '"') + ">" + label + "</a>"
        for href, label in NAVIGATION
    )
    return (
        '<header class="public-header">'
        '<a class="public-brand" href="/" aria-label="SecureCode, inicio">'
        '<img class="public-mark" src="/static/public/securecode-mark.svg" alt=""><span>SecureCode</span></a>'
        '<nav class="public-nav" aria-label="Navegación principal">' + links + "</nav>"
        '<a class="public-login" href="/app">Abrir consola <span aria-hidden="true">→</span></a>'
        "</header>"
    )


def _footer() -> str:
    legal_links = "".join('<a href="' + href + '">' + label + "</a>" for href, label in LEGAL_LINKS)
    return (
        '<footer class="public-footer"><div>'
        '<a class="public-brand" href="/"><img class="public-mark" src="/static/public/securecode-mark.svg" alt=""><span>SecureCode</span></a>'
        "<p>Evaluación verificable de controles para repositorios de código.</p></div>"
        '<nav aria-label="Documentos legales">' + legal_links + "</nav>"
        '<p class="footer-note">Proyecto académico · ' + SITE_UPDATED_AT + "</p></footer>"
    )


def page(title: str, description: str, content: str, path: str, *, legal: bool = False) -> str:
    notice = (
        '<aside class="legal-notice" role="note"><strong>Estado del documento:</strong> ' + LEGAL_NOTICE + "</aside>"
        if legal
        else ""
    )
    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="description" content="' + escape(description) + '">'
        '<meta name="color-scheme" content="light"><title>' + escape(title) + " | SecureCode</title>"
        '<link rel="stylesheet" href="/static/public/site.css?v=20261115-public-site"></head>'
        '<body class="public-site"><a class="skip-link" href="#contenido">Saltar al contenido</a>'
        + _navigation(path) + '<main id="contenido">' + notice + content + "</main>" + _footer() + "</body></html>"
    )


HOME = """
<section class="hero">
  <div class="eyebrow">GOBIERNO DE INGENIERÍA · EVIDENCIA REPRODUCIBLE</div>
  <h1>Confianza técnica<br><em>para cada cambio.</em></h1>
  <p class="hero-copy">SecureCode transforma políticas de repositorio en evaluaciones claras, evidencia sellada y decisiones que un equipo puede comprobar.</p>
  <div class="hero-actions"><a class="button button-primary" href="/app">Ingresar a la plataforma <span aria-hidden="true">→</span></a><a class="button button-secondary" href="#como-funciona">Conocer cómo funciona</a></div>
  <p class="hero-proof"><span></span> Controles declarativos · Evidencia SHA-256 · Acceso por organización</p>
</section>
<section class="feature-grid" aria-label="Beneficios de SecureCode">
  <article><span class="feature-number">01</span><h2>Define el alcance</h2><p>El propietario de cada organización autoriza los repositorios que su equipo puede evaluar.</p></article>
  <article><span class="feature-number">02</span><h2>Contrasta la evidencia</h2><p>Los controles consultan la configuración observable y entregan un dictamen determinista.</p></article>
  <article><span class="feature-number">03</span><h2>Conserva trazabilidad</h2><p>Cada resultado conserva su evidencia normalizada y una huella criptográfica verificable.</p></article>
</section>
<section class="split-section" id="como-funciona">
  <div><p class="eyebrow">UNA RUTA DE TRABAJO CLARA</p><h2>Del repositorio al dictamen, sin perder contexto.</h2></div>
  <ol class="steps"><li><strong>Autoriza</strong><span>El propietario delimita analistas y repositorios de su organización.</span></li><li><strong>Evalúa</strong><span>El analista ejecuta el control sobre una rama explícita.</span></li><li><strong>Verifica</strong><span>El resultado incluye criterios, evidencia y hash para su revisión.</span></li></ol>
</section>
<section class="callout"><div><p class="eyebrow">LISTO PARA UNA DEMOSTRACIÓN</p><h2>Explora la consola de evaluación.</h2><p>La interfaz separa las funciones públicas de las funciones que requieren autenticación.</p></div><a class="button button-primary" href="/app">Abrir consola</a></section>
"""

ABOUT = """
<section class="page-hero"><p class="eyebrow">SOBRE SECURECODE</p><h1>Gobierno de cambios con evidencia que se puede revisar.</h1><p>SecureCode es un proyecto académico que demuestra una plataforma de evaluación automatizada para políticas de repositorios de código.</p></section>
<section class="content-grid"><article><h2>Propósito</h2><p>Reducir la distancia entre una política declarada y la evidencia técnica que permite comprobarla.</p></article><article><h2>Principios</h2><p>Privilegio mínimo, trazabilidad, decisiones reproducibles y separación entre la plataforma, cada organización y sus analistas.</p></article><article><h2>Alcance actual</h2><p>La plataforma incluye controles canónicos de revisión de cambios, protección de rama y firmas de commits.</p></article></section>
<section class="prose"><h2>Una base mantenible</h2><p>La solución separa la interfaz pública, la consola autenticada, las reglas declarativas y los adaptadores de infraestructura. Esta división permite evolucionar cada área sin convertir la aplicación en una única pieza difícil de probar.</p></section>
"""

CONTACT = """
<section class="page-hero compact"><p class="eyebrow">CONTACTO</p><h1>Preparar una conversación segura empieza por dejar claro el canal.</h1><p>El canal comercial definitivo aún no está configurado para este proyecto académico.</p></section>
<section class="contact-layout"><article class="contact-card"><h2>Canal de contacto pendiente</h2><p>Antes de ofrecer el servicio comercialmente se debe configurar un correo corporativo, responsable de privacidad y domicilio de notificación.</p><p class="muted">No ingreses datos personales ni credenciales en esta página mientras esos datos estén pendientes.</p></article><article class="contact-card"><h2>Para la demostración</h2><p>La consola permite revisar el flujo de organizaciones, analistas, autorizaciones y evaluaciones mediante cuentas de prueba autorizadas.</p><a class="text-link" href="/app">Abrir la consola →</a></article></section>
"""

FAQ = """
<section class="page-hero compact"><p class="eyebrow">PREGUNTAS FRECUENTES</p><h1>Lo esencial, sin letra pequeña.</h1><p>Estas respuestas describen el alcance demostrable de la plataforma.</p></section>
<section class="faq-list"><details open><summary>¿Qué evalúa SecureCode?</summary><p>Controles declarativos sobre la configuración observable de un repositorio y una rama, como revisiones requeridas, protección de rama y firmas de commits.</p></details><details><summary>¿Quién puede autorizar un repositorio?</summary><p>El Organization Owner de cada organización. Los Analyst sólo pueden evaluar repositorios que hayan sido autorizados para su cuenta.</p></details><details><summary>¿Qué ocurre con la evidencia?</summary><p>La aplicación conserva el dictamen, criterios contrastados y una huella SHA-256 de la evidencia canónica para permitir su verificación.</p></details><details><summary>¿Se procesan pagos reales?</summary><p>No. El proyecto académico puede mostrar escenarios de plan y consumo, pero no procesa cobros ni medios de pago reales.</p></details><details><summary>¿Cómo se crean las cuentas?</summary><p>Una organización crea inicialmente su cuenta propietaria. Desde Mi Organización, el propietario puede crear cuentas Analyst y limitar sus repositorios autorizados.</p></details></section>
"""

LEGAL_CONTENT: dict[str, tuple[str, str]] = {
    "terminos": ("Términos de servicio", "<h1>Términos de servicio</h1><p>Estos términos describen el uso previsto de SecureCode como demostración académica. No constituyen una oferta comercial vigente ni sustituyen una revisión legal.</p><h2>Uso autorizado</h2><p>El acceso se limita a cuentas creadas por la plataforma y a los repositorios que una organización haya autorizado. Cada usuario es responsable de proteger sus credenciales y de revisar los resultados antes de tomar decisiones.</p><h2>Disponibilidad y cambios</h2><p>La funcionalidad puede cambiar durante la etapa académica. Una oferta comercial deberá definir soporte, disponibilidad, tratamiento de datos y responsables mediante un acuerdo definitivo.</p>"),
    "privacidad": ("Política de privacidad", "<h1>Política de privacidad</h1><p>SecureCode procesa cuentas, roles, configuraciones y evidencias necesarias para operar la demostración. La plataforma no debe recibir secretos, tokens ni información personal innecesaria en campos de repositorio.</p><h2>Finalidad</h2><p>Los datos se usan para autenticar usuarios, separar organizaciones, autorizar evaluaciones y mantener trazabilidad de las acciones realizadas.</p><h2>Pendiente antes de producción</h2><p>Antes de un lanzamiento comercial se deberán definir responsable del tratamiento, plazos de conservación, mecanismo de solicitudes de titulares y canal de contacto de privacidad.</p>"),
    "cookies": ("Política de cookies", "<h1>Política de cookies</h1><p>La aplicación utiliza almacenamiento local del navegador para conservar el estado de sesión de la consola y preferencias de interfaz. No incorpora analítica publicitaria ni cookies de terceros en esta versión.</p><h2>Control</h2><p>Al cerrar sesión se elimina el estado autenticado y los datos de visualización asociados. El usuario también puede limpiar el almacenamiento del sitio desde las opciones de su navegador.</p>"),
    "eula": ("Acuerdo de licencia de usuario final", "<h1>Acuerdo de licencia de usuario final (EULA)</h1><p>Para fines académicos se concede una licencia limitada, revocable y no transferible para usar la interfaz de demostración. No se autoriza interferir con los controles de acceso ni usar la plataforma para evaluar repositorios sin autorización.</p><h2>Propiedad intelectual</h2><p>Las reglas, evidencias y configuraciones asociadas a una organización deben utilizarse sólo dentro de su ámbito autorizado. Un acuerdo comercial definitivo debe especificar derechos de uso y soporte.</p>"),
    "contratacion": ("Condiciones de contratación y reembolsos", "<h1>Condiciones de contratación y reembolsos</h1><p>Esta versión académica no procesa pagos, suscripciones cobrables ni reembolsos. Las pantallas de planes y consumo son demostrativas y no constituyen una cotización.</p><h2>Antes de comercializar</h2><p>Se deberán publicar los precios vigentes, impuestos, medio de pago, renovación, cancelación, periodo de prueba, condiciones de reembolso y canal de soporte antes de aceptar una contratación.</p>"),
    "sla": ("Acuerdo de nivel de servicio", "<h1>Acuerdo de nivel de servicio (SLA)</h1><p>Los indicadores mostrados en la consola sirven como referencia técnica de la demostración. No representan un compromiso comercial de disponibilidad, respuesta o recuperación.</p><h2>Compromiso futuro</h2><p>Un SLA definitivo debe definir métricas medibles, horarios de soporte, exclusiones, ventanas de mantenimiento, procedimiento de incidentes, créditos de servicio y responsables de contacto.</p>"),
}


def public_page(path: str) -> str:
    if path == "/":
        return page("SecureCode — Confianza técnica", "Plataforma para convertir políticas de repositorio en evidencia técnica verificable.", HOME, path)
    if path == "/nosotros":
        return page("Nosotros", "Acerca de SecureCode.", ABOUT, path)
    if path == "/contacto":
        return page("Contacto", "Canales de contacto de SecureCode.", CONTACT, path)
    if path == "/preguntas-frecuentes":
        return page("Preguntas frecuentes", "Preguntas frecuentes sobre SecureCode.", FAQ, path)
    slug = path.rsplit("/", 1)[-1]
    title, body = LEGAL_CONTENT[slug]
    return page(title, title, '<section class="legal-page"><p class="eyebrow">DOCUMENTO INFORMATIVO</p>' + body + '<p class="legal-updated">Última actualización: ' + SITE_UPDATED_AT + "</p></section>", path, legal=True)

# PUBLIC-001 — Sitio público y documentación informativa

## Objetivo

Separar la presencia pública de SecureCode de la consola autenticada sin
duplicar la lógica de autorización ni presentar información comercial ficticia.

## Rutas

| Área | Ruta |
| --- | --- |
| Página de inicio | / |
| Consola autenticada | /app |
| Nosotros | /nosotros |
| Contacto | /contacto |
| Preguntas frecuentes | /preguntas-frecuentes |
| Documentos informativos | /legal/* |

## Decisiones de mantenibilidad

- Las páginas públicas usan un único generador en securecode.api.public_site;
  el encabezado, pie y aviso legal no se duplican entre rutas.
- La consola conserva sus archivos, estilos y JavaScript existentes bajo
  /app, por lo que las funciones autenticadas no dependen del sitio público.
- La hoja pública incluye un punto de quiebre de 760 px para navegación,
  cuadrículas, tarjetas y pie de página.
- Los documentos legales se muestran como borradores académicos. Ninguna
  dirección, correo, precio, reembolso o compromiso comercial se inventa.
- El registro enlaza las condiciones del servicio y el alcance técnico vigentes
  antes de crear la cuenta; la aceptación es explícita y no premarcada.

## Criterios verificables

1. Todas las rutas públicas responden HTML y contienen viewport.
2. /app conserva el shell de la consola.
3. Cada documento legal contiene el aviso de revisión jurídica pendiente.
4. La hoja pública contiene reglas responsivas para pantallas pequeñas.
5. El formulario de registro muestra enlaces a los documentos vigentes y una
   casilla de aceptación sin marcar.

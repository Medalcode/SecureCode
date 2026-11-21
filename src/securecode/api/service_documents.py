import hashlib
import json
from dataclasses import dataclass

from securecode.api.public_site import (
    LEGAL_CONTENT,
    LEGAL_NOTICE,
    SCOPE_PAGE,
    SITE_UPDATED_AT,
)
from securecode.api.service_document_manifest import load_document_manifest

PACKAGE_ID = "SECURECODE-ONBOARDING"
PACKAGE_VERSION = "2026-11-20.1"
ACCEPTANCE_TYPE = "organization_registration"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ServiceDocument:
    document_id: str
    version: str
    title: str
    path: str
    content: str

    @property
    def sha256(self) -> str:
        return _sha256(self.content)

    def as_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "version": self.version,
            "title": self.title,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class OnboardingPackage:
    package_id: str
    version: str
    documents: tuple[ServiceDocument, ...]

    @property
    def sha256(self) -> str:
        payload = {
            "package_id": self.package_id,
            "version": self.version,
            "documents": [
                {
                    "document_id": document.document_id,
                    "version": document.version,
                    "path": document.path,
                    "sha256": document.sha256,
                }
                for document in self.documents
            ],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return _sha256(canonical)

    def as_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "version": self.version,
            "sha256": self.sha256,
            "documents": [document.as_dict() for document in self.documents],
        }


def _legal_document(slug: str, document_id: str, title: str, path: str) -> ServiceDocument:
    legal_title, body = LEGAL_CONTENT[slug]
    content = "\n".join((legal_title, LEGAL_NOTICE, body, f"Última actualización: {SITE_UPDATED_AT}"))
    return ServiceDocument(
        document_id=document_id,
        version=PACKAGE_VERSION,
        title=title,
        path=path,
        content=content,
    )


def current_onboarding_package() -> OnboardingPackage:
    terms = _legal_document("terminos", "SERVICE_TERMS", "Términos de servicio", "/legal/terminos")
    scope = ServiceDocument(
        document_id="TECHNICAL_SCOPE",
        version=PACKAGE_VERSION,
        title="Alcance técnico y exclusiones",
        path="/alcance",
        content=f"Alcance y exclusiones\n{SITE_UPDATED_AT}\n{SCOPE_PAGE}",
    )
    package = OnboardingPackage(
        package_id=PACKAGE_ID,
        version=PACKAGE_VERSION,
        documents=(terms, scope),
    )
    manifest = load_document_manifest()
    expected = {key: manifest[key] for key in ("package_id", "version", "sha256", "documents")}
    if package.as_dict() != expected:
        raise RuntimeError("Generated service document package does not match the trusted manifest")
    return package

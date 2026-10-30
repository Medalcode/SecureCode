from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GH001EvaluationRequest(BaseModel):
    owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repository: str = Field(..., min_length=1, description="GitHub repository name")
    branch: str = Field(..., min_length=1, description="Branch to evaluate")

class SourceResponse(BaseModel):
    type: str
    repository: str
    branch: str

class RuleResponse(BaseModel):
    id: str
    version: int

class EvidenceResponse(BaseModel):
    required_review_approvals: Optional[int]
    dismiss_stale_reviews: Optional[bool]
    hash: str

class EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: Optional[RuleResponse]
    status: str
    source: SourceResponse
    evidence: EvidenceResponse
    collected_at: str
    evaluated_at: str

class GH002EvaluationRequest(BaseModel):
    owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repository: str = Field(..., min_length=1, description="GitHub repository name")

class GH002EvidenceResponse(BaseModel):
    default_branch: str
    protection_enabled: Optional[bool]
    hash: str

class GH002EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: Optional[RuleResponse]
    status: str
    source: SourceResponse
    evidence: GH002EvidenceResponse
    collected_at: str
    evaluated_at: str

class EvaluationHistoryItem(BaseModel):
    evaluation_id: str
    date_utc: str
    control: str
    repository_and_branch: str
    verdict: str
    hash_sha256: str
    raw_id: str
    repository: str
    branch: str
    evaluated_at: str

class EvaluationHistoryResponse(BaseModel):
    total: int
    items: List[EvaluationHistoryItem]
    pagination_info: str

# ===== Billing & Control Center Schemas (Fase 2) =====

class BillingModality(BaseModel):
    title: str
    description: str
    company_rut: str

class CorporateAssistance(BaseModel):
    title: str
    description: str
    action: str

class SubscriptionPlan(BaseModel):
    status: str
    plan_name: str
    badge: str
    description: str
    price: str
    next_billing_date: str
    billing_modality: BillingModality
    corporate_assistance: CorporateAssistance

class StorageUsage(BaseModel):
    title: str
    used: str
    retention_policy: str
    percentage: str

class MonthlyUsage(BaseModel):
    title: str
    cycle: str
    description: str
    consumed: int
    max: int
    usage_percentage: str
    available_evaluations: int
    storage: StorageUsage

class BillingInvoiceRow(BaseModel):
    date: str
    concept: str
    reference: str
    amount: str
    status: str
    invoice_action: str

class BillingHistory(BaseModel):
    title: str
    subtitle: str
    columns: List[str]
    rows: List[BillingInvoiceRow]
    footer_note: str
    link: str

class BillingFooter(BaseModel):
    platform: str
    sla: str
    security: str
    audit_id: str

class BillingSummaryResponse(BaseModel):
    app: str
    navigation: str
    title: str
    subtitle: str
    environment: str
    subscription_plan: SubscriptionPlan
    monthly_usage: MonthlyUsage
    billing_history: BillingHistory
    footer: BillingFooter

# ===== Report Export & Dispatch Schemas (Fase 2) =====

class ExportReportRequest(BaseModel):
    evaluation_id: Optional[str] = None
    evaluated_control: str = Field(..., description="e.g. GH-001 Revisión por pares")
    repository: str = Field(..., description="e.g. acme-corp/payment-gateway (main)")
    verdict: str = Field(..., description="e.g. PASS (CONFORME)")
    integrity_hash: str = Field(..., description="Canonical SHA-256 evidence hash")
    generate_pdf: bool = True
    email: str = Field("auditor@empresa.com", description="Auditor destination email")

class ExportReportResponse(BaseModel):
    success: bool
    title: str
    message: str
    dispatch_id: str
    timestamp_utc: str
    recipient: str
    pdf_generated: bool
    integrity_signature: str
    delivery_mode: str = "sandbox"
    delivery_note: Optional[str] = None

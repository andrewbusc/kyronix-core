from dataclasses import dataclass
from typing import Callable

from app.schemas.paystub_generate import PaystubGenerateRequest
from app.utils.paystub_adp_classic import render_paystub_adp_classic_pdf
from app.utils.paystub_v1 import render_paystub_v1_pdf


@dataclass(frozen=True)
class PaystubTemplateDefinition:
    id: str
    name: str
    description: str
    sections: tuple[str, ...]
    render_pdf: Callable[[PaystubGenerateRequest], bytes]


DEFAULT_PAYSTUB_TEMPLATE_ID = "kyronix_v1"

PAYSTUB_TEMPLATES = (
    PaystubTemplateDefinition(
        id="kyronix_v1",
        name="Kyronix Standard",
        description="Current Kyronix paystub layout with leave balances.",
        sections=(
            "employee",
            "pay_rules",
            "deductions",
            "payment_company",
            "leave_balances",
        ),
        render_pdf=render_paystub_v1_pdf,
    ),
    PaystubTemplateDefinition(
        id="adp_classic_v1",
        name="ADP Classic-Style",
        description="Template based on the uploaded Oct 31 paystub format.",
        sections=(
            "employee",
            "pay_rules",
            "deductions",
            "payment_company",
            "tax_profile",
            "other_benefits",
            "deposits",
        ),
        render_pdf=render_paystub_adp_classic_pdf,
    ),
)


def list_paystub_templates() -> list[PaystubTemplateDefinition]:
    return list(PAYSTUB_TEMPLATES)


def get_paystub_template(template_id: str | None) -> PaystubTemplateDefinition | None:
    requested_id = template_id or DEFAULT_PAYSTUB_TEMPLATE_ID
    for template in PAYSTUB_TEMPLATES:
        if template.id == requested_id:
            return template
    return None

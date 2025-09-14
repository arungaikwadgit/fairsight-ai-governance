# workflow.py
from typing import Dict, Any

WORKFLOW_GATES = [
    {
        "name": "Gate 1 — Intake & Purpose",
        "required_artifacts": ["Problem Statement", "Intended Use", "Stakeholder Map"],
        "ethics": "Clarity of purpose, legitimate use, stakeholder alignment"
    },
    {
        "name": "Gate 2 — Data & Privacy",
        "required_artifacts": ["Data Sources", "Consent Evidence", "Privacy Impact Assessment"],
        "ethics": "Lawful basis, minimization, de-identification"
    },
    {
        "name": "Gate 3 — Model & Fairness",
        "required_artifacts": ["Model Card", "Bias Evaluation Report", "Performance Metrics"],
        "ethics": "Fairness, robustness, explainability"
    },
    {
        "name": "Gate 4 — Deployment & Monitoring",
        "required_artifacts": ["Risk Register", "Human-in-the-loop Plan", "Monitoring KPIs"],
        "ethics": "Accountability, safety, continuous oversight"
    },
]

def gate_requirements_text(gate: Dict[str, Any]) -> str:
    items = "".join([f"- {a}\n" for a in gate["required_artifacts"]])
    return f"""**Requirements:**  
Ethical focus: _{gate['ethics']}_  
Artifacts to submit before advancing:
{items}"""

def can_advance_gate(project: Dict[str, Any], db, approved: bool) -> bool:
    gate_idx = project.get("current_gate_index", 0)
    current_gate = WORKFLOW_GATES[gate_idx]
    artifacts = db.get_project_artifacts(project["id"], gate_idx)
    have = set([a["name"] for a in artifacts])
    needed = set(current_gate["required_artifacts"])
    return approved and needed.issubset(have)

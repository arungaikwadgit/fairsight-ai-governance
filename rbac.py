# rbac.py
def is_caio(role: str) -> bool:
    return role == "ChiefAIOfficer"

def is_reviewer_for(checkpoint: dict, role: str) -> bool:
    req = (checkpoint.get("reviewed_by_role","") or "").strip()
    return role == req or is_caio(role)

def is_submitter_for(checkpoint: dict, role: str) -> bool:
    req = (checkpoint.get("submitted_by_role","") or "").strip()
    return role == req or is_caio(role)

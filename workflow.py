# workflow.py
DECISIONS = ["Approve", "Reject", "ReScope", "Pending"]

def compute_gate_status(checkpoint_decisions):
    if any(d == "Reject" for d in checkpoint_decisions):
        return "Reject"
    if checkpoint_decisions and all(d == "Approve" for d in checkpoint_decisions):
        return "Approve"
    if any(d == "ReScope" for d in checkpoint_decisions):
        return "ReScope"
    return "Pending"

def next_gate_enabled(prev_gate_status: str) -> bool:
    return prev_gate_status == "Approve"

# config_loader.py
import json, os

_CONFIG = {}

def load_config(path: str):
    global _CONFIG
    if not os.path.exists(path):
        _CONFIG = {"roles": [], "decision_rules": {}, "gates": []}
        return _CONFIG
    with open(path, "r", encoding="utf-8") as f:
        _CONFIG = json.load(f)
    return _CONFIG

def get_roles():
    return _CONFIG.get("roles", [])

def get_gates():
    return _CONFIG.get("gates", [])

def get_gate_by_id(gate_id: str, gates=None):
    gates = gates or get_gates()
    for g in gates:
        if g["gate_id"] == gate_id:
            return g
    return gates[0] if gates else None

def get_decision_rules():
    return _CONFIG.get("decision_rules", {})

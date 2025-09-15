# db.py
import json, time, os, base64
from pathlib import Path
from typing import Dict, Any, List

DB_PATH = Path("local_db.json")

DEFAULT_SETTINGS = {
    "openapi_key_obf": "",
    "openapi_model": "gpt-4o-mini"
}

class DB:
    def __init__(self):
        if not DB_PATH.exists():
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump({"projects": [], "settings": DEFAULT_SETTINGS}, f)

    def _load(self) -> Dict[str, Any]:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ---- Settings ----
    def get_settings(self) -> Dict[str, Any]:
        return self._load().get("settings", DEFAULT_SETTINGS)

    def save_openapi_key(self, raw_key: str, model: str | None = None):
        data = self._load()
        obf = base64.b64encode(raw_key.encode("utf-8")).decode("utf-8") if raw_key else ""
        data["settings"]["openapi_key_obf"] = obf
        if model:
            data["settings"]["openapi_model"] = model
        self._save(data)

    def clear_openapi_key(self):
        data = self._load()
        data["settings"]["openapi_key_obf"] = ""
        self._save(data)

    def get_openapi_key(self) -> str:
        obf = self.get_settings().get("openapi_key_obf","")
        if not obf:
            return ""
        try:
            return base64.b64decode(obf.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    # ---- Projects ----
    def create_project(self, proj: Dict[str, Any]) -> str:
        data = self._load()
        pid = f"p_{int(time.time()*1000)}"
        proj["id"] = pid
        proj["gates"] = {}
        data["projects"].append(proj)
        self._save(data)
        return pid

    def list_projects(self) -> List[Dict[str, Any]]:
        return self._load().get("projects", [])

    def get_project(self, pid: str) -> Dict[str, Any] | None:
        for p in self._load().get("projects", []):
            if p["id"] == pid:
                return p
        return None

    def update_project(self, pid: str, patch: Dict[str, Any]):
        data = self._load()
        for i,p in enumerate(data["projects"]):
            if p["id"] == pid:
                p.update(patch)
                p["updated_at"] = time.time()
                data["projects"][i] = p
                self._save(data)
                return

    def save_checkpoint_decision(self, pid: str, gate_id: str, artifact_key: str, decision: str, user: str):
        data = self._load()
        for i,p in enumerate(data["projects"]):
            if p["id"] == pid:
                gates = p.setdefault("gates", {})
                gate = gates.setdefault(gate_id, {"checkpoints": {}, "gate_status": "Pending", "audit": []})
                cp = gate["checkpoints"].setdefault(artifact_key, {})
                cp["decision"] = decision
                cp["decided_by"] = user
                cp["decided_at"] = time.time()
                gate["audit"].append({"ts": time.time(), "who": user, "action": f"checkpoint:{artifact_key}:{decision}"})
                data["projects"][i] = p
                self._save(data)
                return

    def save_checkpoint_payload(self, pid: str, gate_id: str, artifact_key: str, payload: dict, user: str):
        data = self._load()
        for i,p in enumerate(data["projects"]):
            if p["id"] == pid:
                gates = p.setdefault("gates", {})
                # Save for the current gate
                gate = gates.setdefault(gate_id, {"checkpoints": {}, "gate_status": "Pending", "audit": []})
                cp = gate["checkpoints"].setdefault(artifact_key, {})
                cp["payload"] = payload
                cp["updated_by"] = user
                cp["updated_at"] = time.time()
                gate["audit"].append({"ts": time.time(), "who": user, "action": f"artifact:{artifact_key}:update"})
                # PROPAGATE_SIMILAR_ARTIFACTS: copy same payload to other gates with same artifact_key
                for other_gid, other_gate in gates.items():
                    if other_gid == gate_id:
                        continue
                    ocp = other_gate.setdefault("checkpoints", {}).setdefault(artifact_key, {})
                    ocp["payload"] = payload
                    ocp["updated_by"] = user
                    ocp["updated_at"] = time.time()
                data["projects"][i] = p
                self._save(data)
                return

    def save_gate_status(self, pid: str, gate_id: str, status: str, user: str, reason: str = ""):
        data = self._load()
        for i, p in enumerate(data["projects"]):
            if p["id"] == pid:
                gates = p.setdefault("gates", {})
                gate = gates.setdefault(gate_id, {"checkpoints": {}, "gate_status": "Pending", "audit": []})
                gate["gate_status"] = status
                gate["overridden"] = True                 # ← mark as CAIO override
                gate["override_by"] = user
                gate["override_reason"] = reason
                gate["audit"].append({
                    "ts": time.time(),
                    "who": user,
                    "action": f"gate_status:{status}",
                    "reason": reason
                })
                data["projects"][i] = p
                self._save(data)
                return



    def get_artifact_payload(self, pid: str, artifact_key: str):
        data = self._load()
        for p in data.get("projects", []):
            if p["id"] == pid:
                gates = p.get("gates", {})
                # Prefer payload from any gate that has it
                for gid, gs in gates.items():
                    cp = gs.get("checkpoints", {}).get(artifact_key, {})
                    if "payload" in cp:
                        return cp.get("payload")
        return None

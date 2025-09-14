# firestore_db.py
import os, time, json
from pathlib import Path
from typing import Dict, Any, List

# This DB class uses a simple JSON file for persistence to keep the prototype self-contained.
# If Firebase is configured (service account path in env FIREBASE_CREDENTIALS), you can
# replace these methods with firebase_admin Firestore calls.

DB_PATH = Path("local_db.json")

class DB:
    def __init__(self):
        if not DB_PATH.exists():
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump({"projects": []}, f)

    def _load(self) -> Dict[str, Any]:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def create_project(self, proj: Dict[str, Any]) -> str:
        data = self._load()
        pid = f"p_{int(time.time()*1000)}"
        proj["id"] = pid
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
        for i, p in enumerate(data["projects"]):
            if p["id"] == pid:
                p.update(patch)
                p["updated_at"] = time.time()
                data["projects"][i] = p
                self._save(data)
                return

    def add_artifacts(self, pid: str, gate_idx: int, paths: List[str]):
        data = self._load()
        for i, p in enumerate(data["projects"]):
            if p["id"] == pid:
                artifacts = p.get("artifacts", {})
                gate_key = str(gate_idx)
                artifacts.setdefault(gate_key, [])
                for path in paths:
                    artifacts[gate_key].append({"name": path.split('/')[-1], "path": path})
                p["artifacts"] = artifacts
                p["updated_at"] = time.time()
                data["projects"][i] = p
                self._save(data)
                return

    def get_project_artifacts(self, pid: str, gate_idx: int):
        p = self.get_project(pid)
        if not p:
            return []
        return p.get("artifacts", {}).get(str(gate_idx), [])

    def advance_gate(self, pid: str):
        p = self.get_project(pid)
        if not p:
            return
        p["current_gate_index"] = min(p.get("current_gate_index", 0)+1, 3)
        p["updated_at"] = time.time()
        self.update_project(pid, p)

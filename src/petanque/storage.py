from __future__ import annotations
import json
from pathlib import Path
from typing import List

from .models import Team
from .tournament import Tournament


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_tournament(path: Path | str, tournament: Tournament) -> None:
    path = Path(path)
    _write_json(path, tournament.to_dict())


def load_tournament(path: Path | str) -> Tournament:
    path = Path(path)
    data = _read_json(path)
    return Tournament.from_dict(data)


def save_team_templates(path: Path | str, teams: List[Team]) -> None:
    path = Path(path)
    _write_json(path, {"teams": [team.to_dict() for team in teams]})


def load_team_templates(path: Path | str) -> List[Team]:
    path = Path(path)
    data = _read_json(path)
    return [Team.from_dict(item) for item in data.get("teams", [])]

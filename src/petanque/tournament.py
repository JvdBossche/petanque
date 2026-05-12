from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import Team, Round, Game, TournamentSettings


class PairingError(RuntimeError):
    pass


@dataclass
class TeamRanking:
    team: Team
    wins: int
    total_score_difference: int
    best_score_difference: int


@dataclass
class Tournament:
    name: str
    teams: List[Team] = field(default_factory=list)
    settings: TournamentSettings = field(default_factory=TournamentSettings)
    rounds: List[Round] = field(default_factory=list)

    def add_team(self, team: Team) -> None:
        if any(existing.number == team.number for existing in self.teams):
            raise ValueError(f"A team with number {team.number} already exists")
        self.teams.append(team)

    def remove_team(self, team_number: int) -> None:
        self.teams = [team for team in self.teams if team.number != team_number]

    def has_odd_team_count(self) -> bool:
        return len(self.teams) % 2 != 0

    def get_team(self, number: int) -> Optional[Team]:
        return next((team for team in self.teams if team.number == number), None)

    def _previous_opponents(self, team_number: int) -> set[int]:
        opponents = set()
        for round_item in self.rounds:
            if round_item.stage != "round":
                continue
            for game in round_item.games:
                if game.team1_number == team_number:
                    opponents.add(game.team2_number)
                elif game.team2_number == team_number:
                    opponents.add(game.team1_number)
        return opponents

    def _has_played_before(self, team1: int, team2: int) -> bool:
        return team2 in self._previous_opponents(team1)

    def _build_random_pairing(self, candidates: List[int], stage: str) -> List[Tuple[int, int]]:
        if len(candidates) % 2 != 0:
            raise PairingError("Cannot create pairings with an odd number of teams")

        for attempt in range(1000):
            random.shuffle(candidates)
            pairings: List[Tuple[int, int]] = []
            valid = True
            for i in range(0, len(candidates), 2):
                a, b = candidates[i], candidates[i + 1]
                if stage == "round" and self._has_played_before(a, b):
                    valid = False
                    break
                pairings.append((a, b))
            if valid:
                return pairings
        raise PairingError("Could not find a valid pairing without repeating opponents")

    def create_round(self, round_number: int, stage: str = "round") -> Round:
        if self.has_odd_team_count():
            raise PairingError("Cannot create a new round when an odd number of teams is present")
        team_numbers = [team.number for team in self.teams]
        pairings = self._build_random_pairing(team_numbers, stage)
        return Round(number=round_number, stage=stage, games=[Game(team1_number=a, team2_number=b, stage=stage) for a, b in pairings])

    def record_score(self, round_number: int, team1_number: int, team2_number: int, score1: int, score2: int) -> None:
        round_item = next((item for item in self.rounds if item.number == round_number), None)
        if round_item is None:
            raise ValueError(f"Round {round_number} not found")
        game = next((game for game in round_item.games if {game.team1_number, game.team2_number} == {team1_number, team2_number}), None)
        if game is None:
            raise ValueError("Game not found in round")
        game.score1 = score1
        game.score2 = score2

    def add_round(self, round_item: Round) -> None:
        self.rounds.append(round_item)

    def get_rounds_by_stage(self, stage: str) -> List[Round]:
        return [round_item for round_item in self.rounds if round_item.stage == stage]

    def calculate_rankings(self) -> List[TeamRanking]:
        stats: Dict[int, Dict[str, int]] = {}
        for team in self.teams:
            stats[team.number] = {"wins": 0, "total": 0, "best": -999}

        for round_item in self.get_rounds_by_stage("round"):
            for game in round_item.games:
                score1, score2 = game.score1, game.score2
                diff1 = score1 - score2
                diff2 = score2 - score1
                if score1 > score2:
                    stats[game.team1_number]["wins"] += 1
                elif score2 > score1:
                    stats[game.team2_number]["wins"] += 1
                stats[game.team1_number]["total"] += diff1
                stats[game.team2_number]["total"] += diff2
                stats[game.team1_number]["best"] = max(stats[game.team1_number]["best"], diff1)
                stats[game.team2_number]["best"] = max(stats[game.team2_number]["best"], diff2)

        #rankings = [
        #    TeamRanking(
        #        team=self.get_team(number),
        #        wins=data["wins"],
        #        total_score_difference=data["total"],
        #        best_score_difference=data["best"],
        #    )
        #    for number, data in stats.items()
        #]
        rankings = []
        for number, data in stats.items():
            team=self.get_team(number)
            assert team is not None
            rankings.append(
                TeamRanking(
                    team=team,
                    wins=data["wins"],
                    total_score_difference=data["total"],
                    best_score_difference=data["best"],
                )
            )
        rankings.sort(
            key=lambda item: (
                -item.wins,
                -item.total_score_difference,
                -item.best_score_difference,
                item.team.number,
            )
        )
        return rankings

    def top_four(self) -> List[Team]:
        return [ranking.team for ranking in self.calculate_rankings()[:4]]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "settings": self.settings.to_dict(),
            "teams": [team.to_dict() for team in self.teams],
            "rounds": [round_item.to_dict() for round_item in self.rounds],
        }

    @staticmethod
    def from_dict(data: Dict) -> "Tournament":
        teams = [Team.from_dict(item) for item in data.get("teams", [])]
        settings = TournamentSettings.from_dict(data.get("settings", {}))
        rounds = [Round.from_dict(item) for item in data.get("rounds", [])]
        return Tournament(name=data["name"], teams=teams, settings=settings, rounds=rounds)

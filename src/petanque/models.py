from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass(frozen=True)
class Player:
    name: str

    def __post_init__(self):
        name = self.name.strip()
        if not name:
            raise ValueError("Player name must not be empty")
        object.__setattr__(self, "name", name)

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name}

    @staticmethod
    def from_dict(data: Dict[str, str]) -> "Player":
        return Player(name=data["name"])


@dataclass
class Team:
    name: str
    number: int
    players: List[Player] = field(default_factory=list)

    def __post_init__(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Team name must not be empty")
        if self.number <= 0:
            raise ValueError("Team number must be a positive integer")
        if len(self.players) < 2 or len(self.players) > 3:
            raise ValueError("Team must have between 2 and 3 players")
        for player in self.players:
            if not isinstance(player, Player):
                raise TypeError("Team players must be Player instances")

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "number": self.number,
            "players": [player.to_dict() for player in self.players],
        }

    @staticmethod
    def from_dict(data: Dict) -> "Team":
        players = [Player.from_dict(item) for item in data["players"]]
        return Team(name=data["name"], number=int(data["number"]), players=players)


@dataclass
class Game:
    team1_number: int
    team2_number: int
    score1: int = 0
    score2: int = 0
    stage: str = "round"

    def winner_number(self) -> Optional[int]:
        if self.score1 == self.score2:
            return None
        return self.team1_number if self.score1 > self.score2 else self.team2_number

    def score_result(self, team_number: int) -> int:
        if team_number == self.team1_number:
            return self.score1 - self.score2
        if team_number == self.team2_number:
            return self.score2 - self.score1
        raise ValueError("Team number does not participate in this game")

    def to_dict(self) -> Dict:
        return {
            "team1_number": self.team1_number,
            "team2_number": self.team2_number,
            "score1": self.score1,
            "score2": self.score2,
            "stage": self.stage,
        }

    @staticmethod
    def from_dict(data: Dict) -> "Game":
        return Game(
            team1_number=int(data["team1_number"]),
            team2_number=int(data["team2_number"]),
            score1=int(data.get("score1", 0)),
            score2=int(data.get("score2", 0)),
            stage=data.get("stage", "round"),
        )


@dataclass
class Round:
    number: int
    games: List[Game] = field(default_factory=list)
    stage: str = "round"

    def to_dict(self) -> Dict:
        return {
            "number": self.number,
            "stage": self.stage,
            "games": [game.to_dict() for game in self.games],
        }

    @staticmethod
    def from_dict(data: Dict) -> "Round":
        games = [Game.from_dict(item) for item in data.get("games", [])]
        return Round(number=int(data["number"]), stage=data.get("stage", "round"), games=games)


@dataclass
class TournamentSettings:
    rounds: int = 3
    max_points_round: int = 13
    max_points_final: int = 15

    def to_dict(self) -> Dict:
        return {
            "rounds": self.rounds,
            "max_points_round": self.max_points_round,
            "max_points_final": self.max_points_final,
        }

    @staticmethod
    def from_dict(data: Dict) -> "TournamentSettings":
        return TournamentSettings(
            rounds=int(data.get("rounds", 3)),
            max_points_round=int(data.get("max_points_round", 13)),
            max_points_final=int(data.get("max_points_final", 15)),
        )

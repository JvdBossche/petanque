from pathlib import Path

import pytest

from petanque.models import Player, Team
from petanque.tournament import Tournament, PairingError
from petanque.storage import load_tournament, load_team_templates, save_team_templates, save_tournament


def make_team(number: int) -> Team:
    return Team(name=f"Team {number}", number=number, players=[Player(name="Alice"), Player(name="Bob")])


def test_team_requires_two_to_three_players():
    with pytest.raises(ValueError):
        Team(name="Invalid", number=1, players=[Player(name="Only")])


def test_round_pairings_avoid_repeat_opponents():
    tournament = Tournament(name="Test")
    for i in range(1, 5):
        tournament.add_team(make_team(i))
    round1 = tournament.create_round(round_number=1)
    tournament.add_round(round1)
    for game in round1.games:
        tournament.record_score(round_number=1, team1_number=game.team1_number, team2_number=game.team2_number, score1=13, score2=10)
    round2 = tournament.create_round(round_number=2)
    for game in round2.games:
        assert not tournament._has_played_before(game.team1_number, game.team2_number)


def test_calculate_rankings_tie_breakers():
    tournament = Tournament(name="Ranking")
    for i in range(1, 5):
        tournament.add_team(make_team(i))
    round1 = tournament.create_round(round_number=1)
    tournament.add_round(round1)
    # Team 1 beats Team 2 by 13-10, Team 3 beats Team 4 by 13-12
    team1, team2 = round1.games[0].team1_number, round1.games[0].team2_number
    team3, team4 = round1.games[1].team1_number, round1.games[1].team2_number
    tournament.record_score(round_number=1, team1_number=team1, team2_number=team2, score1=13, score2=10)
    tournament.record_score(round_number=1, team1_number=team3, team2_number=team4, score1=13, score2=12)
    rankings = tournament.calculate_rankings()
    assert rankings[0].wins == 1
    assert rankings[0].total_score_difference >= rankings[1].total_score_difference


def test_odd_number_of_teams_raises_pairing_error():
    tournament = Tournament(name="Odd")
    tournament.add_team(make_team(1))
    tournament.add_team(make_team(2))
    tournament.add_team(make_team(3))
    with pytest.raises(PairingError):
        tournament.create_round(round_number=1)


def test_tournament_serialization_round_trip(tmp_path: Path):
    tournament = Tournament(name="SaveLoad")
    tournament.add_team(make_team(1))
    tournament.add_team(make_team(2))
    round1 = tournament.create_round(round_number=1)
    tournament.add_round(round1)
    path = tmp_path / "save.json"
    save_tournament(path, tournament)
    loaded = load_tournament(path)
    assert loaded.name == tournament.name
    assert len(loaded.teams) == len(tournament.teams)
    assert loaded.settings.rounds == tournament.settings.rounds


def test_save_load_team_templates(tmp_path: Path):
    teams = [make_team(1), make_team(2)]
    path = tmp_path / "templates.json"
    save_team_templates(path, teams)
    loaded = load_team_templates(path)
    assert len(loaded) == 2
    assert loaded[0].name == teams[0].name
    assert loaded[1].players[1].name == teams[1].players[1].name

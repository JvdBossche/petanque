from __future__ import annotations
import random
import re
from platformdirs import user_data_dir
from pathlib import Path

import flet as ft

from .models import Game, Player, Round, Team, TournamentSettings
from .storage import load_tournament, save_tournament, save_team_templates, load_team_templates
from .tournament import PairingError, Tournament


APP_NAME = "PetanqueTournamentManager"
APP_AUTHOR = "JvdBossche"
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_FILE = DATA_DIR / "team_templates.json"


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return sanitized or "tournament"


class PetanqueApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.tournament: Tournament | None = None
        self.save_path: Path | None = None
        self.current_round_fields: list[tuple[ft.TextField, ft.TextField, int, int]] = []
        self.open_file_picker = ft.FilePicker(on_upload=self.on_open_file_result)
        self.page.overlay.append(self.open_file_picker)

        self.page.title = "Petanque Tournament Manager"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.START
        setattr(self.page, "window_width", 1000)
        setattr(self.page, "window_height", 800)

        self.show_start_view()

    def clear_controls(self) -> None:
        self.page.controls.clear()

    def close_dialog(self) -> None:
        dialog = getattr(self.page, "dialog", None)
        if dialog:
            dialog.open = False
            self.page.update()

    def show_start_view(self, message: str | None = None) -> None:
        self.clear_controls()
        header = ft.Text("Petanque Tournament Manager", theme_style=ft.TextThemeStyle.HEADLINE_LARGE)
        subtitle = ft.Text(
            "Create tournaments, add teams, record scores, and continue later.",
            theme_style=ft.TextThemeStyle.BODY_LARGE,
        )
        controls: list[ft.Control] = [header, subtitle, ft.ElevatedButton("Create new tournament", on_click=self.show_new_tournament_view)]
        controls.append(ft.ElevatedButton("Load existing tournament", on_click=self.open_load_dialog))
        if message:
            controls.append(ft.Text(message, color=ft.Colors.RED))
        self.page.add(ft.Column(controls, spacing=18, horizontal_alignment=ft.CrossAxisAlignment.START))
        self.page.update()

    def show_new_tournament_view(self, event: ft.Event[ft.Button] | None = None) -> None:
        self.clear_controls()
        self.name_field = ft.TextField(label="Tournament name", width=400)
        self.rounds_field = ft.TextField(label="Rounds", value="3", width=120, keyboard_type=ft.KeyboardType.NUMBER)
        self.max_round_points_field = ft.TextField(label="Points to win round", value="13", width=200, keyboard_type=ft.KeyboardType.NUMBER)
        self.max_final_points_field = ft.TextField(label="Points to win semi/final", value="15", width=200, keyboard_type=ft.KeyboardType.NUMBER)

        row_controls: list[ft.Control] = [self.name_field, self.rounds_field, self.max_round_points_field, self.max_final_points_field]
        button_controls: list[ft.Control] = [
            ft.ElevatedButton("Create tournament", on_click=self.create_tournament),
            ft.TextButton("Back", on_click=lambda _: self.show_start_view()),
        ]
        controls: list[ft.Control] = [
            ft.Text("New Tournament", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Row(row_controls, spacing=16),
            ft.Row(button_controls, spacing=12),
        ]
        self.page.add(ft.Column(controls, spacing=16))
        self.page.update()

    def create_tournament(self, event: ft.Event[ft.Button] | None = None) -> None:
        name = self.name_field.value.strip() if self.name_field.value else ""
        if not name:
            self.show_start_view("Tournament name is required.")
            return
        try:
            rounds = int(self.rounds_field.value)
            max_round = int(self.max_round_points_field.value)
            max_final = int(self.max_final_points_field.value)
            settings = TournamentSettings(rounds=rounds, max_points_round=max_round, max_points_final=max_final)
        except ValueError:
            self.show_start_view("Round counts and point settings must be integers.")
            return

        self.tournament = Tournament(name=name, settings=settings)
        self.save_path = DATA_DIR / f"{sanitize_filename(name)}.json"
        self.show_team_editor_view()

    def show_team_editor_view(self, message: str | None = None) -> None:
        if self.tournament is None:
            self.show_start_view("No tournament is loaded.")
            return

        self.clear_controls()
        header = ft.Text(f"Teams for {self.tournament.name}", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        warning = ft.Text("Odd number of teams: add or remove a team before creating the first round.", color=ft.Colors.ORANGE)
        self.team_detail = ft.Column([], spacing=8)
        self.update_team_list()

        action_controls: list[ft.Control] = [
            ft.ElevatedButton("Add team", on_click=self.open_add_team_dialog),
            ft.ElevatedButton("Save teams as templates", on_click=self.save_current_teams_as_templates),
            ft.ElevatedButton("Load from templates", on_click=self.show_team_templates_view),
            ft.ElevatedButton("Save tournament", on_click=self.save_current_tournament),
            ft.ElevatedButton("Begin rounds", on_click=self.start_rounds, disabled=self.tournament.has_odd_team_count() or len(self.tournament.teams) < 2),
            ft.TextButton("Back to start", on_click=lambda _: self.show_start_view()),
        ]
        action_row = ft.Row(action_controls, spacing=12, wrap=True)

        self.page.add(ft.Column([header, self.team_detail, warning if self.tournament.has_odd_team_count() else ft.Container(), action_row], spacing=16))
        if message:
            self.page.add(ft.Text(message, color=ft.Colors.RED))
        self.page.update()

    def update_team_list(self) -> None:
        if self.tournament is None:
            return
        self.team_detail.controls.clear()
        for team in sorted(self.tournament.teams, key=lambda team: team.number):
            team_row = ft.Row(
                [
                    ft.Text(f"#{team.number}: {team.name} ({', '.join(player.name for player in team.players)})", expand=True),
                    ft.IconButton(ft.icons.Icons.DELETE, tooltip="Remove team", on_click=lambda e, number=team.number: self.remove_team(number)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            self.team_detail.controls.append(team_row)
        self.page.update()

    def open_add_team_dialog(self, event: ft.Event[ft.Button]) -> None:
        self.team_name_field = ft.TextField(label="Team name", width=300)
        self.team_number_field = ft.TextField(label="Team number", width=120, value=str(len(self.tournament.teams) + 1 if self.tournament else 1), keyboard_type=ft.KeyboardType.NUMBER)
        self.player1_field = ft.TextField(label="Player 1", width=300)
        self.player2_field = ft.TextField(label="Player 2", width=300)
        self.player3_field = ft.TextField(label="Player 3 (optional)", width=300)

        self.add_team_dialog = ft.AlertDialog(
            title=ft.Text("Add Team"),
            content=ft.Column(
                [self.team_name_field, self.team_number_field, self.player1_field, self.player2_field, self.player3_field],
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog()),
                ft.ElevatedButton("Add team", on_click=self.add_team),
            ],
            on_dismiss=lambda _: None,
        )
        setattr(self.page, "dialog", self.add_team_dialog)
        self.add_team_dialog.open = True
        self.page.update()

    def add_team(self, event: ft.Event[ft.Button]) -> None:
        if self.tournament is None:
            return
        name = self.team_name_field.value.strip() if self.team_name_field.value else ""
        number_text = self.team_number_field.value or ""
        players = [field.value.strip() for field in [self.player1_field, self.player2_field, self.player3_field] if field.value and field.value.strip()]
        dialog = getattr(self.page, "dialog", None)
        if not name or not number_text or len(players) < 2:
            if dialog:
                dialog.open = False
            self.page.update()
            self.show_team_editor_view("Team name, number, and at least two players are required.")
            return

        try:
            team_number = int(number_text)
            team = Team(name=name, number=team_number, players=[Player(name=player) for player in players])
            self.tournament.add_team(team)
            if dialog:
                dialog.open = False
            self.update_team_list()
            self.show_team_editor_view()
        except ValueError as exc:
            if dialog:
                dialog.open = False
            self.page.update()
            self.show_team_editor_view(f"Invalid team entry: {exc}")
        except Exception as exc:
            if dialog:
                dialog.open = False
            self.page.update()
            self.show_team_editor_view(str(exc))

    def remove_team(self, team_number: int) -> None:
        if self.tournament is None:
            return
        self.tournament.remove_team(team_number)
        self.show_team_editor_view()

    def next_team_number(self) -> int:
        if self.tournament is None or not self.tournament.teams:
            return 1
        existing = {team.number for team in self.tournament.teams}
        number = 1
        while number in existing:
            number += 1
        return number

    def save_current_teams_as_templates(self, event: ft.Event[ft.Button]) -> None:
        if self.tournament is None:
            return
        if not self.tournament.teams:
            self.show_team_editor_view("No teams available to save as templates.")
            return
        save_team_templates(TEMPLATES_FILE, self.tournament.teams)
        self.show_team_editor_view("Current teams saved as reusable templates.")

    def show_team_templates_view(self, event: ft.Event[ft.Button] | None = None) -> None:
        self.clear_controls()
        header = ft.Text("Reusable Team Templates", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        try:
            templates = load_team_templates(TEMPLATES_FILE)
        except Exception:
            templates = []

        if templates:
            template_rows: list[ft.Control] = []
            for template in templates:
                template_rows.append(
                    ft.Row(
                        [
                            ft.Text(f"{template.name}: {', '.join(player.name for player in template.players)}", expand=True),
                            ft.ElevatedButton("Add to tournament", on_click=lambda e, team=template: self.add_template_team(team)),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
        else:
            template_rows = [ft.Text("No reusable templates found. Save one from the team editor first.")]

        action_row: ft.Row = ft.Row(
            [
                ft.TextButton("Back to teams", on_click=lambda _: self.show_team_editor_view()),
            ],
            spacing=12,
        )

        self.page.add(ft.Column([header, *template_rows, action_row], spacing=14))
        self.page.update()

    def add_template_team(self, template: Team) -> None:
        if self.tournament is None:
            return
        try:
            team_number = self.next_team_number()
            team = Team(
                name=template.name,
                number=team_number,
                players=[Player(name=player.name) for player in template.players],
            )
            self.tournament.add_team(team)
            self.show_team_editor_view(f"Imported template team {team.name} as number {team.number}.")
        except Exception as exc:
            self.show_team_editor_view(f"Failed to import template: {exc}")

    def start_rounds(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        try:
            next_round_number = len(self.tournament.get_rounds_by_stage("round")) + 1
            round_item = self.tournament.create_round(next_round_number)
            self.tournament.add_round(round_item)
            self.show_round_view(round_item)
        except PairingError as exc:
            self.show_team_editor_view(str(exc))

    def show_round_view(self, round_item: Round) -> None:
        if self.tournament is None:
            return
        self.clear_controls()
        self.current_round_fields.clear()

        header = ft.Text(f"Round {round_item.number} - Record scores", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        games_controls: list[ft.Control] = []

        for game in round_item.games:
            team1 = self.tournament.get_team(game.team1_number)
            team2 = self.tournament.get_team(game.team2_number)
            assert team1 is not None and team2 is not None
            score1_field = ft.TextField(label=f"{team1.name} score", value=str(game.score1), width=120, keyboard_type=ft.KeyboardType.NUMBER)
            score2_field = ft.TextField(label=f"{team2.name} score", value=str(game.score2), width=120, keyboard_type=ft.KeyboardType.NUMBER)
            self.current_round_fields.append((score1_field, score2_field, game.team1_number, game.team2_number))
            games_controls.append(
                ft.Row(
                    [
                        ft.Text(f"{team1.name} vs {team2.name}", expand=True),
                        score1_field,
                        ft.Text("-"),
                        score2_field,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        round_actions: list[ft.Control] = [
            ft.ElevatedButton("Save scores", on_click=self.save_round_scores),
            ft.ElevatedButton("Save tournament", on_click=self.save_current_tournament),
            ft.TextButton("Back to teams", on_click=lambda _: self.show_team_editor_view()),
        ]
        self.page.add(
            ft.Column(
                [
                    header,
                    *games_controls,
                    ft.Row(round_actions, spacing=12),
                ],
                spacing=16,
            )
        )
        self.page.update()

    def save_round_scores(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        error = None
        for score1_field, score2_field, team1, team2 in self.current_round_fields:
            try:
                score1 = int(score1_field.value or "0")
                score2 = int(score2_field.value or "0")
            except ValueError:
                error = "All scores must be integers."
                break
            if score1 == score2:
                error = "Games cannot end in a draw."
                break
            if max(score1, score2) < self.tournament.settings.max_points_round:
                error = f"Winners must reach {self.tournament.settings.max_points_round} points."
                break
            self.tournament.record_score(round_number=len(self.tournament.get_rounds_by_stage("round")), team1_number=team1, team2_number=team2, score1=score1, score2=score2)

        if error:
            self.show_round_view(self.tournament.rounds[-1])
            self.page.add(ft.Text(error, color=ft.Colors.RED))
            self.page.update()
            return
        self.save_current_tournament(None)
        if len(self.tournament.get_rounds_by_stage("round")) < self.tournament.settings.rounds:
            self.start_rounds(None)
        else:
            self.show_ranking_view()

    def show_ranking_view(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        self.clear_controls()

        header = ft.Text("Round Rankings", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        ranking_rows: list[ft.Control] = []
        rankings = self.tournament.calculate_rankings()
        for index, ranking in enumerate(rankings, start=1):
            ranking_rows.append(
                ft.Text(
                    f"{index}. {ranking.team.name} (#{ranking.team.number}) – Wins: {ranking.wins}, Score diff: {ranking.total_score_difference}, Best diff: {ranking.best_score_difference}",
                )
            )

        ranking_actions: list[ft.Control] = [
            ft.ElevatedButton("Start semifinals", on_click=self.start_semifinals, disabled=len(self.tournament.teams) < 4),
            ft.ElevatedButton("Save tournament", on_click=self.save_current_tournament),
            ft.TextButton("Back to teams", on_click=lambda _: self.show_team_editor_view()),
        ]
        action_row = ft.Row(ranking_actions, spacing=12)

        self.page.add(ft.Column([header, *ranking_rows, action_row], spacing=14))
        self.page.update()

    def start_semifinals(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        if self.tournament.get_rounds_by_stage("semi"):
            self.show_semifinal_view()
            return

        top4 = self.tournament.top_four()
        if len(top4) < 4:
            self.show_ranking_view()
            return

        random.shuffle(top4)
        semi_round = self.tournament.create_round(self.tournament.settings.rounds + 1, stage="semi")
        self.tournament.add_round(semi_round)
        self.show_semifinal_view()

    def show_semifinal_view(self) -> None:
        if self.tournament is None:
            return
        self.clear_controls()
        semifinals = self.tournament.get_rounds_by_stage("semi")
        if not semifinals:
            self.show_ranking_view()
            return

        round_item = semifinals[0]
        self.current_round_fields.clear()
        games_controls: list[ft.Control] = []
        for game in round_item.games:
            team1 = self.tournament.get_team(game.team1_number)
            team2 = self.tournament.get_team(game.team2_number)
            assert team1 is not None and team2 is not None
            score1_field = ft.TextField(label=f"{team1.name} score", value=str(game.score1), width=120, keyboard_type=ft.KeyboardType.NUMBER)
            score2_field = ft.TextField(label=f"{team2.name} score", value=str(game.score2), width=120, keyboard_type=ft.KeyboardType.NUMBER)
            self.current_round_fields.append((score1_field, score2_field, game.team1_number, game.team2_number))
            games_controls.append(ft.Row([ft.Text(f"{team1.name} vs {team2.name}", expand=True), score1_field, ft.Text("-"), score2_field], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        semifinal_actions: list[ft.Control] = [
            ft.ElevatedButton("Save semifinals", on_click=self.save_semifinal_scores),
            ft.ElevatedButton("Save tournament", on_click=self.save_current_tournament),
            ft.TextButton("Back to rankings", on_click=lambda _: self.show_ranking_view()),
        ]
        self.page.add(
            ft.Column(
                [
                    ft.Text("Semi-Finals", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    *games_controls,
                    ft.Row(semifinal_actions, spacing=12),
                ],
                spacing=16,
            )
        )
        self.page.update()

    def save_semifinal_scores(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        error = None
        semifinals = self.tournament.get_rounds_by_stage("semi")
        if not semifinals:
            return

        for score1_field, score2_field, team1, team2 in self.current_round_fields:
            try:
                score1 = int(score1_field.value or "0")
                score2 = int(score2_field.value or "0")
            except ValueError:
                error = "All scores must be integers."
                break
            if score1 == score2:
                error = "Games cannot end in a draw."
                break
            if max(score1, score2) < self.tournament.settings.max_points_final:
                error = f"Winners must reach {self.tournament.settings.max_points_final} points."
                break
            self.tournament.record_score(round_number=semifinals[0].number, team1_number=team1, team2_number=team2, score1=score1, score2=score2)

        if error:
            self.show_semifinal_view()
            self.page.add(ft.Text(error, color=ft.Colors.RED))
            self.page.update()
            return

        self.save_current_tournament(None)
        self.create_final_rounds()
        self.show_final_view()

    def create_final_rounds(self) -> None:
        if self.tournament is None:
            return
        semifinal_rounds = self.tournament.get_rounds_by_stage("semi")
        if not semifinal_rounds:
            return
        semi = semifinal_rounds[0]
        winners = []
        losers = []
        for game in semi.games:
            if game.score1 > game.score2:
                winners.append(game.team1_number)
                losers.append(game.team2_number)
            else:
                winners.append(game.team2_number)
                losers.append(game.team1_number)

        final_round = Round(number=self.tournament.settings.rounds + 2, stage="final", games=[
            Game(team1_number=winners[0], team2_number=winners[1], stage="final"),
            Game(team1_number=losers[0], team2_number=losers[1], stage="final"),
        ])
        self.tournament.add_round(final_round)

    def show_final_view(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        self.clear_controls()
        final_rounds = self.tournament.get_rounds_by_stage("final")
        if not final_rounds:
            self.show_semifinal_view()
            return

        round_item = final_rounds[0]
        self.current_round_fields.clear()
        games_controls: list[ft.Control] = []
        for game in round_item.games:
            team1 = self.tournament.get_team(game.team1_number)
            team2 = self.tournament.get_team(game.team2_number)
            assert team1 is not None and team2 is not None
            score1_field = ft.TextField(label=f"{team1.name} score", value=str(game.score1), width=120, keyboard_type=ft.KeyboardType.NUMBER)
            score2_field = ft.TextField(label=f"{team2.name} score", value=str(game.score2), width=120, keyboard_type=ft.KeyboardType.NUMBER)
            self.current_round_fields.append((score1_field, score2_field, game.team1_number, game.team2_number))
            games_controls.append(ft.Row([ft.Text(f"{team1.name} vs {team2.name}", expand=True), score1_field, ft.Text("-"), score2_field], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        final_actions: list[ft.Control] = [
            ft.ElevatedButton("Save finals", on_click=self.save_final_scores),
            ft.ElevatedButton("Save tournament", on_click=self.save_current_tournament),
            ft.TextButton("Back to semifinals", on_click=lambda _: self.show_semifinal_view()),
        ]
        self.page.add(
            ft.Column(
                [
                    ft.Text("Finals", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    *games_controls,
                    ft.Row(final_actions, spacing=12),
                ],
                spacing=16,
            )
        )
        self.page.update()

    def save_final_scores(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        error = None
        final_rounds = self.tournament.get_rounds_by_stage("final")
        if not final_rounds:
            return

        for score1_field, score2_field, team1, team2 in self.current_round_fields:
            try:
                score1 = int(score1_field.value or "0")
                score2 = int(score2_field.value or "0")
            except ValueError:
                error = "All scores must be integers."
                break
            if score1 == score2:
                error = "Games cannot end in a draw."
                break
            if max(score1, score2) < self.tournament.settings.max_points_final:
                error = f"Winners must reach {self.tournament.settings.max_points_final} points."
                break
            self.tournament.record_score(round_number=final_rounds[0].number, team1_number=team1, team2_number=team2, score1=score1, score2=score2)

        if error:
            self.show_final_view()
            self.page.add(ft.Text(error, color=ft.Colors.RED))
            self.page.update()
            return

        self.save_current_tournament(None)
        self.show_summary_view()

    def show_summary_view(self) -> None:
        if self.tournament is None:
            return
        self.clear_controls()
        final_rounds = self.tournament.get_rounds_by_stage("final")
        if not final_rounds:
            self.show_final_view()
            return

        header = ft.Text("Tournament Summary", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        winners: list[str] = []
        for game in final_rounds[0].games:
            team1 = self.tournament.get_team(game.team1_number)
            team2 = self.tournament.get_team(game.team2_number)
            assert team1 is not None and team2 is not None
            winner = team1.name if game.score1 > game.score2 else team2.name
            winners.append(f"{team1.name} vs {team2.name} -> Winner: {winner}")

        summary_actions: list[ft.Control] = [
            ft.ElevatedButton("Save tournament", on_click=self.save_current_tournament),
            ft.TextButton("Back to start", on_click=lambda _: self.show_start_view()),
        ]
        self.page.add(
            ft.Column(
                [
                    header,
                    *[ft.Text(line) for line in winners],
                    ft.Row(summary_actions, spacing=12),
                ],
                spacing=16,
            )
        )
        self.page.update()

    def save_current_tournament(self, event: ft.Event[ft.Button] | None = None) -> None:
        if self.tournament is None:
            return
        if self.save_path is None:
            self.save_path = DATA_DIR / f"{sanitize_filename(self.tournament.name)}.json"
        save_tournament(self.save_path, self.tournament)
        setattr(self.page, "snack_bar", ft.SnackBar(ft.Text(f"Tournament saved to {self.save_path}")))
        bar = getattr(self.page, "snack_bar", None)
        if bar:
            bar.open = True
        self.page.update()

    async def open_load_dialog(self, event: ft.Event[ft.Button]) -> None:
        await self.open_file_picker.pick_files()

    def on_open_file_result(self, event: ft.FilePickerUploadEvent) -> None:
        files = getattr(event, "files", [])
        if not files:
            return
        path = Path(files[0].path)
        try:
            self.tournament = load_tournament(path)
            self.save_path = path
            self.show_team_editor_view()
        except Exception as exc:
            self.show_start_view(f"Failed to load tournament: {exc}")


def main(page: ft.Page) -> None:
    PetanqueApp(page)


if __name__ == "__main__":
    ft.run(main)

import typing

from app.game.views import (
    FinishedGameListView, FinishedGameDeleteView
)

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/game.list_finished_games", FinishedGameListView)
    app.router.add_view("/game.delete_finished_game", FinishedGameDeleteView)

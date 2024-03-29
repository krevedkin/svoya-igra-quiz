from aiohttp.web_exceptions import HTTPNotFound
from aiohttp_apispec import (
    docs, request_schema, response_schema
)

from app.game.schemes import DeleteFinishedGameRequestSchema, \
    DeleteFinishedGameResponseSchema, FinishedGameListSchema
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class FinishedGameListView(AuthRequiredMixin, View):
    @docs(tags=["games"], summary="get finished games list")
    @response_schema(FinishedGameListSchema)
    async def get(self):
        finished_games = await self.request.app.store.game.get_finished_games()
        return json_response(
            FinishedGameListSchema().dump({"finished_games": finished_games}))


class FinishedGameDeleteView(AuthRequiredMixin, View):
    @docs(tags=["games"], summary="delete finished game")
    @request_schema(DeleteFinishedGameRequestSchema)
    @response_schema(DeleteFinishedGameResponseSchema)
    async def delete(self):
        game = await self.request.app.store.game.delete_finished_game_by_id(
            id_=self.data["id"]
        )
        if not game:
            raise HTTPNotFound(
                text=f"game with id {self.data['id']} "
                     f"doesn't exist or game is not finished."
                     f" Provide correct id"
            )
        return json_response(
            DeleteFinishedGameResponseSchema().dump(game))

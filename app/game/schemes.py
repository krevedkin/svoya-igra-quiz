from marshmallow import Schema, fields


class FinishedGameSchema(Schema):
    id = fields.Int()
    created_at = fields.DateTime()
    players_and_scores = fields.Dict()


class FinishedGameListSchema(Schema):
    finished_games = fields.Nested(FinishedGameSchema, many=True)


class DeleteFinishedGameRequestSchema(FinishedGameSchema):
    class Meta:
        fields = ('id',)


class DeleteFinishedGameResponseSchema(FinishedGameSchema):
    class Meta:
        exclude = ('players_and_scores',)

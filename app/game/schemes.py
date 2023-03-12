from marshmallow import Schema, fields


class DeleteFinishedGameRequestSchema(Schema):
    game_id = fields.Int(required=True)


class DeleteFinishedGameResponseSchema(DeleteFinishedGameRequestSchema):
    id = fields.Int()
    created_at = fields.DateTime()
    is_finished = fields.Bool()
    chat_id = fields.Integer()

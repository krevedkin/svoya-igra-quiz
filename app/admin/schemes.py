from marshmallow import Schema, fields


class AdminSchema(Schema):
    id = fields.Integer()
    email = fields.Str(required=True)


class AdminLoginRequestSchema(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True)


class AdminLoginResponseSchema(AdminSchema):
    ...


class AdminCurrentResponseSchema(AdminSchema):
    ...

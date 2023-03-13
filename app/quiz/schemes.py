from marshmallow import Schema, fields, validates, ValidationError


class ThemeSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)


class ThemeAddRequestSchema(ThemeSchema):
    class Meta:
        exclude = ("id",)


class ThemeListResponseSchema(Schema):
    themes = fields.Nested(ThemeSchema, many=True)


class ThemeDeleteRequestSchema(Schema):
    theme_id = fields.Int()


class QuestionSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)
    theme_id = fields.Int(required=True)
    answer = fields.Str(required=True)
    cost = fields.Int(required=True)

    @validates("answer")
    def validate_answer_is_one_word(self, answer):
        answer = answer.split()
        if len(answer) != 1:
            raise ValidationError(
                "Answer must be single word. "
                "Provide correct value."
            )

    @validates("cost")
    def validate_cost_in_range_of_costs(self, cost):
        if cost not in [100, 200, 300, 400, 500]:
            raise ValidationError(
                "Cost value must be one of 100,200,300,400,500. "
                "Provide correct value."
            )


class QuestionAddRequestSchema(QuestionSchema):
    class Meta:
        exclude = ("id",)


class QuestionListRequestSchema(ThemeDeleteRequestSchema):
    ...


class QuestionListResponseSchema(Schema):
    questions = fields.Nested(QuestionSchema, many=True)


class QuestionUpdateRequestSchema(QuestionSchema):
    id = fields.Int(required=True)


class QuestionDeleteRequestSchema(Schema):
    question_id = fields.Int()

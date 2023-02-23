from marshmallow import Schema, fields, validates, ValidationError
from marshmallow.validate import Length


class ThemeSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)


class QuestionSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)
    theme_id = fields.Int(required=True)
    answers = fields.Nested(
        "AnswerSchema", many=True, required=True, validate=Length(min=2)
    )

    @validates("answers")
    def validate_has_true_answer(self, answers):
        if not any([answer["is_correct"] for answer in answers]):
            raise ValidationError(
                "There is no correct answer. "
                "Provide is_correct field as true in one answer"
            )

    @validates("answers")
    def validate_has_only_one_correct_answer(self, answers):
        bool_fields = [answer["is_correct"] for answer in answers]
        true_answers = list(filter(lambda x: x is True, bool_fields))
        if len(true_answers) > 1:
            raise ValidationError(
                "There is more than one correct answer. "
                "Only one answer can be correct"
            )


class AnswerSchema(Schema):
    title = fields.Str(required=True)
    is_correct = fields.Bool(required=True)


class ThemeListSchema(Schema):
    themes = fields.Nested(ThemeSchema, many=True)


class ThemeIdSchema(Schema):
    theme_id = fields.Int()


class ListQuestionSchema(Schema):
    questions = fields.Nested(QuestionSchema, many=True)

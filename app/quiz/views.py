from aiohttp.web_exceptions import HTTPConflict, HTTPNotFound
from aiohttp_apispec import querystring_schema, request_schema, response_schema, docs

from app.quiz.models import Answer
from app.quiz.schemes import (
    ListQuestionSchema,
    QuestionSchema,
    ThemeIdSchema,
    ThemeListSchema,
    ThemeSchema,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class ThemeAddView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="add new theme")
    @request_schema(ThemeSchema)
    @response_schema(ThemeSchema)
    async def post(self):
        if not await self.store.quizzes.get_theme_by_title(self.data["title"]):
            theme = await self.store.quizzes.create_theme(
                title=self.data["title"],
            )
            return json_response(data=ThemeSchema().dump(theme))
        else:
            raise HTTPConflict(
                text="This title already exist. Provide unique theme",
            )


class ThemeListView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="get themes list")
    @response_schema(ThemeListSchema)
    async def get(self):
        themes = await self.store.quizzes.list_themes()
        return json_response(data=ThemeListSchema().dump({"themes": themes}))


class QuestionAddView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="add new question")
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema)
    async def post(self):
        theme = await self.request.app.store.quizzes.get_theme_by_id(
            self.data["theme_id"],
        )
        if not theme:
            raise HTTPNotFound(
                text="Theme id does not exist. "
                "Get available theme ids by /quiz.list_themes endpoint"
            )
        question = await self.request.app.store.quizzes.get_question_by_title(
            title=self.data["title"],
        )
        if question:
            raise HTTPConflict(
                text="This question already exist. Provide unique question",
            )

        answers = [Answer(**answer) for answer in self.data["answers"]]
        question = await self.request.app.store.quizzes.create_question(
            title=self.data["title"],
            theme_id=self.data["theme_id"],
            answers=answers,
        )
        return json_response(QuestionSchema().dump(question))


class QuestionListView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="get list of questions")
    @querystring_schema(ThemeIdSchema)
    @response_schema(ListQuestionSchema)
    async def get(self):
        theme_id = self.request.query.get("theme_id")
        if theme_id:
            questions = await self.request.app.store.quizzes.list_questions(
                int(theme_id)
            )

            if not questions:
                raise HTTPNotFound

            return json_response(ListQuestionSchema().dump({"questions": questions}))
        # return all questions
        questions = await self.request.app.store.quizzes.list_questions()
        if not questions:
            return json_response(ListQuestionSchema().dump({"questions": []}))
        return json_response(ListQuestionSchema().dump({"questions": questions}))

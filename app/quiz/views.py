from aiohttp.web_exceptions import HTTPConflict, HTTPNotFound
from aiohttp_apispec import (
    querystring_schema,
    request_schema,
    response_schema,
    docs
)

from sqlalchemy.exc import IntegrityError

from app.quiz.schemes import (
    ThemeSchema,
    ThemeAddRequestSchema,
    ThemeListResponseSchema,
    ThemeDeleteRequestSchema,
    QuestionSchema,
    QuestionAddRequestSchema,
    QuestionListRequestSchema,
    QuestionListResponseSchema,
    QuestionUpdateRequestSchema,
    QuestionDeleteRequestSchema,

)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class ThemeAddView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="add new theme")
    @request_schema(ThemeAddRequestSchema)
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
    @response_schema(ThemeListResponseSchema)
    async def get(self):
        themes = await self.store.quizzes.list_themes()
        return json_response(
            data=ThemeListResponseSchema().dump({"themes": themes}))


class ThemeUpdateView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="edit theme title")
    @request_schema(ThemeSchema)
    @response_schema(ThemeSchema)
    async def patch(self):
        theme = await self.request.app.store.quizzes.edit_theme_by_id(
            id_=self.data["id"], title=self.data["title"]
        )
        if not theme:
            raise HTTPNotFound(
                text=f"theme with id {self.data['id']} "
                     f"doesn't exist. Provide correct theme_id"
            )
        return json_response(ThemeSchema().dump(theme))


class ThemeDeleteView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="delete theme")
    @request_schema(ThemeDeleteRequestSchema)
    @response_schema(ThemeSchema)
    async def delete(self):
        theme = await self.request.app.store.quizzes.delete_theme_by_id(
            id_=self.data["theme_id"]
        )
        if not theme:
            raise HTTPNotFound(
                text=f"theme with id {self.data['theme_id']} "
                     f"doesn't exist. Provide correct theme_id"
            )
        return json_response(ThemeSchema().dump(theme))


class QuestionAddView(AuthRequiredMixin, View):
    @docs(
        tags=["quiz"],
        summary="add new question",
        description="param answer must be single word, param cost must be one "
                    "of 100,200,300,400,500")
    @request_schema(QuestionAddRequestSchema)
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

        question = await self.request.app.store.quizzes.create_question(
            title=self.data["title"],
            theme_id=self.data["theme_id"],
            answer=self.data["answer"],
            cost=self.data["cost"],
        )
        return json_response(QuestionSchema().dump(question))


class QuestionListView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="get list of questions")
    @querystring_schema(QuestionListRequestSchema)
    @response_schema(QuestionListResponseSchema)
    async def get(self):
        theme_id = self.request.query.get("theme_id")
        if theme_id:
            questions = await self.request.app.store.quizzes.list_questions(
                int(theme_id)
            )

            if not questions:
                raise HTTPNotFound

            return json_response(
                QuestionListResponseSchema().dump({"questions": questions}))
        # return all questions
        questions = await self.request.app.store.quizzes.list_questions()
        if not questions:
            return json_response(
                QuestionListResponseSchema().dump({"questions": []}))
        return json_response(
            QuestionListResponseSchema().dump({"questions": questions}))


class QuestionUpdateView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="update question data")
    @request_schema(QuestionUpdateRequestSchema)
    @response_schema(QuestionSchema)
    async def patch(self):
        question_id = self.data.pop("id")
        try:
            question = await self.request.app.store.quizzes.edit_question_by_id(
                id_=question_id, **self.data
            )
            if not question:
                raise HTTPNotFound(
                    text=f"question with id {question_id} "
                         f"doesn't exist. Provide correct question id"
                )

        except IntegrityError:
            raise HTTPNotFound(
                text=f"question with theme_id {self.data['theme_id']} "
                     f"doesn't exist. Provide correct theme_id"
            )

        return json_response(QuestionSchema().dump(question))


class QuestionDeleteView(AuthRequiredMixin, View):
    @docs(tags=["quiz"], summary="update question data")
    @request_schema(QuestionDeleteRequestSchema)
    @response_schema(QuestionSchema)
    async def delete(self):
        question = await self.request.app.store.quizzes.delete_question_by_id(
            self.data["question_id"]
        )
        if not question:
            raise HTTPNotFound(
                text=f"question with id {self.data['question_id']} "
                     f"doesn't exist. Provide correct question id"
            )
        return json_response(QuestionSchema().dump(question))

import typing

from app.quiz.views import (
    ThemeAddView,
    ThemeListView,
    ThemeUpdateView,
    ThemeDeleteView,
    QuestionAddView,
    QuestionListView,
    QuestionUpdateView,
    QuestionDeleteView,
)

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/quiz.add_theme", ThemeAddView)
    app.router.add_view("/quiz.list_themes", ThemeListView)
    app.router.add_view("/quiz.update_theme", ThemeUpdateView)
    app.router.add_view("/quiz.delete_theme", ThemeDeleteView)

    app.router.add_view("/quiz.add_question", QuestionAddView)
    app.router.add_view("/quiz.list_questions", QuestionListView)
    app.router.add_view("/quiz.update_question", QuestionUpdateView)
    app.router.add_view("/quiz.delete_question", QuestionDeleteView)

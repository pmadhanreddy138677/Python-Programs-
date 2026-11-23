from django.urls import path
from . import views as v

app_name = "ask"
urlpatterns = [
    path("", v.ask_list, name="list"),
    path("new/", v.ask_new, name="new"),
    path("moderation/", v.moderation, name="moderation"),
    path("reports/<int:pk>/<str:action>/", v.resolve_report, name="resolve"),
    path("<int:pk>/", v.ask_detail, name="detail"),
    path("<int:pk>/delete/", v.question_delete, name="delete"),
    path("<int:pk>/answer/", v.answer_new, name="answer"),
    path("<int:pk>/save/", v.bookmark, name="save"),
    path("<int:pk>/report/", v.report_question, name="report_question"),
    path("answers/<int:pk>/delete/", v.answer_delete, name="answer_delete"),
    path("answers/<int:pk>/helpful/", v.answer_helpful, name="helpful"),
    path("answers/<int:pk>/accept/", v.answer_accept, name="accept"),
    path("answers/<int:pk>/comment/", v.comment_new, name="comment"),
    path("answers/<int:pk>/report/", v.report_answer, name="report_answer"),
    path("comments/<int:pk>/delete/", v.comment_delete, name="comment_delete"),
]

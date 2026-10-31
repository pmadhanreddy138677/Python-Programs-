from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("learn/", views.learn_start, name="learn_start"),

    path("signup/", views.signup_page, name="signup_page"),
    path("login/", views.login_page, name="login_page"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_page, name="dashboard"),
    path("settings/", views.settings_page, name="settings_page"),

    path("assessment/start/", views.assessment_start, name="assessment_start"),
    path("assessment/", views.assessment_play, name="assessment_play"),

    path("practice/", views.practice_topics, name="practice_topics"),
    path("practice/<str:slug>/", views.practice_quiz, name="practice_quiz"),

    path("daily-challenge/", views.daily_challenge, name="daily_challenge"),
    path("revision/", views.revision_mode, name="revision_mode"),

    path("playground/", views.playground_page, name="playground_page"),
    path("playground/run/", views.playground_run, name="playground_run"),

    path("projects/", views.projects_list, name="projects_list"),
    path("projects/<str:slug>/", views.project_detail, name="project_detail"),
    path("projects/<str:slug>/submit/", views.project_submit, name="project_submit"),

    path("analytics/", views.analytics_page, name="analytics_page"),
    path("ai-analysis/", views.ai_analysis_page, name="ai_analysis_page"),

    path("friends/", views.friends_page, name="friends_page"),
    path("friends/add/", views.friend_add, name="friend_add"),
    path("friends/accept/<int:friendship_id>/", views.friend_accept, name="friend_accept"),
    path("friends/challenge/<int:user_id>/", views.friend_challenge_create,
         name="friend_challenge_create"),
    path("friends/challenge/play/<int:challenge_id>/", views.friend_challenge_play,
         name="friend_challenge_play"),
    path("friends/challenge/result/<int:challenge_id>/", views.friend_challenge_result,
         name="friend_challenge_result"),

    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/assignments/create/", views.teacher_assignment_create,
         name="teacher_assignment_create"),
    path("assignments/<int:assignment_id>/complete/", views.assignment_complete,
         name="assignment_complete"),

    path("language/", views.language_page, name="language_page"),
    path("language/<str:code>/", views.set_language, name="set_language"),

    path("level/", views.level_page, name="level_page"),
    path("level/<str:lvl>/", views.set_level, name="set_level"),

    path("purpose/", views.purpose_page, name="purpose_page"),
    path("purpose/<str:key>/", views.set_purpose, name="set_purpose"),

    path("mode/", views.mode_page, name="mode_page"),
    path("animation/", views.animation_page, name="animation_page"),
    path("animation/lesson/<slug:slug>/", views.animation_lesson_view, name="animation_lesson"),
    path("theory/", views.theory_page, name="theory_page"),

    path("game/", views.game_page, name="game_page"),
    path("game/answer/", views.game_answer, name="game_answer"),
    path("game/next/", views.game_next, name="game_next"),

    path("api/chat/", views.chat_send, name="chat_send"),
    path("api/chat/reset/", views.chat_reset, name="chat_reset"),
]

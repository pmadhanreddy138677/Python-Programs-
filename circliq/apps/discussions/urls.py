from django.urls import path
from . import views

app_name = "discussions"
urlpatterns = [
    path("posts/new/", views.create_post, name="create"),
    path("posts/<int:pk>/", views.post_detail, name="detail"),
    path("posts/<int:pk>/edit/", views.post_edit, name="edit"),
    path("posts/<int:pk>/delete/", views.post_delete, name="delete"),
    path("posts/<int:pk>/react/", views.post_react, name="react"),
    path("posts/<int:pk>/save/", views.post_save, name="save"),
    path("posts/<int:pk>/comment/", views.comment_add, name="comment"),
    path("posts/<int:pk>/accept/<int:cid>/", views.accept_answer, name="accept"),
    path("comments/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
    path("saved/", views.saved_posts, name="saved"),
]

from django.contrib import admin
from django.urls import include, path, re_path

from .views import frontend_index


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("game.urls")),
    re_path(r"^(?!static/|api/|admin/).*$", frontend_index),
]

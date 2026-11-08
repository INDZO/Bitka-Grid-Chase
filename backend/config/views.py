from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404


def frontend_index(_request):
    index_path = Path(settings.FRONTEND_DIST) / "index.html"
    if not index_path.exists():
        raise Http404("Frontend build nije pronađen.")
    return FileResponse(index_path.open("rb"), content_type="text/html")

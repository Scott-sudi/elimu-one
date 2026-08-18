"""Servir /media/ avec en-têtes CORS pour Flutter Web (localhost)."""

from __future__ import annotations

from django.views.static import serve as django_serve


def cors_media_serve(request, path, document_root=None, show_indexes=False):
    if request.method == "OPTIONS":
        from django.http import HttpResponse

        response = HttpResponse(status=204)
    else:
        response = django_serve(
            request,
            path,
            document_root=document_root,
            show_indexes=show_indexes,
        )

    origin = request.headers.get("Origin", "")
    if origin.startswith("http://localhost:") or origin.startswith(
        "http://127.0.0.1:",
    ):
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
        response["Vary"] = "Origin"
    return response

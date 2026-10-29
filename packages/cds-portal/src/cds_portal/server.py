from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route

import solara.server.starlette

from cds_client.cookies import make_student_cookie, verify_student_token

_COOKIE_NAME = "cds_student"
_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


async def student_auth(request: Request):
    """Verify the short-lived handshake token and set the long-lived session cookie."""
    token = request.query_params.get("t", "")
    next_url = request.query_params.get("next", "/")

    username = verify_student_token(token)
    if username is None:
        return RedirectResponse("/", status_code=303)

    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(
        _COOKIE_NAME,
        make_student_cookie(username),
        path="/",
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=_COOKIE_MAX_AGE,
    )
    return response


async def student_logout(request: Request):
    """Clear the student session cookie and redirect to the portal root."""
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(_COOKIE_NAME, path="/")
    return response


routes = [
    Route("/student-auth", endpoint=student_auth),
    Route("/student-logout", endpoint=student_logout),
    Mount("/", routes=solara.server.starlette.routes),
]

app = Starlette(routes=routes, middleware=solara.server.starlette.middleware)

"""cPanel/Passenger WSGI entrypoint wrapping the FastAPI ASGI application."""
from a2wsgi import ASGIMiddleware
from app.main import app

application = ASGIMiddleware(app)

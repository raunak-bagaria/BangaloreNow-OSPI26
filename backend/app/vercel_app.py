# Vercel Python serverless entry point.
# Vercel requires a module-level `app` (ASGI) object to be importable
# from the file referenced in vercel.json.
from app.main import app  # noqa: F401  re-exported for Vercel

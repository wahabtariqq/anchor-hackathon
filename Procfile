# Universal start command — Render, Railway and Heroku-style buildpacks all read this.
#
# `cd backend` matters twice: uvicorn needs `backend/` on sys.path to import `app.main`,
# and the repo root must still exist above it, because app/analysis/demo.py resolves
# contracts/fixtures/ as parents[3]. Deploying with a root directory of `backend/` builds
# fine and then fails on the demo path during the pitch.
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

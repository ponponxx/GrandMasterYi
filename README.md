# MasterYi local setup

This project has:
- `backend` (Flask + PostgreSQL)
- `frontend` (Vite + React)

## Version lock

- Python: `backend/runtime.txt` (`3.10.11`)
- Node: `.nvmrc` / `.node-version` (`24.13.1`)
- Backend direct deps: `backend/requirements.txt`
- Backend full lock deps: `backend/requirements.lock.txt`
- Frontend lock deps: `frontend/package-lock.json`

## First-time setup on a new machine (Windows)

1. Clone repo and open project root.
2. Run:
   ```bat
   setup-dev.bat
   ```
3. Edit `.env` with real secrets.
4. Start services:
   ```bat
   start-dev.bat
   ```

## Manual setup (if you do not use `setup-dev.bat`)

1. Backend:
   ```bat
   cd backend
   py -3.10 -m venv venv
   venv\Scripts\activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.lock.txt
   ```
2. Frontend:
   ```bat
   cd frontend
   npm ci
   npm run dev
   ```

## Environment variables

Copy `.env.example` to `.env` and fill in required values:
- `DATABASE_URL`
- `GOOGLE_CLIENT_ID`
- `JWT_SECRET` (at least 32 bytes)
- `GEMINI_API_KEY`
- `VITE_GOOGLE_CLIENT_ID`

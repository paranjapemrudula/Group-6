# MyFinance

MyFinance is a local full-stack finance dashboard built with Django and React. It focuses on portfolio management, stock tracking, market overview, market news, and stock analysis tools.

## Project Structure

```text
myFinance/
|-- backend/    Django REST API
|-- frontend/   React + Vite client
|-- README.md
```

## Features

- User signup and login
- Portfolio creation and stock tracking
- Sector-based stock browsing
- Live market overview
- Market news feed
- Stock analysis endpoints
- Portfolio analytics

## Local Setup

### 1. Clone the project

```bash
git clone <your-repository-url>
cd myFinance
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

Start the backend:

```bash
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000`.

### 3. Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Local Development Notes

- The frontend is already configured to call `http://127.0.0.1:8000` by default.
- Django settings are configured for localhost development.
- This project is now cleaned for local use only. Deployment-specific files and deployment-only setup steps were removed.

## Available Modules

- `accounts`: authentication
- `portfolios`: portfolio management
- `stocks`: stock data, sector browsing, news, and market overview
- `analysis`: stock and portfolio analytics
- `core`: health check

## Run Checklist

1. Start Django from `backend/`
2. Start Vite from `frontend/`
3. Open `http://localhost:5173`

## Notes

- Use the same machine for both backend and frontend during local development.
- If dependencies change, reinstall them with `pip install -r requirements.txt` and `npm install`.

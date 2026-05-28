# CareerStep

AI 기반 취업 지원 플랫폼 MVP입니다.

## Structure

```text
frontend/       React 18 + Vite + TypeScript
backend/
  main-api/     FastAPI main backend
  ai-api/       FastAPI AI service backend
```

## Run

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Frontend only:

```powershell
cd frontend
npm install
npm run dev
```

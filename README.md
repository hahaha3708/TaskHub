# TaskHub

Task management API for the FastAPI learning module. Day 1 covers layered architecture, Pydantic v2 schemas, dependency injection, and in-memory Task CRUD.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- Health: `GET /health`

## Day 1 endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/api/v1/tasks/` | Create a task |
| GET | `/api/v1/tasks/` | List tasks |
| GET | `/api/v1/tasks/{task_id}` | Get one task |
| PATCH | `/api/v1/tasks/{task_id}` | Partial update |
| DELETE | `/api/v1/tasks/{task_id}` | Delete a task |

Required fields such as `title`, `status`, and `priority` reject JSON `null` on PATCH. `description` and `due_date` may be cleared with `null`.

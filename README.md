# Loan Application Service: Step-by-Step Guide (A to Z)

This guide explains everything done in this project, in the order it was built, with every command. Follow it from top to bottom to set up and run the project on a new machine.

---

## Table of contents

1. [Install the tools](#part-1-install-the-tools-one-time)
2. [Create the project](#part-2-create-the-project)
3. [Install the packages](#part-3-install-the-packages)
4. [Start PostgreSQL with Docker](#part-4-start-postgresql-with-docker)
5. [Connect the app to the database](#part-5-connect-the-app-to-the-database)
6. [Create the tables with Alembic](#part-6-create-the-tables-with-alembic)
7. [Build the layers](#part-7-build-the-layers)
8. [Error handling and logging](#part-8-error-handling-and-logging)
9. [Business logic for loans](#part-9-business-logic-for-loans)
10. [Run the app](#part-10-run-the-app)
11. [Test in Postman](#part-11-test-in-postman)
12. [Check data in DBeaver](#part-12-check-data-in-dbeaver)
13. [Unit tests](#part-13-unit-tests)
14. [Code quality with Ruff](#part-14-code-quality-with-ruff)
15. [Git and GitHub](#part-15-git-and-github)
16. [README](#part-16-readme)
17. [Daily cheat sheet](#daily-cheat-sheet)

---

## Part 1: Install the tools (one time)

Install these on your machine:

| Tool | Used for |
|---|---|
| Python 3.14 | The programming language |
| uv | Installing packages and running commands |
| Docker Desktop | Running PostgreSQL in a container |
| Git | Version control |
| VS Code | Writing code |
| Postman | Testing the APIs |
| DBeaver | Viewing the database tables |

Check that they work:

```powershell
python --version
uv --version
docker --version
git --version
```

---

## Part 2: Create the project

```powershell
uv init --package loan-application
cd loan-application
uv python pin 3.14
```

This creates the `src/loan_application/` folder layout, `pyproject.toml` and `.python-version`.

---

## Part 3: Install the packages

```powershell
uv add "fastapi[standard]" "uvicorn[standard]" sqlalchemy "psycopg[binary]" alembic "pydantic[email]"
uv add --dev pytest httpx ruff
```

**Main packages**

| Package | What it does |
|---|---|
| FastAPI | Builds the API endpoints |
| Uvicorn | The server that runs the app |
| SQLAlchemy | Works with database tables as Python classes |
| psycopg | Connects Python to PostgreSQL |
| Alembic | Creates and updates tables (migrations) |
| Pydantic | Validates input and shapes output |

**Dev packages**

| Package | What it does |
|---|---|
| pytest | Runs the tests |
| httpx | Used for API tests |
| Ruff | Checks code style and finds mistakes |

`uv` creates the `.venv` folder and `uv.lock` file automatically.

> On a new machine, after cloning the repo, just run `uv sync` to install everything.

---

## Part 4: Start PostgreSQL with Docker

Create `docker-compose.yml` with:
- Image: `postgres:16`
- User: `kowshick`
- Database: `app_db`
- Port: `5433` (on your machine) → `5432` (inside the container)

Commands:

```powershell
docker compose up -d      # start the database
docker ps                 # check it is running
docker compose down       # stop it (data is kept in the volume)
```

---

## Part 5: Connect the app to the database

**`db.py`**
- Database URL (from the `DATABASE_URL` environment variable, with a default)
- `engine`: the connection to PostgreSQL
- `SessionLocal`: creates database sessions
- `Base`: the parent class for all models
- `get_db()`: opens a session for each request and closes it afterwards
- `DbSession`: the shortcut type used in routers

**`models.py`**
- `Customer` and `Loan` classes
- Each class is a table, and each attribute is a column

---

## Part 6: Create the tables with Alembic

Set up Alembic:

```powershell
uv run alembic init alembic
```

In `alembic/env.py`, point Alembic to `Base.metadata` and the database URL.

Create the customers table:

```powershell
uv run alembic revision --autogenerate -m "create customers table"
uv run alembic upgrade head
```

Create the loans table. Autogenerate does not detect CHECK constraints, so this migration was written by hand:

```powershell
uv run alembic revision -m "create loans table"
uv run alembic upgrade head
```

Useful extra commands:

```powershell
uv run alembic current        # which migration the database is on
uv run alembic history        # list all migrations
uv run alembic downgrade -1   # undo the last migration
```

---

## Part 7: Build the layers

Four folders inside `src/loan_application/`, each with one job:

| Folder | Job |
|---|---|
| `schemas/` | Pydantic models for what comes **in** (`CustomerCreate`, `LoanCreate`) and what goes **out** (`CustomerOut`, `LoanOut`, `CustomerSummary`). All field validation lives here. |
| `repositories/` | The only code that talks to the database: `get_by_id`, `add`, `delete`, `count_approved_for_customer`, `list_for_customer`. |
| `services/` | The brain: business rules, eligibility checks, EMI formula, commits, and raising `AppError` for 404 / 409. |
| `routers/` | The URLs. They receive the request and call the service. Nothing else. |

**Flow of every request:**

```
Router → Service → Repository → Database
```

---

## Part 8: Error handling and logging

**`exceptions.py`**
- `AppError` class for business errors (404, 409)
- Three handlers: app errors, HTTP errors (404 / 405), validation errors (400)
- `error_response()` gives every error the same shape:

```json
{
  "error": "NOT_FOUND",
  "message": "Customer with id 99 not found",
  "request_id": "3f2a9c1e..."
}
```

**`logging_config.py`**
- Puts the request ID on every log line

**`main.py`**
- Creates the FastAPI app
- Adds the **middleware**: request ID, response timing, catching crashes as 500
- Registers the error handlers
- Includes the routers
- Adds the `/health` endpoint

---

## Part 9: Business logic for loans

All in `services/loan_service.py`.

**Interest rate by tenure**

| Tenure (months) | 12 | 24 | 36 | 48 | 60 |
|---|---|---|---|---|---|
| Annual rate | 10% | 11% | 12% | 13% | 13% |

**Eligibility rules (checked in order, the first failure is the reason)**

1. Age must be between 21 and 60
2. Amount must not exceed 20 × monthly income
3. Customer must have fewer than 2 approved loans

**EMI formula**

```
r   = annual_rate / 12 / 100
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)
```

Rounded to 2 decimals. Example: ₹3,00,000 at 12% for 36 months = **₹9,964.29**

**Result**
- All rules pass → **APPROVED**, with EMI
- Any rule fails → **REJECTED**, with the reason
- Both are saved and return **201 Created**

---

## Part 10: Run the app

```powershell
docker compose up -d
uv run fastapi dev src/loan_application/main.py
```

| URL | What it is |
|---|---|
| `http://localhost:8000` | The API |
| `http://localhost:8000/docs` | Swagger docs |
| `http://localhost:8000/health` | Health check |

Stop the server with **Ctrl + C**.

---

## Part 11: Test in Postman

Set the body to **raw → JSON**. Test in this order:

| # | Request | Expected |
|---|---|---|
| 1 | `POST /api/customers` | 201 Created |
| 2 | `GET /api/customers/{id}` | 200 OK |
| 3 | `POST /api/loans` | 201, APPROVED with EMI |
| 4 | `POST /api/loans` with a big amount | 201, REJECTED (20× income) |
| 5 | `POST /api/loans` for a third loan | 201, REJECTED (2 active loans) |
| 6 | `GET /api/customers/{id}/loans` | 200, list of loans |
| 7 | `GET /api/customers/{id}/summary` | 200, loan totals |
| 8 | Any request with a wrong ID | 404 Not Found |
| 9 | Any request with bad data | 400 Validation Failed |

---

## Part 12: Check data in DBeaver

1. New connection → **PostgreSQL**
2. Host: `localhost`
3. Port: `5433`
4. Database: `app_db`
5. User: `kowshick`
6. Open the `customers` and `loans` tables
7. Press **Refresh** after each Postman request to see the new data

---

## Part 13: Unit tests

Created a `tests/` folder at the project root:

| File | What it contains |
|---|---|
| `conftest.py` | Fixtures (`today`, `make_customer`) and a fresh `test_app_db` database that is created and dropped on every run |
| `test_loan_rules.py` | 18 tests for EMI, every eligibility rule, boundary values and rule order |

Commands:

```powershell
uv run pytest -v                      # run all tests
uv run pytest -v -k "age"             # run only tests with "age" in the name
uv run pytest -v -k "not database"    # skip the database test
```

> PostgreSQL must be running (`docker compose up -d`) for the database test.

---

## Part 14: Code quality with Ruff

```powershell
uv run ruff check .          # find problems
uv run ruff check . --fix    # fix what it can automatically
uv run ruff format .         # format the code
```

---

## Part 15: Git and GitHub

**First time**

```powershell
git init
git remote add origin https://github.com/kowshick-ionixx/Loan-Applications.git
git add .
git commit -m "Initial project setup"
git push -u origin main
```

**Every change**

```powershell
git status
git add .
git commit -m "Clear message about what changed"
git push
```

**The proper way: feature branch and Pull Request**

```powershell
git checkout -b feature/final-wrap-up
git add .
git commit -m "Add README and Postman collection"
git push -u origin feature/final-wrap-up
```

Then open a **Pull Request** on GitHub and merge it into `main`.

---

## Part 16: README

Added `README.md` with:
- What the project does
- Setup steps
- All API endpoints with examples
- Validation and eligibility rules
- Error codes
- How to run the tests
- Week 1 summary

---

## Daily cheat sheet

```powershell
docker compose up -d                              # 1. start the database
uv run fastapi dev src/loan_application/main.py   # 2. start the app
uv run pytest -v                                  # 3. run the tests
uv run ruff check .                               # 4. check the code
git add .                                         # 5. save your work
git commit -m "message"
git push
```
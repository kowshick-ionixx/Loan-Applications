# Loan Application Service: Step-by-Step Guide (A to Z)

This guide explains everything done in this project, in the order it was built, with every command. Follow it from top to bottom to set up and run the project on a new machine.

---

## Table of contents

- [API reference](#api-reference) (every endpoint, and which ones are extra)

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
11. [Test the APIs](#part-11-test-the-apis)
12. [Check data in DBeaver](#part-12-check-data-in-dbeaver)
13. [Unit tests](#part-13-unit-tests)
14. [Code quality with Ruff, black and pre-commit](#part-14-code-quality-with-ruff-black-and-pre-commit)
15. [Git and GitHub](#part-15-git-and-github)
16. [README](#part-16-readme)
17. [Week 2 Monday - Authentication and roles](#part-17-week-2-monday---authentication-and-roles)
18. [Week 2 Wednesday - Docker and CI](#part-18-week-2-wednesday---docker-and-ci)
19. [Daily cheat sheet](#daily-cheat-sheet)

---

## API reference

Every request except `/health`, `/auth/register` and `/auth/login` needs `Authorization: Bearer <token>`.

**Active:** the Round 2 and Plan endpoints (up to Week 2 Tuesday) plus `POST /auth/register`; these 9 are what Swagger shows at `http://localhost:8000/docs`. Every other **EXTRA** endpoint is **commented out** in the code, marked `# EXTRA API (not in Round 2 spec / plan up to Week 2 Tuesday) - uncomment to enable.` To turn one back on, uncomment its route and the `# EXTRA API imports` lines at the top of that router (for `/api/users`, the two lines in `main.py`); its tests are marked `@EXTRA` (skipped) in the test files, so remove that marker too.

**Source** says where each endpoint comes from:
- **Round 2**: one of the six APIs in the Round 2 assessment (their JSON shape and status codes follow that spec).
- **Plan**: asked for in the 2-week plan (day noted).
- **EXTRA**: added on top of the spec and the plan; **commented out** for now, except `POST /auth/register`.

### Health and authentication

| Method | Path | Who | Success | Source |
|---|---|---|---|---|
| GET | `/health` | public | 200 `{"status": "ok"}` (also checks the database) | Plan, Week 1 Mon |
| POST | `/auth/login` | public | 200 `{"access_token", "token_type", "expires_in"}`; form body, not JSON | Plan, Week 2 Mon |
| POST | `/auth/register` | public | 201 the new user; body is only `username` and `password`; creates a CUSTOMER login with no profile yet | **EXTRA, enabled** (the plan only asks for login; officers come from the seed script) |

### Customers

| Method | Path | Who | Success | Source |
|---|---|---|---|---|
| POST | `/api/customers` | CUSTOMER (own profile, once); OFFICER | 201 the customer | Round 2, API 1 (who may call it is **EXTRA**) |
| GET | `/api/customers/{id}` | OFFICER any; CUSTOMER own | 200 the customer | Round 2, API 2 |
| GET | `/api/customers/{id}/loans?status=` | OFFICER any; CUSTOMER own | 200 list of loans, newest first | Round 2, API 5 |
| GET | `/api/customers/{id}/summary` | OFFICER any; CUSTOMER own | 200 the loan summary | Round 2, API 6 |
| GET | `/api/customers?page=&size=` | OFFICER | 200 `{"items", "page", "size", "total", "pages"}` | **EXTRA** |
| GET | `/api/customers/me` | CUSTOMER | 200 own profile (officer: 404) | **EXTRA** |
| PATCH | `/api/customers/{id}` | OFFICER any field; CUSTOMER own `name`, `phone`, `address` only | 200 the updated customer | **EXTRA** (started as PUT, changed to PATCH) |
| DELETE | `/api/customers/{id}` | OFFICER | 200 `{"message": "Customer deleted successfully"}`; 409 if it has approved loans | **EXTRA** |

### Loans

| Method | Path | Who | Success | Source |
|---|---|---|---|---|
| POST | `/api/loans` | OFFICER any; CUSTOMER own `customer_id` | 201 the loan (APPROVED or REJECTED) | Round 2, API 3 |
| GET | `/api/loans/{id}` | OFFICER any; CUSTOMER own | 200 the loan | Round 2, API 4 |
| GET | `/api/loans?status=` | OFFICER all; CUSTOMER own | 200 list of loans, newest first | **EXTRA** for now: it is a Week 2 Thu task (`page` and `size` not added yet) |
| DELETE | `/api/loans/{id}` | OFFICER | 200 `{"message": "Loan deleted successfully"}` | **EXTRA** |

### Users (all **EXTRA**, commented out)

| Method | Path | Who | Success |
|---|---|---|---|
| GET | `/api/users/me` | anyone logged in | 200 own user |
| GET | `/api/users/{id}` | OFFICER any; CUSTOMER own | 200 the user |
| GET | `/api/users` | OFFICER | 200 list of users |
| PATCH | `/api/users/{id}/role` | OFFICER, not on themselves | 200 the updated user; body `{"role": "OFFICER"}` or `"CUSTOMER"` |
| PATCH | `/api/users/me/password` | anyone logged in | 200 `{"message": "Password changed successfully"}`; body `{"old_password", "new_password"}` |
| DELETE | `/api/users/{id}` | OFFICER, not on themselves | 200 `{"message": "User deactivated successfully"}` (soft delete) |

### Errors (every endpoint)

| Status | `error` | When |
|---|---|---|
| 400 | `VALIDATION_FAILED` (with `details`, one entry per failing field) | Bad field, bad id, bad query parameter |
| 400 | `INVALID_REQUEST` | Body is not valid JSON |
| 401 | `UNAUTHORIZED` / `INVALID_CREDENTIALS` | No, bad, expired or tampered token; inactive user / wrong login |
| 403 | `FORBIDDEN` (or a specific code such as `CANNOT_DEMOTE_SELF`) | Wrong role, or another customer's data |
| 404 | `NOT_FOUND` | Record does not exist |
| 409 | `DUPLICATE_EMAIL`, `DUPLICATE_USERNAME`, `CUSTOMER_HAS_ACTIVE_LOANS`, `CUSTOMER_REMOVED` | Conflict with existing data |
| 500 | `INTERNAL_ERROR` | Unexpected failure; no stack trace is sent |

Every error body also has `request_id`, the same value as the `X-Request-ID` response header.

**Other extras beyond the spec:** the optional `address` field on customers, the officer/customer roles on the Round 2 APIs, and plain-text logs by default (`LOG_FORMAT=json` gives the JSON logs the plan asks for).

---

## Part 1: Install the tools (one time)

Install these on your machine:

| Tool | Used for |
|---|---|
| Python 3.12 | The programming language |
| uv | Installing packages and running commands |
| Docker Desktop | Running PostgreSQL in a container |
| Git | Version control |
| VS Code | Writing code |
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
uv python pin 3.12
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
- Puts the request ID (and, once logged in, the user ID) on every log line
- Writes plain, readable lines by default (the status code is coloured in a terminal):

```text
2026-10-14 10:32:32 | INFO    | 678a9a43... | user_id=55 | GET /api/customers/7 -> 200 (4.2 ms)
```

- Set `LOG_FORMAT=json` in `.env` to get one JSON object per line instead, for log tools that search by `request_id` or `user_id`. Stack traces stay in the server log; the client only ever sees `INTERNAL_ERROR`.

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

## Part 11: Test the APIs

Start the app (Part 10) and open `http://localhost:8000/docs`. Click **Authorize**, log in as an officer (`officer1`, see Part 17), then use **Try it out** on each endpoint. Every endpoint lists the error responses it can return. Test in this order:

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
| 10 | `DELETE /api/loans/{id}` or `/api/customers/{id}` | 200, `{"message": "Loan deleted successfully"}` / `"Customer deleted successfully"` |

---

## Part 12: Check data in DBeaver

1. New connection → **PostgreSQL**
2. Host: `localhost`
3. Port: `5433`
4. Database: `app_db`
5. User: `kowshick`
6. Open the `customers` and `loans` tables
7. Press **Refresh** after each request to see the new data

---

## Part 13: Unit tests

| File | What it covers |
|---|---|
| `tests/conftest.py` | Shared fixtures (test database, client, officer, signup) and helpers; not a test file |
| `tests/test_customers.py` | Customer create, read, list (paging), `/me`, PATCH rules, delete, summary, ownership |
| `tests/test_loans.py` | Unit tests for EMI, every eligibility rule and risk bands; loan apply, get, list, delete; the full customer journey |
| `tests/test_users.py` | Register, login, tokens, `/api/users`, 400/401/403/404 on every endpoint, logging, health, seed script |

All of them run against `app_db_test`, never `app_db` (see Part 17). Coverage: `uv run pytest --cov=loan_application`.

```powershell
uv run pytest -v                      # run all tests
uv run pytest -v -k "loan"            # run only tests with "loan" in the name
```

> PostgreSQL must be running (`docker compose up -d`).

---

## Part 14: Code quality with Ruff, black and pre-commit

```powershell
uv run ruff check .          # find problems
uv run ruff check . --fix    # fix what it can automatically
uv run black .               # format the code
uv run pre-commit install    # once: run ruff + black on every git commit
uv run pre-commit run --all-files
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
git commit -m "Add README"
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

## Part 17: Week 2 Monday - Authentication and roles

New packages: `pwdlib[argon2]` (password hashing), `pyjwt` (tokens), `pydantic-settings` (reads `.env`), `python-multipart` (login form).

### Setup

1. Copy `.env.example` to `.env` and fill in the placeholders. No secret lives in the code; everything comes from `.env` (git-ignored):

   | Variable | Used for |
   |---|---|
   | `POSTGRES_PASSWORD`, `DATABASE_URL` | Docker and the app's database |
   | `JWT_SECRET_KEY` | Signs tokens, at least 32 characters (`python -c "import secrets; print(secrets.token_hex(32))"`) |
   | `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | `HS256`, `30` |
   | `SEED_OFFICER_PASSWORD` | Password for the first officer (if empty, the seed script asks for it) |
   | `LOG_FORMAT` | `text` (default) or `json` |

2. Create the tables and the first officer (`officer1`):

   ```powershell
   uv run alembic upgrade head
   uv run python -m loan_application.scripts.seed
   ```

### The flow: register → login → use the APIs

1. `POST /auth/register` with JSON creates a CUSTOMER login only (no profile yet):
   `{"username": "arjun_ramesh", "password": "Arjun@1234"}`. A `role` (or any other field) in the body is ignored. A taken username gives 409 `DUPLICATE_USERNAME`.
2. `POST /auth/login` with a **form body** (`x-www-form-urlencoded`, the OAuth2 standard; the only endpoint that does not take JSON): `username=arjun_ramesh&password=Arjun@1234` → `{"access_token": "...", "token_type": "bearer", "expires_in": 1800}`. Log in with the **username**, not the name.
3. Send `Authorization: Bearer <access_token>` on every other request. In Swagger, click **Authorize** and log in there.
4. Create your profile with `POST /api/customers` (customer token):
   `{"name": "Arjun Ramesh", "email": "arjun.ramesh@example.com", "phone": "9876543210", "date_of_birth": "1995-06-18", "monthly_income": 85000, "address": "Chennai"}` (`address` is optional). It is linked to your login; a second call gives 409 `PROFILE_EXISTS`, a taken email 409 `DUPLICATE_EMAIL`. Until then, the other customer endpoints answer 403 `CUSTOMER_PROFILE_REQUIRED`.
5. Officers come from the seed script. An officer can also create a customer (`POST /api/customers`) and give them a login from the terminal:

   ```powershell
   uv run python -c "from loan_application.scripts.seed import create_customer_user; create_customer_user('meena', 'Secret@123', customer_id=1)"
   ```

The table below includes the EXTRA endpoints for reference; they answer 404 while commented out.

### Who can do what

| Endpoint | No token | CUSTOMER | OFFICER |
|---|---|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /health` | public | public | public |
| `POST /api/customers` | 401 | 201 own profile, linked to the login (409 `PROFILE_EXISTS` if it already has one; 409 `DUPLICATE_EMAIL`) | 201 unlinked profile (409 `DUPLICATE_EMAIL`) |
| `GET /api/customers?page=&size=` | 401 | 403 (use `/me`) | 200, paginated: `{"items", "page", "size", "total", "pages"}` |
| `GET /api/customers/me` | 401 | own profile | 404 (officers have no profile) |
| `GET /api/customers/{id}`, `/summary`, `/loans` | 401 | own only, else 403 | any (404 if missing) |
| `PATCH /api/customers/{id}` | 401 | own only, and only `name`, `phone`, `address` (other fields 403; unknown fields such as `customer_id` ignored) | any field (409 `DUPLICATE_EMAIL`) |
| `DELETE /api/customers/{id}` | 401 | 403 | 200 `{"message": "Customer deleted successfully"}`; 409 `CUSTOMER_HAS_ACTIVE_LOANS` if any APPROVED loan (rejected applications are deleted with the customer) |
| `POST /api/loans` | 401 | own `customer_id` only | 201 |
| `GET /api/loans?status=`, `GET /api/loans/{id}` | 401 | own loans only | all |
| `DELETE /api/loans/{id}` | 401 | 403 | 200 `{"message": "Loan deleted successfully"}` |
| `GET /api/users/me` | 401 | own user | own user |
| `GET /api/users/{id}` | 401 | own only, else 403 | any (404 if missing) |
| `GET /api/users` | 401 | 403 | all users |
| `PATCH /api/users/{id}/role` `{"role": "OFFICER"}` | 401 | 403 | 200; 403 `CANNOT_DEMOTE_SELF` on themselves. Promoting a customer unlinks their profile (the profile and loans stay) |
| `PATCH /api/users/me/password` `{"old_password", "new_password"}` | 401 | 200 `{"message": "Password changed successfully"}`; 400 `WRONG_PASSWORD` | same |
| `DELETE /api/users/{id}` | 401 | 403 | 200 `{"message": "User deactivated successfully"}` (soft delete: cannot log in or use a token); 403 `CANNOT_DEACTIVATE_SELF` |

- `401 UNAUTHORIZED` (with header `WWW-Authenticate: Bearer`): no token, bad or expired token, unknown or inactive user. This comes before any 400: even a malformed JSON body gets 401 if the caller has no valid token (FastAPI reads the body before the dependencies run, so `main.py` checks the token first in the validation error handler). Wrong login details give `401 INVALID_CREDENTIALS`, the same for a wrong username or a wrong password.
- `403 FORBIDDEN`: wrong role, or another customer's data. A customer gets 403 even for ids that do not exist, so they cannot probe which ids exist; an officer gets 404. `403 CUSTOMER_PROFILE_REQUIRED`: a customer login that has not created its profile yet (or whose profile was deleted).
- Every log line carries the request id and the user id (`user_id=-` when not logged in), see Part 8. Passwords and tokens are never logged.

### How a request is checked

`token` → `get_current_user` (decodes the JWT, loads the user from the database, puts `user_id` in the log context) → `require_customer_profile` → the service's `check_owner` (a CUSTOMER only reaches their own `customer_id`) → repository.

| File | Job |
|---|---|
| `config.py` | Settings from `.env` |
| `security.py` | Argon2 hash/verify, create/decode JWTs |
| `dependencies.py` | `get_current_user`, `require_customer_profile`, `require_officer` |
| `services/auth_service.py` | Register (login + profile), check credentials |
| `services/customer_service.py` | Customer CRUD, paging, editable-field rule, `check_owner` |
| `services/user_service.py` | Users: read, list, change role, change password, deactivate |
| `routers/auth.py` | `POST /auth/register`, `POST /auth/login` |
| `routers/users.py` | `/api/users` endpoints |
| `alembic/versions/d81f3b6c2a45_...py` | Adds the optional `customers.address` column |
| `scripts/seed.py` | Create or reset the officer; `create_customer_user(username, password, customer_id=None)` |
| `alembic/versions/c4e8f2a19d07_...py` | Deleting a customer sets the user's `customer_id` to NULL |
| `tests/test_users.py` | Register, login, token and role tests |

### Tests use their own database

`pytest` always runs against `app_db_test`: `tests/conftest.py` switches the URL before the engine is created, rebuilds the schema with the Alembic migrations, rolls every test back, and aborts if the database name does not end in `_test`. Your `app_db` is never touched.

---

## Part 18: Week 2 Wednesday - Docker and CI

### Run everything with one command (clean clone)

```powershell
git clone https://github.com/kowshick-ionixx/Loan-Applications.git
cd Loan-Applications
copy .env.example .env        # then fill in the placeholders (see Part 17)
docker compose up --build -d
```

That starts two containers:

| Service | What it does |
|---|---|
| `db` | PostgreSQL 16 on `localhost:5433`. A healthcheck (`pg_isready`) tells compose when it is ready. On a **new** volume, `docker/initdb/create-test-db.sql` also creates `app_db_test` for pytest. |
| `api` | Waits until `db` is healthy, then `docker/entrypoint.sh` runs `alembic upgrade head`, seeds `officer1` if `SEED_OFFICER_PASSWORD` is set, and starts uvicorn on `http://localhost:8000`. |

```powershell
docker compose ps             # both should say (healthy)
docker compose logs -f api    # follow the api logs
docker compose down           # stop (data kept); add -v to also delete the data
```

Developing locally is unchanged: `docker compose up -d db` starts only the database, and `uv run fastapi dev src/loan_application/main.py` runs the app on your machine.

### The image (`Dockerfile`)

- Two stages: `build` installs the locked packages with `uv sync --locked --no-dev`; `runtime` copies only the finished `.venv`, so uv and its cache are not in the final image.
- Dependencies are installed before the source is copied, so changing code does not reinstall packages.
- Runs as a normal user (`app`), not root, and has a `HEALTHCHECK` on `/health`.
- `.dockerignore` keeps `.env`, `.git`, `.venv` and the tests out of the image.

### Secrets only via environment

- `config.py` (pydantic-settings) reads every setting from environment variables; `.env` is only a local convenience and is git-ignored and docker-ignored.
- `docker-compose.yml` has no secret in it: it passes `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` and `SEED_OFFICER_PASSWORD` from `.env`, and stops with an error such as `set JWT_SECRET_KEY in .env` if a required one is missing.
- Inside compose, `DATABASE_URL` points at `db:5432` (the service name), not `localhost:5433`.
- CI generates a fresh random `JWT_SECRET_KEY` for every run; its database is a throwaway service container.

### CI (`.github/workflows/ci.yml`)

Runs on every pull request and every push to `main`:

| Job | Steps |
|---|---|
| Lint | `uv sync --locked`, `ruff check .`, `black --check .` |
| Tests | PostgreSQL 16 service with `app_db_test`, then `pytest --cov=loan_application --cov-fail-under=80` (fails under 80% coverage) |
| Docker | `docker build .` so a broken Dockerfile fails the PR |

Run the same checks locally before pushing:

```powershell
uv run ruff check .
uv run black --check .
uv run pytest --cov=loan_application --cov-fail-under=80
```

---

## Daily cheat sheet

```powershell
docker compose up -d db                           # 1. start the database (or: docker compose up --build -d for db + api)
uv run fastapi dev src/loan_application/main.py   # 2. start the app
uv run pytest -v                                  # 3. run the tests
uv run ruff check .                               # 4. check the code
git add .                                         # 5. save your work
git commit -m "message"
git push
```
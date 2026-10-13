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
17. [Week 2 Monday - Login with JWT](#part-17-week-2-monday---login-with-jwt)
18. [Daily cheat sheet](#daily-cheat-sheet)

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

The full end-to-end run is in `postman/loan-application.postman_collection.json` (57 requests: every Round 2 checklist case plus register, login, profile and ownership). The login requests store the token in a collection variable. Start the app, then run it from the terminal (or import it into Postman and set `officerPassword`):

```powershell
postman collection run postman/loan-application.postman_collection.json --env-var officerPassword=<password>
```

Set the body to **raw → JSON**. Since Week 2, first log in as an officer (`POST /auth/login`, see Part 17) and set **Authorization → Bearer Token** on the collection. Test in this order:

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

| File | What it covers |
|---|---|
| `tests/test_loan_rules.py` | Unit tests: EMI per tenure, every eligibility rule at its boundaries, rule order, risk bands |
| `tests/test_api.py` | All six Round 2 APIs and the 18-scenario self-test checklist |
| `tests/test_auth.py` | Register, login, tokens, profile required, ownership |
| `tests/test_flow.py` | One end-to-end customer journey through the API |
| `tests/test_seed.py` | The seed script |

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

2. Create the tables and the first officer (`officer1`):

   ```powershell
   uv run alembic upgrade head
   uv run python -m loan_application.scripts.seed
   ```

### The flow: register → login → create profile → use the APIs

1. `POST /auth/register` with JSON `{"username": "meena", "password": "Secret@123"}` creates a CUSTOMER account with no profile (a `role` in the body is ignored). Usernames are stored in lowercase.
2. `POST /auth/login` with a **form body** (`x-www-form-urlencoded`, the OAuth2 standard; this is the only endpoint that does not take JSON): `username=meena&password=Secret@123` → `{"access_token": "...", "token_type": "bearer", "expires_in": 1800}`.
3. Send `Authorization: Bearer <access_token>` on every other request. In Swagger, click **Authorize** and log in there.
4. `POST /api/customers` with the Round 2 customer body creates the profile **and links it to your account** in one transaction. Until then every customer/loan API returns `403 CUSTOMER_PROFILE_REQUIRED`.
5. Officers are created only by the seed script. `create_customer_user(username, password, customer_id=None)` in `scripts/seed.py` can also make a customer login from the terminal.

### Who can do what

| Endpoint | No token | CUSTOMER no profile | CUSTOMER with profile | OFFICER |
|---|---|---|---|---|
| `POST /auth/login`, `POST /auth/register`, `GET /health` | public | public | public | public |
| `POST /api/customers` | 401 | 201 + linked | 409 `PROFILE_ALREADY_EXISTS` | 201 (not linked) |
| `GET /api/customers/{id}` | 401 | 403 | own 200, other 403 | 200 |
| `GET /api/customers/{id}/summary`, `/loans` | 401 | 403 | own only | 200 |
| `POST /api/loans` | 401 | 403 | own `customer_id` only | 201 |
| `GET /api/loans/{id}` | 401 | 403 | own loan only | 200 |

- `401 UNAUTHORIZED` (with header `WWW-Authenticate: Bearer`): no token, bad or expired token, unknown or inactive user. Wrong login details give `401 INVALID_CREDENTIALS`, the same for a wrong username or a wrong password.
- `403 FORBIDDEN`: wrong role, or another customer's data. A customer gets 403 even for ids that do not exist, so they cannot probe which ids exist; an officer gets 404.
- Every log line carries the request id and the user id (`user_id=-` when not logged in), e.g. `2026-10-13 21:30:01 | INFO    | 678a9a43... | user_id=55 | GET /api/customers/7 -> 200 (4.2 ms)`; the status code is coloured in a terminal. Passwords and tokens are never logged.

### How a request is checked

`token` → `get_current_user` (decodes the JWT, loads the user from the database, puts `user_id` in the log context) → `require_customer_profile` → the service's `check_owner` (a CUSTOMER only reaches their own `customer_id`) → repository.

| File | Job |
|---|---|
| `config.py` | Settings from `.env` |
| `security.py` | Argon2 hash/verify, create/decode JWTs |
| `dependencies.py` | `get_current_user`, `require_customer_profile` |
| `services/auth_service.py` | Register, check credentials, issue token |
| `services/customer_service.py` | Profile creation and linking, `check_owner` |
| `routers/auth.py` | `POST /auth/register`, `POST /auth/login` |
| `scripts/seed.py` | Create or reset the officer; `create_customer_user(username, password, customer_id=None)` |
| `alembic/versions/c4e8f2a19d07_...py` | Deleting a customer sets the user's `customer_id` to NULL |
| `tests/test_auth.py` | Register, login, tokens, profile and ownership tests |

### Tests use their own database

`pytest` always runs against `app_db_test`: `tests/conftest.py` switches the URL before the engine is created, rebuilds the schema with the Alembic migrations, rolls every test back, and aborts if the database name does not end in `_test`. Your `app_db` is never touched.

The Postman collection needs the officer password passed in: `--env-var officerPassword=<password>`.

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
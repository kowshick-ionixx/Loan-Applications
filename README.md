# Loan Application Service

A REST API for a small lending company: register customers, apply for loans with automatic
eligibility checks and EMI calculation, and report each customer's loan position.
Every endpoint except `/health` and `/auth/login` needs a JWT, and a customer can only see their own data.

**Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16 (Docker), JWT (PyJWT), Argon2 password hashing (pwdlib), pytest, uv.

## Run it

```powershell
docker compose up -d                          # PostgreSQL on localhost:5433, database loan_db
uv sync                                       # install packages
uv run alembic upgrade head                   # create the tables
uv run python -m loan_application.seed        # create the officer login
uv run uvicorn loan_application.main:app --reload
```

First copy `.env.example` to `.env` and fill in your own values. `.env` is git-ignored, so no password or secret is in the repo; Docker, Alembic and the app all read it:

```
POSTGRES_PASSWORD=<database password>
DATABASE_URL=postgresql+psycopg://kowshick:<database password>@localhost:5433/loan_db
JWT_SECRET_KEY=<any long random string>
```

Open **http://127.0.0.1:8000/docs**, click **Authorize** and log in.

## Logins and roles

| Role | How the login is made | What it can do |
|---|---|---|
| OFFICER | `uv run python -m loan_application.seed` (username `officer1`) | Everything |
| CUSTOMER | `create_customer_user(username, password, customer_id)` in `seed.py` | Only their own customer, loans and summary |

Create a customer login for an existing customer (example: customer 1):

```powershell
uv run python -c "from loan_application.seed import create_customer_user; create_customer_user('kowshick', '<password>', 1)"
```

- No token, a bad token or an expired token: **401 UNAUTHORIZED**
- Logged in, but not allowed (wrong role, or another customer's id): **403 FORBIDDEN**
- Every request logs the user id: `... user=<id> ...`

## Endpoints

| Method | Path | Who | Result |
|---|---|---|---|
| GET | `/health` | anyone | DB connection check |
| POST | `/auth/login` | anyone | form fields `username`, `password` → `access_token` |
| POST | `/customers/` | officer | 201 customer, 409 `DUPLICATE_EMAIL` |
| GET | `/customers/{id}` | officer, owner | 200, 404, 400 if id ≤ 0 |
| PUT | `/customers/{id}` | officer, owner (owner cannot change income or date of birth) | 200 |
| DELETE | `/customers/{id}` | officer | 200, 409 if the customer has loans |
| GET | `/customers/{id}/loans?status=` | officer, owner | newest first; status must be APPROVED or REJECTED |
| GET | `/customers/{id}/summary` | officer, owner | totals, EMI-to-income ratio, risk band |
| POST | `/loans/apply` | officer, owner | 201 APPROVED or REJECTED |
| GET | `/loans/{id}` | officer, owner | 200, 404 |
| GET | `/loans/?customer_id=` | officer, owner | same list as `/customers/{id}/loans` |
| DELETE | `/loans/{id}` | officer | 200 |

## Business rules

- **Customer:** name 3–50 letters and spaces; valid unique email; unique 10-digit phone; date of birth in the past; monthly income > 0.
- **Loan:** amount 10,000–5,000,000; tenure 12/24/36/48/60 months.
- **Eligibility, first failure wins:** age 21–60 → amount ≤ 20 × monthly income → fewer than 2 APPROVED loans. Rejected applications are saved too.
- **Interest:** 12 → 10%, 24 → 11%, 36 → 12%, 48/60 → 13%. EMI = P·r·(1+r)ⁿ / ((1+r)ⁿ − 1), r = rate ÷ 12 ÷ 100, rounded to 2 decimals (300000 for 36 months → 9964.29).
- **Risk band:** EMI-to-income ratio below 30 LOW, 30–50 MEDIUM, above 50 HIGH.

## Errors

| Status | `error` | When |
|---|---|---|
| 400 | `VALIDATION_FAILED` | one entry in `details` for every failing field |
| 400 | `INVALID_REQUEST` | body missing or not valid JSON |
| 401 | `UNAUTHORIZED` | no token, bad token, wrong password |
| 403 | `FORBIDDEN` | wrong role or another customer's data |
| 404 | `NOT_FOUND` | customer or loan does not exist |
| 409 | `DUPLICATE_EMAIL` / `CONFLICT` | email already used / customer still has loans |
| 500 | `INTERNAL_ERROR` | anything unexpected; no stack trace is returned |

## Tests

```powershell
uv run pytest                                                 # service and smoke tests (SQLite in memory)
postman collection run "postman/collections/loan application e2e"   # 60 end-to-end requests, server must be running
uv run ruff check src tests alembic                           # lint
```

The Postman collection covers the whole Round 2 checklist plus login, roles and ownership.
It logs in as `officer1` and as the customer `kowshick`, linked to customer 1 (change the `myId` variable if yours differs).

## Layout

```
src/loan_application/
  main.py            app, routers, error handlers
  config.py          settings from .env (database URL, JWT secret)
  db.py              engine and session
  tables.py          SQLAlchemy tables: customers, loans, users
  security.py        password hashing, JWT create/decode
  logging_context.py user id on every log line
  seed.py            create officer and customer logins
  dependencies/      current user, role checks
  routers/           HTTP layer
  services/          business rules and ownership checks
  repositories/      database queries
  schemas/           Pydantic request/response models
alembic/versions/    migrations
tests/               pytest
postman/             end-to-end collection
```

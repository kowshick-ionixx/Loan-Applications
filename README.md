# Loan Application Service

A REST API for a small lending desk. Customers register, create a profile and apply for loans. The service checks each application against the eligibility rules, approves or rejects it, calculates the EMI, and gives a risk summary per customer. Loan officers can see and manage every customer and loan.

Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, **Alembic**, **JWT authentication**, **Docker** and **GitHub Actions**.

---

## Table of contents

1. [Tech stack](#1-tech-stack)
2. [Concepts used in this project](#2-concepts-used-in-this-project)
   - [2.1 Web and HTTP basics](#21-web-and-http-basics)
   - [2.2 FastAPI concepts](#22-fastapi-concepts)
   - [2.3 Python language features](#23-python-language-features)
   - [2.4 Data and validation (Pydantic)](#24-data-and-validation-pydantic)
   - [2.5 Configuration](#25-configuration)
   - [2.6 Database (PostgreSQL)](#26-database-postgresql)
   - [2.7 ORM and sessions (SQLAlchemy)](#27-orm-and-sessions-sqlalchemy)
   - [2.8 Transactions and concurrency](#28-transactions-and-concurrency)
   - [2.9 Migrations (Alembic)](#29-migrations-alembic)
   - [2.10 Architecture and error handling](#210-architecture-and-error-handling)
   - [2.11 Security](#211-security)
   - [2.12 Observability (logging)](#212-observability-logging)
   - [2.13 Lending domain (business terms)](#213-lending-domain-business-terms)
   - [2.14 Packaging and environments (uv)](#214-packaging-and-environments-uv)
   - [2.15 Docker and Docker Compose](#215-docker-and-docker-compose)
   - [2.16 Testing](#216-testing)
   - [2.17 Code quality, Git and CI](#217-code-quality-git-and-ci)
   - [2.18 Documentation](#218-documentation)
3. [How a request flows end to end](#3-how-a-request-flows-end-to-end)
4. [Project structure](#4-project-structure)
5. [Setup, end to end](#5-setup-end-to-end)
6. [Configuration (.env)](#6-configuration-env)
7. [How to use the API](#7-how-to-use-the-api)
8. [API reference](#8-api-reference)
9. [Business rules](#9-business-rules)
10. [Validation rules](#10-validation-rules)
11. [Errors](#11-errors)
12. [Testing](#12-testing)
13. [Code quality and CI](#13-code-quality-and-ci)
14. [Database](#14-database)
15. [Command cheat sheet](#15-command-cheat-sheet)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Tech stack

| Tool / library | Version | Used for |
|---|---|---|
| Python | 3.12 | Programming language |
| uv | 0.12 | Installs packages, manages the virtual environment, runs commands |
| FastAPI | 0.142+ | Web framework that builds the API endpoints |
| Uvicorn | 0.54+ | ASGI server that runs the FastAPI app |
| Pydantic | 2.x | Validates request data and shapes response data |
| pydantic-settings | 2.x | Reads settings from environment variables / `.env` |
| SQLAlchemy | 2.1+ | ORM: database tables as Python classes |
| psycopg | 3.x | PostgreSQL driver |
| PostgreSQL | 16 | The database |
| Alembic | 1.x | Database migrations (create and change tables) |
| PyJWT | 2.x | Creates and checks JWT access tokens |
| pwdlib (Argon2) | 0.3+ | Hashes passwords |
| python-multipart | — | Reads the login form body |
| pytest, httpx, pytest-cov | — | Tests and coverage |
| Ruff, black, pre-commit | — | Linting and formatting |
| Docker, Docker Compose | — | Runs PostgreSQL and the API in containers |
| GitHub Actions | — | CI: lint, tests and Docker build on every PR |

---

## 2. Concepts used in this project

Every concept has a **Definition** (what it means in general) and **In this project** (where and how it is used here). The groups go from the outside of the system (HTTP) to the inside (database), then to tooling (Docker, tests, CI).

### 2.1 Web and HTTP basics

**HTTP**
*Definition:* HyperText Transfer Protocol, the request/response protocol of the web. A client sends a *request* (method, URL, headers, optional body) and the server sends back a *response* (status code, headers, optional body).
*In this project:* Every interaction with the service is an HTTP request to `http://localhost:8000`.

**Client and server**
*Definition:* The client starts the conversation (browser, Postman, `curl`, a test); the server listens and answers.
*In this project:* The server is Uvicorn running FastAPI. Clients are Swagger UI, Postman, PowerShell `Invoke-RestMethod`, and the test suite's `TestClient`.

**REST API**
*Definition:* A style of web API where each URL names a *resource* (such as `/api/loans/5`) and the HTTP method says what to do with it.
*In this project:* Customers and loans are resources under `/api/...`; authentication lives under `/auth/...`.

**Resource and endpoint**
*Definition:* A resource is a "thing" the API exposes (a customer, a loan). An endpoint is one method + path combination that acts on it (`GET /api/loans/{loan_id}`).
*In this project:* 10 endpoints, listed in [API reference](#8-api-reference).

**HTTP methods**
*Definition:* The verb of a request. `GET` reads and never changes data; `POST` creates something new. (Others such as `PUT`, `PATCH` and `DELETE` exist but are not used here.)
*In this project:* `GET` for reading customers, loans and summaries; `POST` for register, login, creating a profile and applying for a loan.

**URL, path and path parameter**
*Definition:* The path is the part of the URL after the host (`/api/customers/7`). A path parameter is a variable piece of the path (`{customer_id}` → `7`).
*In this project:* `{customer_id}` and `{loan_id}` must be positive integers (`PositiveId` in `dependencies.py`); anything else is `400 VALIDATION_FAILED`.

**Query parameter**
*Definition:* Optional `key=value` pairs after `?` in the URL, used for filtering and paging.
*In this project:* `?status=APPROVED`, `?page=2&size=10` on the loan lists.

**Headers**
*Definition:* Key/value metadata sent with a request or response (`Content-Type`, `Authorization`, ...).
*In this project:* `Authorization: Bearer <token>` (who you are), `Content-Type` (body format), `X-Request-ID` (tracing), `X-Health-Probe` (marks Docker's health check), `WWW-Authenticate: Bearer` (sent back on every `401`).

**Request body and JSON**
*Definition:* The data sent with a `POST`. JSON (JavaScript Object Notation) is the text format `{"key": "value"}` that most APIs use.
*In this project:* Every body is JSON except the login body.

**Content-Type: `application/json` vs `application/x-www-form-urlencoded`**
*Definition:* `Content-Type` tells the server how the body is encoded. JSON looks like `{"username": "a"}`; a URL-encoded form looks like `username=a&password=b` (what an HTML form sends).
*In this project:* `POST /auth/login` takes a **form** body because the OAuth2 standard requires it; `python-multipart` parses it. Everything else is JSON.

**HTTP status codes**
*Definition:* A three-digit number in every response: `2xx` success, `4xx` the client made a mistake, `5xx` the server failed.
*In this project:* `200` OK, `201` Created, `400` bad input, `401` not logged in, `403` logged in but not allowed, `404` not found, `409` conflict with existing data, `500` unexpected error.

**401 vs 403**
*Definition:* `401 Unauthorized` really means "unauthenticated" — the server doesn't know who you are. `403 Forbidden` means "I know who you are, and you may not do this."
*In this project:* No/expired/bad token → `401`. A customer asking for another customer's data → `403`.

**400 vs 422**
*Definition:* FastAPI's default for invalid input is `422 Unprocessable Entity`; many APIs use `400 Bad Request` instead.
*In this project:* All validation errors are `400` (see `exceptions.py`), and `main.py` removes the `422` entries from the generated docs.

**409 Conflict**
*Definition:* The request is valid but clashes with the current state of the data.
*In this project:* Duplicate username/email, a login that already has a profile, or a customer removed while the request was running.

**ASGI server (Uvicorn)**
*Definition:* ASGI (Asynchronous Server Gateway Interface) is the standard contract between a Python web app and a web server. Uvicorn is an ASGI server: it listens on a port, parses HTTP, and hands each request to the app.
*In this project:* `uvicorn loan_application.main:app --host 0.0.0.0 --port 8000` in Docker; `fastapi dev` (which uses Uvicorn with auto-reload) locally.

**Host `0.0.0.0` vs `localhost`**
*Definition:* `localhost` (127.0.0.1) only accepts connections from the same machine. `0.0.0.0` means "listen on every network interface".
*In this project:* Inside the container the API listens on `0.0.0.0` so Docker can forward your machine's port 8000 into it.

**Port**
*Definition:* A number that identifies one listening program on a machine.
*In this project:* API on `8000`; PostgreSQL on `5432` inside Docker, published as `5433` on your machine (so it does not clash with a locally installed PostgreSQL).

### 2.2 FastAPI concepts

**FastAPI**
*Definition:* A Python web framework. You write functions with type hints; FastAPI turns them into endpoints, validates the input, serialises the output, and generates API docs automatically.
*In this project:* `main.py` creates `app = FastAPI(...)`; `routers/` holds the endpoints.

**Path operation (endpoint function)**
*Definition:* A function decorated with `@router.get(...)` / `@router.post(...)`. Its parameters declare what it needs (body, path params, query params, dependencies).
*In this project:* e.g. `apply_for_loan(data: LoanCreate, db: DbSession, user: ProfileUser)` in `routers/loans.py`.

**Router (`APIRouter`)**
*Definition:* A group of related endpoints with a shared prefix and tags, added to the app with `include_router`.
*In this project:* `routers/auth.py` (`/auth`), `routers/customers.py` (`/api/customers`) and `routers/loans.py`.

**Tags**
*Definition:* Labels that group endpoints in the docs.
*In this project:* "Authentication", "Customers", "Loans".

**`response_model` and `status_code`**
*Definition:* `response_model` is the schema the return value is converted to (extra fields are dropped). `status_code` is the code sent on success.
*In this project:* e.g. `response_model=LoanOut, status_code=201`. The ORM object is returned, and FastAPI converts it to `LoanOut`, so internal columns such as `password_hash` can never leak.

**`responses=` (documented errors)**
*Definition:* Extra status codes and their body shapes, shown in the docs.
*In this project:* `PROTECTED_RESPONSES` in `schemas/common.py` documents `400/401/403` for every protected router.

**Dependency injection (`Depends`)**
*Definition:* Instead of an endpoint creating what it needs, it declares it, and FastAPI calls the provider for each request and passes the result in. Dependencies can depend on other dependencies.
*In this project:*
- `DbSession` → `get_db()` opens a database session per request and closes it afterwards.
- `CurrentUser` → `get_current_user()` reads the bearer token, decodes it and loads the user.
- `ProfileUser` → `require_customer_profile()` builds on `CurrentUser` and also requires a customer profile for CUSTOMER logins.

**Dependency override**
*Definition:* Replacing a dependency with a different one, usually in tests.
*In this project:* `tests/conftest.py` sets `app.dependency_overrides[get_db] = lambda: db` so every request uses the test's rolled-back session.

**Middleware**
*Definition:* Code that runs around *every* request, before the endpoint and after it.
*In this project:* `request_context` in `main.py` assigns a request ID, times the request, logs one line, adds `X-Request-ID` to the response, and turns any unhandled crash into a clean `500 INTERNAL_ERROR`.

**Exception handler**
*Definition:* A function registered with the app that converts a specific exception type into an HTTP response.
*In this project:* `main.py` registers handlers for `AppError`, `HTTPException` and `RequestValidationError` (all in `exceptions.py`).

**`OAuth2PasswordBearer` and `OAuth2PasswordRequestForm`**
*Definition:* FastAPI helpers. The first reads `Authorization: Bearer <token>` from a request; the second parses the `username`/`password` login form.
*In this project:* `oauth2_scheme` in `dependencies.py` (with `auto_error=False`, so the app raises its own `401` format) and the `login()` endpoint in `routers/auth.py`.

**Sync vs async endpoints**
*Definition:* FastAPI runs `async def` functions on its event loop and plain `def` functions in a thread pool, so blocking code (like database calls) does not freeze the server.
*In this project:* Endpoints that use the (blocking) database are plain `def`; small dependencies and the middleware are `async def`.

**Health check**
*Definition:* A simple endpoint that a monitor (Docker, a load balancer) calls to decide whether the app is alive.
*In this project:* `GET /health` runs `SELECT 1` against the database and returns `{"status": "ok"}`.

### 2.3 Python language features

**Package, module and `src/` layout**
*Definition:* A module is one `.py` file; a package is a folder of modules with an `__init__.py`. The `src/` layout puts the package under `src/`, so tests always use the *installed* package, not files that happen to be in the current folder.
*In this project:* The package is `src/loan_application/`, installed into `.venv` by `uv sync`.

**`python -m`**
*Definition:* Runs a module inside a package as a script.
*In this project:* `python -m loan_application.scripts.seed`.

**Type hints**
*Definition:* Annotations such as `amount: Decimal` or `-> Loan` that state the expected types. Python does not enforce them at runtime, but FastAPI, Pydantic and SQLAlchemy read them to validate and map data.
*In this project:* Used everywhere; they drive validation, the ORM columns (`Mapped[int]`) and the docs.

**`Annotated`**
*Definition:* Attaches extra metadata to a type: `Annotated[int, Path(gt=0)]` is "an int, and also must be > 0 when it comes from the path".
*In this project:* `PositiveId`, `DbSession`, `CurrentUser`, `ProfileUser`, and the reusable field types `Name`, `Email`, `Phone`, `Income`, `Username`, `Password`.

**`Literal`**
*Definition:* A type that only allows the listed values.
*In this project:* `Literal[12, 24, 36, 48, 60]` for tenure, `Literal["APPROVED", "REJECTED"]` for status, `Literal["LOW", "MEDIUM", "HIGH"]` for risk band.

**Optional values (`X | None`)**
*Definition:* The value may be `X` or `None`.
*In this project:* e.g. `address: str | None`, `emi: Decimal | None` (no EMI on a rejected loan).

**Generic class (`class Page[T]`)**
*Definition:* A class written once that works for any item type `T` (Python 3.12 syntax).
*In this project:* `Page[T]` in `schemas/common.py`; `LoanPage = Page[LoanOut]`.

**`type` alias statement**
*Definition:* Python 3.12's way to name a type: `type DbSession = Annotated[...]`.
*In this project:* `DbSession` in `db.py`.

**Decorator**
*Definition:* `@something` above a function wraps or registers it.
*In this project:* `@router.get`, `@app.middleware("http")`, `@contextmanager`, `@pytest.fixture`, `@computed_field`.

**Generator and `yield`**
*Definition:* A function with `yield` pauses, hands a value out, and resumes later. FastAPI and pytest use this for "set up → hand over → clean up".
*In this project:* `get_db()` yields a session and closes it in `finally`; fixtures in `conftest.py` yield and then roll back.

**Context manager (`with`)**
*Definition:* An object that runs setup code when a `with` block starts and cleanup code when it ends, even if an error happens. `@contextmanager` builds one from a generator.
*In this project:* `with transaction(db, ...):` in every service write; `with SessionLocal() as db:` in the seed script.

**Exceptions and custom exception classes**
*Definition:* `raise` stops normal flow and jumps to the nearest handler. Your own subclasses of `Exception` can carry extra data.
*In this project:* `AppError(status_code, error, message)` and subclasses in `exceptions.py`.

**`Decimal`**
*Definition:* `float` stores numbers in binary and cannot represent 0.1 exactly (`0.1 + 0.2 != 0.3`). `Decimal` stores decimal digits exactly, which is required for money.
*In this project:* Amounts, income, rates and EMI are `Decimal` in Python and `NUMERIC` in PostgreSQL. They become JSON numbers only in the response models.

**`ContextVar`**
*Definition:* A variable whose value is separate for each request/task, even when many run at the same time.
*In this project:* `request_id_var` and `user_id_var` in `logging_config.py`; the log filter reads them so every log line shows which request and user it belongs to.

**`getpass`**
*Definition:* Reads a password from the terminal without echoing it.
*In this project:* The seed script asks for the officer password this way when `SEED_OFFICER_PASSWORD` is empty.

### 2.4 Data and validation (Pydantic)

**Pydantic model / schema (DTO)**
*Definition:* A class (subclass of `BaseModel`) that describes the shape of data. Pydantic checks incoming data against it and converts it to the right types. DTO = Data Transfer Object: the shape data has when it crosses the API boundary.
*In this project:* `schemas/` — input models `RegisterRequest`, `CustomerCreate`, `LoanCreate`; output models `UserOut`, `TokenResponse`, `CustomerOut`, `CustomerSummary`, `LoanOut`, `LoanPage`, `ErrorResponse`, `ValidationErrorResponse`.

**Schema vs model**
*Definition:* In this codebase a *schema* (Pydantic) is the API shape, and a *model* (SQLAlchemy) is the database table. They are kept separate on purpose.
*In this project:* `CustomerCreate` (what a client may send) ≠ `Customer` in `models.py` (what is stored).

**Input validation**
*Definition:* Rejecting bad data at the edge of the system, before it reaches business logic or the database.
*In this project:* A failure returns `400 VALIDATION_FAILED` with one friendly message per field (`FIELD_MESSAGES` in `exceptions.py`).

**Field constraints (`Field(...)`)**
*Definition:* Rules on a field: `gt`/`ge`/`le` (number bounds), `min_length`/`max_length`, `pattern` (regex), `max_digits`/`decimal_places`.
*In this project:* e.g. `amount: Decimal = Field(ge=10000, le=5000000, decimal_places=2)`.

**Regular expression (regex)**
*Definition:* A pattern language for text. `^[0-9]{10}$` means "exactly ten digits, nothing else".
*In this project:* Phone, name and username patterns — in Pydantic, and again as CHECK constraints in the database.

**Special types: `EmailStr`, `PastDate`**
*Definition:* Ready-made Pydantic types. `EmailStr` checks the email format; `PastDate` accepts only dates before today.
*In this project:* `email` and `date_of_birth` on `CustomerCreate`.

**Normalisation (`AfterValidator`)**
*Definition:* Transforming a value after it passes validation, so equal values are stored the same way.
*In this project:* Emails and usernames are lowercased, so `Arjun@X.com` and `arjun@x.com` count as the same.

**Strict mode**
*Definition:* By default Pydantic converts `"5"` to `5`. `strict=True` rejects anything that isn't already the exact type.
*In this project:* `LoanCreate.customer_id` is strict, so `"1"` or `1.0` is rejected.

**`from_attributes` (ORM mode)**
*Definition:* Lets a Pydantic model read its fields from an object's attributes (an ORM row) instead of a dict.
*In this project:* `CustomerOut`, `LoanOut` and `UserOut` set `ConfigDict(from_attributes=True)`.

**`computed_field`**
*Definition:* An output field calculated from other fields rather than stored.
*In this project:* `UserOut.has_customer_profile` is `customer_id is not None`.

**`exclude=True`**
*Definition:* The field is accepted as input but left out when the model is dumped.
*In this project:* `CustomerCreate.username` is used only to choose which login to link, and is not passed to the `Customer` table.

**Mass-assignment protection**
*Definition:* Never let a client set fields it should not control just by adding them to the body.
*In this project:* `RegisterRequest` has only `username` and `password`; a `"role": "OFFICER"` in the body is ignored, so nobody can register as an officer.

**Serialization**
*Definition:* Converting Python objects to JSON for the response.
*In this project:* Response models declare money fields as `float`, so the JSON has plain numbers (`9964.29`).

### 2.5 Configuration

**Environment variable**
*Definition:* A named value set in the operating system or container (`DATABASE_URL=...`) that a program reads at start-up.
*In this project:* All settings come from environment variables.

**`.env` file**
*Definition:* A local text file of `KEY=value` lines that tools load as environment variables. It holds secrets, so it is never committed.
*In this project:* Copied from `.env.example`; listed in `.gitignore` and `.dockerignore`. Docker Compose also reads it to fill `${...}` in `docker-compose.yml`.

**pydantic-settings**
*Definition:* A Pydantic model that fills itself from environment variables (and `.env`) and validates them at start-up.
*In this project:* `Settings` in `config.py`. A missing `DATABASE_URL` or a `JWT_SECRET_KEY` shorter than 32 characters stops the app immediately with a clear error. `.env` is read from the **current folder**, so run commands from the project root.

**Secrets management**
*Definition:* Passwords and keys are never written in code or committed; they are injected at runtime.
*In this project:* `.env` locally, Compose environment in Docker, and a fresh random `JWT_SECRET_KEY` on every CI run.

**Twelve-factor config**
*Definition:* A widely used rule: the same build runs in every environment, and only the environment variables change.
*In this project:* The same Docker image runs locally and anywhere else; only `DATABASE_URL`, `JWT_SECRET_KEY`, etc. differ.

### 2.6 Database (PostgreSQL)

**Relational database / PostgreSQL**
*Definition:* Stores data in tables of rows and columns, linked by keys, and queried with SQL. PostgreSQL is an open-source relational database.
*In this project:* Three tables — `customers`, `loans`, `users` — in the database `app_db` (and `app_db_test` for tests).

**SQL**
*Definition:* Structured Query Language: `SELECT` reads, `INSERT` adds, `UPDATE` changes, `DELETE` removes.
*In this project:* SQLAlchemy generates almost all SQL; the only hand-written query is `SELECT 1` in `/health`.

**Table, row, column**
*Definition:* A table is one kind of record; a row is one record; a column is one attribute with a type.
*In this project:* e.g. one row in `loans` is one application with columns `amount`, `tenure_months`, `status`, ...

**Database schema (two meanings)**
*Definition:* (1) The structure of the database — tables, columns, constraints. (2) In PostgreSQL, a *namespace* that holds tables; the default one is `public`.
*In this project:* Migrations build meaning (1). The tests reset meaning (2) with `DROP SCHEMA public CASCADE`.

**Column types**
*Definition:* `INTEGER`, `VARCHAR(n)` (text up to n characters), `NUMERIC(p, s)` (exact decimal with p digits, s after the point), `DATE`, `TIMESTAMP WITH TIME ZONE`, `BOOLEAN`.
*In this project:* Money is `NUMERIC(12, 2)` (up to 9,999,999,999.99); interest rate is `NUMERIC(5, 2)`; `created_at` is timezone-aware.

**NULL**
*Definition:* "No value". Different from `0` or an empty string.
*In this project:* `emi` and `interest_rate` can be NULL on a rejected loan; `users.customer_id` is NULL for officers and for customers without a profile.

**Server default**
*Definition:* A value the database fills in when the insert does not provide one.
*In this project:* `created_at` defaults to `now()`, `applied_on` to `current_date`, `is_active` to `true`.

**Primary key (PK)**
*Definition:* A column that uniquely identifies each row; usually an auto-incrementing integer.
*In this project:* `id` on every table.

**Foreign key (FK)**
*Definition:* A column that must point to an existing row in another table.
*In this project:* `loans.customer_id → customers.id`, `users.customer_id → customers.id`.

**`ON DELETE SET NULL`**
*Definition:* A foreign-key rule: when the referenced row is deleted, set the pointer to NULL instead of failing.
*In this project:* If a customer row is deleted, the linked login survives with `customer_id = NULL` (it then gets `403 CUSTOMER_PROFILE_REQUIRED`).

**Unique constraint**
*Definition:* No two rows can have the same value in that column.
*In this project:* `customers.email`, `users.username`, `users.customer_id` (one login per profile).

**CHECK constraint**
*Definition:* A condition every row must satisfy, enforced by the database.
*In this project:* Name length/letters, 10-digit phone, positive income, amount range, allowed tenures, allowed status, allowed role, and consistency rules such as "an APPROVED loan has an EMI and no rejection reason" and "only CUSTOMER logins may link to a customer".

**Defence in depth**
*Definition:* Checking the same rule in more than one layer, so a bug in one layer cannot corrupt data.
*In this project:* Rules are checked by Pydantic (friendly `400`), by the services, and again by database constraints (last line of defence).

**Index**
*Definition:* A lookup structure that makes searches on a column fast, like a book index.
*In this project:* `customers.email`, `users.username` and `loans.customer_id` are indexed.

**Connection URL**
*Definition:* One string with everything needed to connect: `driver://user:password@host:port/database`.
*In this project:* `postgresql+psycopg://kowshick:<pw>@localhost:5433/app_db` — `+psycopg` tells SQLAlchemy to use the psycopg 3 driver.

**Database driver (psycopg)**
*Definition:* The library that speaks PostgreSQL's network protocol for Python.
*In this project:* `psycopg[binary]` 3.x.

**`LIMIT` / `OFFSET` and `COUNT(*)`**
*Definition:* `LIMIT n` returns at most n rows; `OFFSET k` skips the first k; `COUNT(*)` counts matching rows.
*In this project:* `GET /api/loans` uses `OFFSET (page-1)*size LIMIT size` plus one `COUNT(*)` for `total`.

### 2.7 ORM and sessions (SQLAlchemy)

**ORM (Object-Relational Mapper)**
*Definition:* Lets you work with tables as Python classes and rows as objects, and generates the SQL for you.
*In this project:* `models.py` defines `Customer`, `Loan` and `User`.

**Declarative model, `Mapped` and `mapped_column`**
*Definition:* A class that inherits from `Base`; each `Mapped[...]` attribute becomes a column, and `mapped_column(...)` adds details (type, key, default).
*In this project:* e.g. `amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))`.

**`Base` and metadata**
*Definition:* The parent class of all models. `Base.metadata` is the collected description of every table.
*In this project:* `Base` in `db.py`; Alembic reads `Base.metadata` to compare models with the database.

**Engine and connection pool**
*Definition:* The engine knows how to reach the database and keeps a pool of open connections to reuse, because opening one is slow.
*In this project:* `engine = create_engine(DATABASE_URL)` in `db.py`.

**Session and `sessionmaker`**
*Definition:* A session is SQLAlchemy's workspace for one conversation with the database: it tracks objects you load or change and sends the SQL when you flush or commit. `sessionmaker` is a factory for sessions.
*In this project:* `SessionLocal = sessionmaker(bind=engine)`; `get_db()` opens one session per request and always closes it.

**`add`, `flush`, `commit`, `refresh`, `rollback`**
*Definition:* `add` registers a new object; `flush` sends pending SQL now (inside the transaction, e.g. to get the new `id`) without making it permanent; `commit` makes it permanent; `refresh` reloads an object from the database; `rollback` undoes everything since the transaction began.
*In this project:* Repositories only `add` + `flush`. Services `commit` (via `transaction()`).

**`select()`, `db.get()`, `scalar`, `scalars`**
*Definition:* `select(Model).where(...)` builds a query; `db.get(Model, id)` loads by primary key; `scalar` returns one value or object; `scalars` returns many.
*In this project:* All in `repositories/`.

**`IntegrityError`**
*Definition:* The error SQLAlchemy raises when the database rejects a write because of a constraint (unique, FK, CHECK).
*In this project:* `transaction()` turns it into a `409` with a meaningful code (e.g. `DUPLICATE_EMAIL`).

### 2.8 Transactions and concurrency

**Transaction**
*Definition:* A group of database changes that either all succeed (commit) or all fail (rollback). Properties summarised as ACID: Atomic, Consistent, Isolated, Durable.
*In this project:* Each service operation is one transaction.

**Unit of work**
*Definition:* The pattern of collecting all changes of one business operation and committing them together once at the end.
*In this project:* `transaction()` in `db.py`. Services decide where the transaction starts and ends; repositories only `flush()`; routers never commit. Any exception rolls everything back.

**Race condition**
*Definition:* A bug where the result depends on the timing of two things running at once. Classic example: two requests both read "1 active loan", both decide "OK, under the limit of 2", both insert → 3 loans.
*In this project:* Prevented with a row lock (next entry).

**Row locking (`SELECT ... FOR UPDATE`)**
*Definition:* Locks the selected rows until the transaction ends; any other transaction that wants the same lock waits.
*In this project:* `apply_for_loan` loads the customer with `lock=True`. Two applications for the same customer run one after the other, so the second sees the first one's approval. `test_transactions.py` proves it with two threads.

**Savepoint**
*Definition:* A bookmark inside a transaction; you can roll back to it without ending the outer transaction.
*In this project:* Tests open a session with `join_transaction_mode="create_savepoint"`, so even when app code calls `commit()`, it only commits a savepoint, and the outer transaction is rolled back at the end of the test.

### 2.9 Migrations (Alembic)

**Migration**
*Definition:* A versioned script that changes the database structure one step at a time, so every database (dev, test, Docker, CI) ends up identical.
*In this project:* 7 scripts in `alembic/versions/`: create customers, add CHECK constraints, create loans, create users, allow self-registered customers, FK `SET NULL`, add address.

**Revision, `upgrade()` / `downgrade()`**
*Definition:* Each migration is a *revision* with an id and a pointer to the previous one. `upgrade()` applies the change; `downgrade()` undoes it.
*In this project:* Each file in `alembic/versions/` has both functions.

**Head**
*Definition:* The newest revision. `alembic upgrade head` applies everything up to it.
*In this project:* Run automatically by `docker/entrypoint.sh` and by the test setup.

**Autogenerate**
*Definition:* Alembic compares `Base.metadata` with the live database and drafts a migration for the differences.
*In this project:* `alembic revision --autogenerate -m "..."`. It does not detect CHECK constraints, so add those by hand. A post-write hook in `alembic.ini` runs Ruff on new files.

**`alembic.ini` and `env.py`**
*Definition:* `alembic.ini` is Alembic's config file; `env.py` connects to the database and runs the migrations.
*In this project:* `env.py` takes the URL from `loan_application.db`, so Alembic always uses the same `DATABASE_URL` as the app.

### 2.10 Architecture and error handling

**Layered architecture / separation of concerns**
*Definition:* The code is split into layers, each with one job, and each layer only calls the layer below it. Changing one concern (e.g. SQL) does not ripple through the rest.

```
Router  →  Service  →  Repository  →  Database
(HTTP)     (rules)      (SQL)
```

| Layer | Folder | Job |
|---|---|---|
| Router | `routers/` | Receives the request, calls the service, returns the response. No logic. |
| Service | `services/` | Business rules: eligibility, EMI, ownership, transactions, errors. |
| Repository | `repositories/` | The only code that queries the database. |
| Schema | `schemas/` | Input and output shapes, plus validation. |
| Model | `models.py` | Table definitions. |

**Repository pattern**
*Definition:* All data access for one table lives behind small functions (`get_by_id`, `add`, `count`), so the rest of the code never builds queries.
*In this project:* `customer_repository.py`, `loan_repository.py`, `user_repository.py`.

**Service layer**
*Definition:* Where the business decisions live, independent of HTTP.
*In this project:* `auth_service.py` (register, login), `customer_service.py` (create profile, ownership), `loan_service.py` (eligibility, EMI, risk, listing).

**Custom exceptions and error codes**
*Definition:* Your own error classes carrying a status code and a stable machine-readable code, raised anywhere and turned into a response in one place.
*In this project:* `AppError` and subclasses (`UnauthorizedError`, `InvalidCredentialsError`, `ForbiddenError`, `ProfileRequiredError`, `NotFoundError`, `DuplicateUsernameError`). Clients should branch on the `error` code (`NOT_FOUND`), not on the message text.

**Consistent error body**
*Definition:* Every error has the same JSON shape, so clients handle them in one place.
*In this project:* `{"error", "message", "request_id"}`, or `{"error", "details", "request_id"}` for validation. See [Errors](#11-errors).

**Token checked before body**
*Definition:* FastAPI parses the body before running dependencies, so a broken body would normally answer `400` even to a caller who is not logged in.
*In this project:* `check_token_before_body()` makes sure an unauthenticated caller always gets `401` first, revealing nothing about validation.

### 2.11 Security

**Authentication (authn)**
*Definition:* Proving *who* you are.
*In this project:* Username + password at `POST /auth/login` → a JWT.

**Authorization (authz)**
*Definition:* Deciding *what* you may do once the app knows who you are.
*In this project:* Roles (OFFICER / CUSTOMER) plus ownership checks.

**Password hashing, salt and Argon2**
*Definition:* A hash is a one-way transformation: you can check a password against it but cannot reverse it. A *salt* is random data mixed in per password, so two users with the same password get different hashes. Argon2 is a modern, deliberately slow, memory-hard algorithm that makes guessing expensive.
*In this project:* `pwdlib` with Argon2 (`PasswordHash.recommended()`) in `security.py`. Only `password_hash` is stored; the salt is inside the hash string.

**Timing attack and user enumeration**
*Definition:* If "unknown user" answers faster than "wrong password", an attacker can measure the time to learn which usernames exist (enumeration).
*In this project:* `authenticate_user()` verifies against `DUMMY_HASH` when the user does not exist, and both failures return the same `401 INVALID_CREDENTIALS`.

**JWT (JSON Web Token)**
*Definition:* A compact token in three base64url parts, `header.payload.signature`. The payload holds *claims*; the signature proves the server issued it and nobody changed it. Anyone can *read* a JWT, so it must never contain secrets.
*In this project:* Created in `security.py`; the reasons for choosing JWT over sessions are in [docs/adr/0001-jwt-vs-session-auth.md](docs/adr/0001-jwt-vs-session-auth.md).

**Claims (`sub`, `role`, `iat`, `exp`)**
*Definition:* Standard fields in a JWT payload: `sub` subject (who), `iat` issued-at time, `exp` expiry time. `role` is a custom claim.
*In this project:* `sub` = user id, `exp` = 30 minutes after `iat`. Decoding requires `exp` and `sub`.

**HS256 / HMAC signature and the secret key**
*Definition:* HS256 = HMAC with SHA-256: the server signs and verifies with the same secret. Whoever knows the secret can create valid tokens.
*In this project:* `JWT_SECRET_KEY` (≥ 32 characters, enforced by `config.py`). Changing it logs everyone out.

**Stateless authentication**
*Definition:* The server stores no session; each request carries its own proof (the token).
*In this project:* Any API container can verify any token. The user is still reloaded from the database on every request, so a deactivated user (`is_active = false`) is locked out at once. A token cannot be revoked early; logout is client-side.

**Token expiry**
*Definition:* A token stops working after `exp`, limiting the damage if it leaks.
*In this project:* 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`); an expired token → `401 "Token has expired"`.

**OAuth2 password flow / Bearer token**
*Definition:* A standard login: send `username` and `password` as a form, receive `{access_token, token_type: "bearer"}`, then send `Authorization: Bearer <token>` on every request. "Bearer" means "whoever holds this token is treated as the user".
*In this project:* `POST /auth/login`. It also makes the **Authorize** button work in Swagger.

**Role-based access control (RBAC)**
*Definition:* What a user may do depends on their role.
*In this project:* **OFFICER** sees and acts on everything. **CUSTOMER** only acts on their own profile and loans.

**Ownership check and IDOR**
*Definition:* IDOR (Insecure Direct Object Reference) is when changing an id in the URL lets you see someone else's data. An ownership check stops it.
*In this project:* `check_owner()` in `customer_service.py`. A customer asking for another id gets `403` — even if that id does not exist — so customers cannot probe which ids exist.

**Least privilege**
*Definition:* Give each component only the permissions it needs.
*In this project:* The Docker image runs as a non-root user `app`; customers are limited to their own data; registration can only create CUSTOMER logins.

**CSRF**
*Definition:* Cross-Site Request Forgery tricks a browser into sending a request with the victim's cookies.
*In this project:* Not applicable: no cookies are used; the token is sent explicitly in a header.

### 2.12 Observability (logging)

**Logging and log levels**
*Definition:* Writing events to an output stream. Levels mark severity: `DEBUG` < `INFO` < `WARNING` < `ERROR`.
*In this project:* `INFO` for each request and each loan decision, `WARNING` for client errors (4xx), `ERROR` with the stack trace for crashes (5xx).

**Request ID / correlation ID**
*Definition:* A unique id attached to one request and to every log line written while handling it, so one request can be traced through the logs.
*In this project:* Taken from the incoming `X-Request-ID` header or generated (`uuid4`). Returned in the `X-Request-ID` response header and in every error body.

**Structured logging**
*Definition:* Log lines with fixed fields (time, level, request id, user id), optionally as JSON so log tools can search them.
*In this project:* `logging_config.py`. `LOG_FORMAT=text` → readable lines with a coloured status (colour only when writing to a terminal); `LOG_FORMAT=json` → one JSON object per line. Passwords and tokens are never logged.

**Log filter and formatter**
*Definition:* A filter adds or drops data on each log record; a formatter turns the record into text.
*In this project:* `LogContextFilter` adds `request_id`/`user_id` from the `ContextVar`s; `JsonFormatter` / `TEXT_FORMATTER` print them.

**Latency measurement**
*Definition:* How long the server took to answer.
*In this project:* The middleware measures with `time.perf_counter()` and logs e.g. `GET /api/loans -> 200 (12.4 ms)`.

**Noise suppression**
*Definition:* Not logging events that carry no information.
*In this project:* Successful Docker health checks (marked with `X-Health-Probe`) are not logged; Uvicorn's own access log is disabled so each request is logged once.

### 2.13 Lending domain (business terms)

**Loan, principal (P)**
*Definition:* Money lent now and paid back with interest. The principal is the amount borrowed.
*In this project:* `amount`, ₹10,000 – ₹50,00,000.

**Tenure (n)**
*Definition:* How many months the loan runs.
*In this project:* 12, 24, 36, 48 or 60 months.

**Interest rate (annual and monthly)**
*Definition:* The yearly cost of borrowing as a percentage. The monthly rate `r` is the annual rate ÷ 12 ÷ 100.
*In this project:* Fixed by tenure (10%–13%), see [Business rules](#9-business-rules).

**EMI (Equated Monthly Instalment)**
*Definition:* The fixed amount paid every month so the loan and its interest are fully repaid by the end of the tenure (a reducing-balance / amortising loan).
*In this project:* `calculate_emi()` in `loan_service.py`; `EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)`.

**Rounding half-up**
*Definition:* Round to the nearest value; exactly halfway goes up (2.345 → 2.35). Python's default for `Decimal` is "half-even" (banker's rounding), which differs.
*In this project:* EMI and the EMI/income ratio use `ROUND_HALF_UP` to 2 decimals.

**Eligibility rules**
*Definition:* Conditions an applicant must meet to be approved.
*In this project:* Age 21–60, amount ≤ 20 × monthly income, fewer than 2 approved loans. The first failing rule becomes the `rejection_reason`.

**Age calculation**
*Definition:* Completed years: subtract birth year from current year, minus one if this year's birthday hasn't happened yet.
*In this project:* `calculate_age()`; "today" is the server's local date.

**Active loan**
*Definition:* A loan the customer is still repaying.
*In this project:* Every `APPROVED` loan counts as active (there is no closure flow yet).

**Approved vs rejected application**
*Definition:* The decision on an application.
*In this project:* Both are saved and both return `201`; a rejected loan has `rejection_reason` and no EMI.

**EMI-to-income ratio and risk band**
*Definition:* The share of monthly income already committed to EMIs. Lenders use it to judge how stretched a borrower is.
*In this project:* `total approved EMI / monthly income × 100`; below 30 → LOW, 30–50 → MEDIUM, above 50 → HIGH.

**Indian number format**
*Definition:* Groups digits as lakh (1,00,000) and crore (1,00,00,000).
*In this project:* Used in this README: ₹50,00,000 = 5,000,000.

### 2.14 Packaging and environments (uv)

**Virtual environment (`.venv`)**
*Definition:* An isolated folder with its own Python packages for one project, so projects don't break each other.
*In this project:* `.venv/`, created and managed by uv. Git- and Docker-ignored.

**`pyproject.toml`**
*Definition:* The standard file that describes a Python project: name, Python version, dependencies, tool settings.
*In this project:* Lists runtime dependencies, a `dev` dependency group (pytest, Ruff, black, pre-commit, ...), the build backend, and Ruff/pytest settings.

**Lock file (`uv.lock`)**
*Definition:* Pins the exact version of every package, including indirect ones, so every machine installs the same set.
*In this project:* `uv sync --locked` (CI and Docker) fails if `uv.lock` is out of date with `pyproject.toml`.

**uv**
*Definition:* A fast Python package and project manager: creates the venv, installs packages, can even install Python, and runs commands inside the environment.
*In this project:* `uv sync` installs everything; `uv run <cmd>` runs a command inside `.venv` without activating it.

**Dependency group (`dev`)**
*Definition:* Packages needed only for development, not to run the app.
*In this project:* Installed by `uv sync`; skipped in the Docker image with `--no-dev`.

**Build backend**
*Definition:* The tool that turns the project into an installable package.
*In this project:* `uv_build`.

**Extras (`package[extra]`)**
*Definition:* Optional add-ons of a package.
*In this project:* `fastapi[standard]` (CLI + Uvicorn), `psycopg[binary]` (pre-built driver), `pwdlib[argon2]`, `pydantic[email]`.

### 2.15 Docker and Docker Compose

**Container and image**
*Definition:* An image is a read-only package of an app plus everything it needs (OS files, Python, libraries). A container is a running instance of an image, isolated from your machine.
*In this project:* The `Dockerfile` builds the API image; PostgreSQL runs from the official `postgres:16` image.

**Dockerfile instructions**
*Definition:* `FROM` (base image), `WORKDIR` (folder), `COPY` (add files), `RUN` (run a command at build time), `ENV` (set variables), `USER` (who runs the app), `EXPOSE` (document the port), `HEALTHCHECK`, `ENTRYPOINT` + `CMD` (what runs at start).
*In this project:* All are used in the `Dockerfile`.

**Layer caching**
*Definition:* Each instruction creates a layer; Docker reuses a layer if its inputs did not change. Copying the dependency files before the source code means a code change doesn't reinstall every package.
*In this project:* `pyproject.toml` and `uv.lock` are copied and synced first, then `src/`.

**Multi-stage build**
*Definition:* A "build" stage installs things; a slim "runtime" stage copies only the result, so build tools don't end up in the final image.
*In this project:* `build` runs `uv sync`; `runtime` copies only `.venv`, `alembic/` and the entrypoint.

**`.dockerignore`**
*Definition:* Files Docker must never send into the build.
*In this project:* `.env` (secrets), `.git`, `.venv`, caches and `tests/`.

**`ENTRYPOINT` vs `CMD` and `exec "$@"`**
*Definition:* `ENTRYPOINT` always runs; `CMD` is the default arguments passed to it. `exec "$@"` in a shell script replaces the script with the given command, so that command receives stop signals directly.
*In this project:* `entrypoint.sh` runs migrations → seeds the officer → `exec uvicorn ...` (the `CMD`).

**Docker Compose and services**
*Definition:* A tool that starts several containers together from one YAML file; each container definition is a *service*.
*In this project:* `docker-compose.yml` has two services, `db` and `api`.

**Container network and service names**
*Definition:* Compose puts its services on a private network where each one is reachable by its service name.
*In this project:* Inside Docker the API connects to `db:5432`; from your machine you use `localhost:5433`.

**Port mapping (`"5433:5432"`)**
*Definition:* `host_port:container_port` — forwards a port on your machine into the container.
*In this project:* `8000:8000` for the API, `5433:5432` for PostgreSQL.

**Volume**
*Definition:* Storage managed by Docker that survives container removal.
*In this project:* `pgdata` holds the database files. `docker compose down` keeps it; `docker compose down -v` deletes all data.

**Init scripts (`/docker-entrypoint-initdb.d`)**
*Definition:* The `postgres` image runs SQL files from this folder **only the first time** it starts on an empty volume.
*In this project:* `docker/initdb/create-test-db.sql` creates `app_db_test`.

**Compose variable substitution**
*Definition:* `${VAR}` is filled from `.env`/your shell; `${VAR:-default}` uses a default; `${VAR:?message}` stops with an error if it's missing.
*In this project:* `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` are required (`:?`); the rest have defaults.

**`depends_on` with `condition: service_healthy`**
*Definition:* Start one service only after another reports healthy.
*In this project:* `api` waits for `db` to pass `pg_isready`.

**Container health check**
*Definition:* A command Docker runs regularly to mark a container `healthy` or `unhealthy`.
*In this project:* `pg_isready` for `db`; a Python call to `/health` (with `X-Health-Probe`) for `api`.

**Restart policy**
*Definition:* What Docker does when a container stops.
*In this project:* `api` uses `restart: unless-stopped`.

**Non-root user**
*Definition:* Running the app as a normal user inside the container limits damage if it is compromised.
*In this project:* `useradd ... app` and `USER app` in the `Dockerfile`.

**Seeding**
*Definition:* Inserting the starting data an app needs.
*In this project:* `scripts/seed.py` creates the first officer (`officer1`) or resets their password. Helper functions `create_customer_user()` and `link_customer_user()` manage customer logins.

### 2.16 Testing

**Automated tests (pytest)**
*Definition:* Code that checks the app behaves correctly, run with one command. pytest finds `test_*.py` files and runs every `test_*` function; a plain `assert` checks a condition.
*In this project:* 140 tests in `tests/`.

**Unit test vs integration test vs end-to-end test**
*Definition:* A unit test checks one function alone (fast). An integration test checks several parts together (API + database). An end-to-end test follows a whole user journey.
*In this project:* Unit: `calculate_emi`, `check_eligibility`, `get_risk_band`. Integration: every endpoint through `TestClient` with a real PostgreSQL. End-to-end: the "register → profile → apply → summary" journey tests.

**Fixture**
*Definition:* Reusable setup that pytest passes into a test by parameter name. `scope="session"` runs once per test run; `autouse=True` applies it without being asked for.
*In this project:* `tests/conftest.py` — `migrated_database` (session, autouse), `db`, `client`, `officer`, `signup`, `profileless`.

**`conftest.py`**
*Definition:* A file pytest loads automatically; fixtures and helpers in it are available to every test.
*In this project:* Also holds helpers `login()`, `register()`, `apply()`, `create()`, `error_of()`, `fields_of()`.

**Parametrize**
*Definition:* `@pytest.mark.parametrize` runs the same test with several inputs.
*In this project:* Used for boundary values (tenures, amounts, ages, invalid fields, ...), which is why 79 test functions become 140 tests.

**`TestClient`**
*Definition:* Calls the FastAPI app in-process, like a real HTTP client but without a network (built on httpx).
*In this project:* The `client` fixture.

**Test isolation**
*Definition:* Tests must not affect each other or your real data.
*In this project:* A separate `app_db_test` database (the run refuses to start if the name doesn't end in `_test`); each test runs in a transaction + savepoint that is rolled back afterwards.

**Concurrency test**
*Definition:* A test that runs code in parallel to prove there is no race condition.
*In this project:* `test_transactions.py` starts two threads applying for loans at once and checks the second waits for the first.

**Code coverage**
*Definition:* The percentage of code lines executed by the tests.
*In this project:* `pytest-cov`; currently 96%; CI fails below 80%.

### 2.17 Code quality, Git and CI

**Linter (Ruff)**
*Definition:* Reads code without running it to find likely bugs, unused imports and style problems.
*In this project:* `uv run ruff check .` (target Python 3.12).

**Formatter (black)**
*Definition:* Rewrites code into one consistent style, so reviews focus on logic.
*In this project:* `uv run black .`; CI runs `black --check`.

**pre-commit and Git hooks**
*Definition:* A Git hook is a script Git runs at a moment such as "before commit". pre-commit manages these hooks.
*In this project:* `.pre-commit-config.yaml` runs Ruff (with `--fix`) and black on every `git commit`, after `uv run pre-commit install`.

**Git, branch, commit, remote, pull request**
*Definition:* Git tracks changes. A commit is a saved snapshot; a branch is a line of work; a remote is a copy on a server (GitHub); a pull request (PR) asks to merge a branch, with review and CI.
*In this project:* Work happens on feature branches (e.g. `feature/week2-monday`) and is merged into `main` through PRs.

**`.gitignore`**
*Definition:* Files Git must never track.
*In this project:* `.env`, `.venv`, caches, coverage reports.

**Continuous Integration (CI)**
*Definition:* Every push or PR is automatically built and tested on a clean machine, so broken code is caught before it is merged.
*In this project:* `.github/workflows/ci.yml`.

**GitHub Actions: workflow, job, step, runner, action, service container**
*Definition:* A *workflow* is a YAML file triggered by events. It has *jobs* (run in parallel on fresh *runner* VMs), each made of *steps*. An *action* is a reusable step (`actions/checkout`). A *service container* is a sidecar such as a database for the job.
*In this project:* Three jobs — **Lint**, **Tests** (with a `postgres:16` service container) and **Docker build**. The test job writes a random `JWT_SECRET_KEY` into `$GITHUB_ENV`, which makes it available to later steps.

### 2.18 Documentation

**OpenAPI**
*Definition:* A standard, machine-readable (JSON/YAML) description of an API: paths, inputs, outputs, errors.
*In this project:* Generated automatically at `/openapi.json`; can be imported into Postman.

**Swagger UI and ReDoc**
*Definition:* Web pages that render the OpenAPI description. Swagger lets you try every endpoint; ReDoc is read-only.
*In this project:* `/docs` (Swagger) and `/redoc`.

**Docstrings**
*Definition:* The text in triple quotes at the top of a function.
*In this project:* Endpoint docstrings appear as descriptions in Swagger.

**ADR (Architecture Decision Record)**
*Definition:* A short document recording one important technical decision: context, decision, consequences.
*In this project:* [docs/adr/0001-jwt-vs-session-auth.md](docs/adr/0001-jwt-vs-session-auth.md).

---

## 3. How a request flows end to end

Example: a customer calls `POST /api/loans`.

```
Client ──HTTP──► Uvicorn ──► FastAPI app
                               │
  1. Middleware request_context: set request_id, start timer
  2. Routing: match POST /api/loans → apply_for_loan()
  3. Body parsing + validation: JSON → LoanCreate (bad → 400 VALIDATION_FAILED)
  4. Dependencies:
       get_db()                   → opens a Session
       get_current_user()         → reads Bearer token, decodes JWT, loads User (bad → 401)
       require_customer_profile() → CUSTOMER must have a profile (else 403)
  5. Router calls loan_service.apply_for_loan()
  6. Service, inside transaction():
       get_customer_for_user(lock=True) → ownership check (403) + SELECT ... FOR UPDATE (404)
       count approved loans → check_eligibility → rate → calculate_emi
       loan_repository.add() → INSERT + flush
       COMMIT (any error → ROLLBACK; IntegrityError → 409)
  7. Response model: Loan (ORM) → LoanOut → JSON, status 201
  8. get_db() closes the Session
  9. Middleware: log "POST /api/loans -> 201 (x ms)", add X-Request-ID header
                               │
Client ◄──────── 201 + JSON ───┘
```

Any `AppError` raised in steps 4–6 is caught by `app_error_handler` and becomes the standard error body.

---

## 4. Project structure

```
Loan-Applications/
├── src/loan_application/
│   ├── main.py                  # FastAPI app, middleware, error handlers, /health
│   ├── config.py                # Settings from environment / .env
│   ├── db.py                    # Engine, session, Base, transaction()
│   ├── models.py                # Customer, Loan, User tables
│   ├── security.py              # Password hashing, JWT create/decode
│   ├── dependencies.py          # CurrentUser, ProfileUser, PositiveId
│   ├── exceptions.py            # AppError classes + global error handlers
│   ├── logging_config.py        # Text/JSON logs with request_id and user_id
│   ├── routers/                 # auth.py, customers.py, loans.py
│   ├── services/                # auth_service.py, customer_service.py, loan_service.py
│   ├── repositories/            # customer_, loan_, user_repository.py
│   ├── schemas/                 # auth, common, customer, loan, user
│   └── scripts/seed.py          # Create / reset the first officer, link logins
├── alembic/                     # Migrations (env.py + versions/)
├── tests/                       # conftest.py + test_*.py
├── docker/
│   ├── entrypoint.sh            # migrate → seed → start server
│   └── initdb/create-test-db.sql  # creates app_db_test on first start
├── docs/adr/                    # Architecture decision records
├── .github/workflows/ci.yml     # CI pipeline
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml / uv.lock     # Dependencies
├── .env.example                 # Template for .env
└── .pre-commit-config.yaml
```

---

## 5. Setup, end to end

The steps below take a fresh Windows machine to a running API, a first officer login, a full customer journey, and a green test run. Commands are PowerShell; run them from the project folder unless stated otherwise.

### 5.1 Install the tools (one time)

| Tool | Why | Install (PowerShell) | Check |
|---|---|---|---|
| Git | Get the code | `winget install --id Git.Git -e` | `git --version` |
| Docker Desktop | Runs PostgreSQL (and the API) | `winget install --id Docker.DockerDesktop -e` | `docker --version` and `docker compose version` |
| uv | Python + packages | `winget install --id astral-sh.uv -e` | `uv --version` |
| Python 3.12 | Only for Option B | `uv python install 3.12` | `uv run python --version` |

Notes:
- **Docker Desktop** needs WSL 2 on Windows. If it asks, run `wsl --install` in an *administrator* PowerShell and restart. Start Docker Desktop and wait until it says *Engine running* before using `docker`.
- After installing, **open a new terminal** so the new commands are on your `PATH`.
- Optional: VS Code (editor), DBeaver (browse the database), Postman (call the API).

### 5.2 Get the code

```powershell
git clone https://github.com/kowshick-ionixx/Loan-Applications.git
cd Loan-Applications
```

### 5.3 Create `.env`

```powershell
copy .env.example .env
```

Generate two random values — one for `JWT_SECRET_KEY`, one you can use as a password:

```powershell
uv run --no-project python -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env` and replace **every** `change-me`:

| Line | Set it to |
|---|---|
| `POSTGRES_PASSWORD=` | A database password of your choice |
| `DATABASE_URL=` | The same password in place of `change-me`: `postgresql+psycopg://kowshick:<that password>@localhost:5433/app_db` |
| `JWT_SECRET_KEY=` | The 64-character hex string you just generated |
| `SEED_OFFICER_PASSWORD=` | The password `officer1` will log in with |

> `POSTGRES_PASSWORD` is only used the **first** time the database volume is created. If you change it later, also run `docker compose down -v` (this deletes the data) or change the password inside PostgreSQL.

Every variable is explained in [Configuration](#6-configuration-env).

### 5.4 Option A — run everything in Docker (easiest)

```powershell
docker compose up --build -d
docker compose ps
```

Wait until both services show `(healthy)` (about 20–30 seconds on the first run). What happened:

| Service | What it does |
|---|---|
| `db` | Starts PostgreSQL 16 on `localhost:5433`. On a brand-new volume it creates `app_db` and also `app_db_test` (for the tests). |
| `api` | Builds the image, waits for `db` to be healthy, runs `alembic upgrade head` (creates the tables), creates/resets `officer1` with `SEED_OFFICER_PASSWORD`, then starts Uvicorn on `http://localhost:8000`. |

Watch the start-up:

```powershell
docker compose logs -f api
```

You should see `Running database migrations...`, `OFFICER 'officer1' created (id=1)` and `Uvicorn running on http://0.0.0.0:8000`. Press `Ctrl+C` to stop following (the container keeps running).

### 5.5 Option B — run the API on your machine (for development)

Use this when you change code and want auto-reload. PostgreSQL still runs in Docker.

```powershell
docker compose stop api                            # free port 8000 if the Docker api is running
uv sync                                            # create .venv and install all packages (incl. dev tools)
docker compose up -d db                            # start only PostgreSQL
uv run alembic upgrade head                        # create / update the tables in app_db
uv run python -m loan_application.scripts.seed     # create or reset officer1
uv run fastapi dev src/loan_application/main.py    # start with auto-reload on http://localhost:8000
```

`uv run` runs the command inside `.venv`, so you never need to activate it. If you prefer to activate it: `.venv\Scripts\Activate.ps1`.

### 5.6 Check it works

| URL | Expected |
|---|---|
| http://localhost:8000/health | `{"status":"ok"}` |
| http://localhost:8000/docs | Swagger UI with Authentication, Customers and Loans |
| http://localhost:8000/redoc | Read-only API docs |
| http://localhost:8000/openapi.json | The OpenAPI spec |

```powershell
Invoke-RestMethod http://localhost:8000/health
```

### 5.7 First journey from PowerShell (register → profile → loan → summary)

Copy this block into PowerShell. It registers a customer, logs in, creates the profile, applies for a loan and shows the summary.

```powershell
$base = "http://localhost:8000"

# 1. Register a CUSTOMER login (JSON body)
Invoke-RestMethod -Method Post "$base/auth/register" -ContentType "application/json" `
  -Body '{"username": "arjun_ramesh", "password": "Arjun@1234"}'

# 2. Log in (form body) and keep the token
$login = Invoke-RestMethod -Method Post "$base/auth/login" `
  -Body @{ username = "arjun_ramesh"; password = "Arjun@1234" }
$auth = @{ Authorization = "Bearer $($login.access_token)" }

# 3. Create the customer profile (linked to this login)
$profile = @{
  name = "Arjun Ramesh"; email = "arjun.ramesh@example.com"; phone = "9876543210"
  date_of_birth = "1995-06-18"; monthly_income = 85000; address = "Chennai"
} | ConvertTo-Json
$me = Invoke-RestMethod -Method Post "$base/api/customers" -Headers $auth `
  -ContentType "application/json" -Body $profile

# 4. Apply for a loan
$loan = @{ customer_id = $me.id; amount = 300000; tenure_months = 36 } | ConvertTo-Json
Invoke-RestMethod -Method Post "$base/api/loans" -Headers $auth `
  -ContentType "application/json" -Body $loan

# 5. Summary and list
Invoke-RestMethod "$base/api/customers/$($me.id)/summary" -Headers $auth
Invoke-RestMethod "$base/api/loans?page=1&size=10" -Headers $auth
```

The loan comes back `APPROVED` with `emi = 9964.29`. Running the block a second time gives `409 DUPLICATE_USERNAME` at step 1 — change the username and email to try again.

To act as the officer, log in the same way with `officer1` and your `SEED_OFFICER_PASSWORD`; the officer sees every customer and loan.

### 5.8 Use Swagger or Postman instead

- **Swagger:** open http://localhost:8000/docs → **Authorize** → enter username and password → **Authorize**. Every request you try now sends the token.
- **Postman:** *Import* → *Link* → `http://localhost:8000/openapi.json`. Set the collection's *Authorization* to *Bearer Token* and paste the `access_token` from `POST /auth/login` (Body → `x-www-form-urlencoded`).

### 5.9 Run the tests

The tests use `app_db_test` (never `app_db`) on the same PostgreSQL, so the `db` container must be running.

```powershell
uv sync                                    # once, if you only used Option A so far
docker compose up -d db
uv run pytest                              # expect: 140 passed
uv run pytest --cov=loan_application --cov-report=term-missing
```

If you see `database "app_db_test" does not exist`, see [Troubleshooting](#16-troubleshooting).

### 5.10 Set up code-quality hooks (once)

```powershell
uv run pre-commit install
```

From now on every `git commit` runs Ruff and black first. Run the same checks as CI before pushing:

```powershell
uv run ruff check . ; uv run black --check . ; uv run pytest --cov=loan_application --cov-fail-under=80
```

### 5.11 Browse the database (optional, DBeaver)

New connection → PostgreSQL → host `localhost`, port `5433`, database `app_db`, user `kowshick`, password = your `POSTGRES_PASSWORD`.

### 5.12 Day-to-day: stop, update, reset

```powershell
docker compose stop                    # stop containers, keep everything
docker compose up -d                   # start them again
git pull ; uv sync ; uv run alembic upgrade head    # after pulling new code (Option B)
docker compose up --build -d           # after pulling new code (Option A: rebuilds, migrates on start)
docker compose down                    # remove containers, keep data
docker compose down -v                 # remove containers AND all data (fresh start; re-creates app_db_test)
```

---

## 6. Configuration (.env)

All settings come from environment variables. Locally they are read from `.env` in the **current folder**, which is never committed.

| Variable | Required | Example / default | Meaning |
|---|---|---|---|
| `POSTGRES_PASSWORD` | yes (Docker) | `change-me` | Password of the PostgreSQL user `kowshick`; used when the volume is first created |
| `DATABASE_URL` | yes | `postgresql+psycopg://kowshick:<pw>@localhost:5433/app_db` | Where the app connects when it runs on your machine. Inside Docker, compose sets it to `db:5432`. |
| `JWT_SECRET_KEY` | yes | 64 hex characters | Signs tokens; at least 32 characters |
| `JWT_ALGORITHM` | no | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Token lifetime |
| `SEED_OFFICER_PASSWORD` | no | — | Password for `officer1`. In Docker, if empty, the seed is skipped; locally, the seed script asks for it. |
| `SEED_OFFICER_USERNAME` | no | `officer1` | Username of the seeded officer |
| `LOG_FORMAT` | no | `text` | `text` (readable) or `json` |
| `TEST_DATABASE_URL` | no | — | Overrides the test database (CI uses this). Default: `DATABASE_URL` with the database renamed to `app_db_test`. |

---

## 7. How to use the API

### Step 1: Register (customer)

```http
POST /auth/register
Content-Type: application/json

{"username": "arjun_ramesh", "password": "Arjun@1234"}
```

→ `201`, the new user (role `CUSTOMER`, `has_customer_profile: false`). Only `username` and `password` are used; a `role` sent in the body is ignored.

### Step 2: Log in

The login endpoint takes a **form body**, not JSON:

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=arjun_ramesh&password=Arjun@1234
```

→ `{"access_token": "eyJ...", "token_type": "bearer", "expires_in": 1800}`

Send the token on every other request:

```
Authorization: Bearer eyJ...
```

In Swagger, click **Authorize** and log in there.

### Step 3: Create your customer profile

```http
POST /api/customers
{
  "name": "Arjun Ramesh",
  "email": "arjun.ramesh@example.com",
  "phone": "9876543210",
  "date_of_birth": "1995-06-18",
  "monthly_income": 85000,
  "address": "Chennai"
}
```

→ `201`. The profile is linked to your login. Until you create it, the other customer endpoints answer `403 CUSTOMER_PROFILE_REQUIRED`.

### Step 4: Apply for a loan

```http
POST /api/loans
{"customer_id": 1, "amount": 300000, "tenure_months": 36}
```

→ `201` with `status: "APPROVED"` and the `emi`, or `status: "REJECTED"` and a `rejection_reason`.

### Step 5: View loans and the summary

```http
GET /api/loans?status=APPROVED&page=1&size=10
GET /api/customers/1/loans
GET /api/customers/1/summary
```

### Officers

The first officer (`officer1`) is created by the seed script. An officer can:
- See every customer and loan.
- Apply for a loan for any customer.
- Create a profile for a registered customer login by adding `"username": "arjun_ramesh"` to `POST /api/customers`. Without `username`, the profile is created unlinked.

To link an existing login to an existing profile, or to create a login for a profile, run:

```powershell
uv run python -c "from loan_application.scripts.seed import link_customer_user; link_customer_user('arjun_ramesh', 1)"
uv run python -c "from loan_application.scripts.seed import create_customer_user; create_customer_user('meena', 'Secret@123', customer_id=1)"
```

When the API runs in Docker, run the same commands as `docker compose exec api python -c "..."`.

---

## 8. API reference

Every endpoint except `/health`, `/auth/register` and `/auth/login` needs `Authorization: Bearer <token>`.

| Method | Path | Who | Success |
|---|---|---|---|
| GET | `/health` | public | `200 {"status": "ok"}` |
| POST | `/auth/register` | public | `201` the new CUSTOMER user |
| POST | `/auth/login` | public | `200 {access_token, token_type, expires_in}` |
| POST | `/api/customers` | CUSTOMER (own profile, once); OFFICER | `201` the customer |
| GET | `/api/customers/{id}` | OFFICER any; CUSTOMER own | `200` the customer |
| GET | `/api/customers/{id}/loans?status=` | OFFICER any; CUSTOMER own | `200` list of loans, oldest first |
| GET | `/api/customers/{id}/summary` | OFFICER any; CUSTOMER own | `200` the loan summary |
| POST | `/api/loans` | OFFICER any; CUSTOMER own `customer_id` | `201` the loan (APPROVED or REJECTED) |
| GET | `/api/loans/{id}` | OFFICER any; CUSTOMER own | `200` the loan |
| GET | `/api/loans?status=&page=&size=` | OFFICER all; CUSTOMER own | `200 {items, page, size, total, pages}` |

### Who can do what

| Endpoint | No token | CUSTOMER | OFFICER |
|---|---|---|---|
| `/health`, `/auth/*` | allowed | allowed | allowed |
| `POST /api/customers` | 401 | own profile, once (409 `PROFILE_EXISTS` after that) | any profile |
| `GET /api/customers/{id}`, `/loans`, `/summary` | 401 | own only, otherwise 403 | any (404 if missing) |
| `POST /api/loans` | 401 | own `customer_id` only | any customer |
| `GET /api/loans`, `GET /api/loans/{id}` | 401 | own loans only | all loans |

### Example responses

**Loan**

```json
{
  "id": 7, "customer_id": 1, "amount": 300000.0, "tenure_months": 36,
  "interest_rate": 12.0, "emi": 9964.29, "status": "APPROVED",
  "rejection_reason": null, "applied_on": "2026-10-16"
}
```

**Summary**

```json
{
  "customer_id": 1, "customer_name": "Arjun Ramesh",
  "total_applications": 2, "approved_count": 1, "rejected_count": 1,
  "total_approved_amount": 300000.0, "total_monthly_emi": 9964.29,
  "emi_to_income_ratio": 11.72, "risk_band": "LOW"
}
```

**Loan page**

```json
{"items": [ ... ], "page": 1, "size": 10, "total": 23, "pages": 3}
```

`pages` is `0` when nothing matches. A page past the end returns `200` with empty `items`.

---

## 9. Business rules

All of these live in `services/loan_service.py`.

### Interest rate by tenure

| Tenure (months) | 12 | 24 | 36 | 48 | 60 |
|---|---|---|---|---|---|
| Annual rate | 10% | 11% | 12% | 13% | 13% |

### Eligibility

The rules are checked in this order, and the first one that fails becomes the `rejection_reason`:

1. Age must be between **21 and 60**.
2. Amount must not exceed **20 × monthly income**.
3. The customer must have fewer than **2 APPROVED** (active) loans.

Both approved and rejected applications are saved and return `201`.

### EMI (Equated Monthly Instalment)

```
r   = annual_rate / 12 / 100
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)
```

`P` is the amount and `n` is the tenure in months. The result is rounded half-up to 2 decimals. For example, ₹3,00,000 at 12% for 36 months gives **₹9,964.29**.

### Risk band (summary)

`emi_to_income_ratio = total monthly EMI of approved loans / monthly income × 100`

| Ratio | Risk band |
|---|---|
| below 30 | LOW |
| 30 – 50 | MEDIUM |
| above 50 | HIGH |

---

## 10. Validation rules

| Field | Rule |
|---|---|
| `name` | 3–50 characters, letters and spaces only |
| `email` | Valid email, unique, stored in lowercase |
| `phone` | Exactly 10 digits |
| `date_of_birth` | A past date, `YYYY-MM-DD` |
| `monthly_income` | Greater than 0, at most 2 decimal places |
| `address` | Optional, 1–255 characters |
| `customer_id`, `{id}` | Positive integer |
| `amount` | 10,000 – 50,00,000, at most 2 decimal places |
| `tenure_months` | One of 12, 24, 36, 48, 60 |
| `status` (query) | `APPROVED` or `REJECTED` |
| `page` / `size` | `page` ≥ 1; `size` 1–100 (default 20) |
| `username` | 3–50 characters: letters, digits, `_` `.` `@`; stored in lowercase |
| `password` | 8–128 characters |

---

## 11. Errors

Every error has the same shape, and `request_id` matches the `X-Request-ID` response header:

```json
{"error": "NOT_FOUND", "message": "Customer with id 99 not found", "request_id": "3f2a9c1e..."}
```

Validation errors list each failing field:

```json
{"error": "VALIDATION_FAILED", "details": [{"field": "phone", "message": "must be exactly 10 digits"}], "request_id": "..."}
```

| Status | `error` | When |
|---|---|---|
| 400 | `VALIDATION_FAILED` | A field, id or query parameter is invalid |
| 400 | `INVALID_REQUEST` | The body is missing or is not valid JSON |
| 400 | `NOT_A_CUSTOMER` | An officer linked a profile to a non-customer login |
| 401 | `UNAUTHORIZED` | No token, or the token is bad, expired, or belongs to an inactive or deleted user |
| 401 | `INVALID_CREDENTIALS` | Wrong username or password |
| 403 | `FORBIDDEN` | Another customer's data |
| 403 | `CUSTOMER_PROFILE_REQUIRED` | A customer login has no profile yet |
| 404 | `NOT_FOUND` | The record does not exist |
| 409 | `DUPLICATE_USERNAME` / `DUPLICATE_EMAIL` | The value is already taken |
| 409 | `PROFILE_EXISTS` | The login already has a profile |
| 409 | `CUSTOMER_REMOVED` | The customer was removed during the request |
| 500 | `INTERNAL_ERROR` | An unexpected failure; the stack trace stays in the server log |

A request without a valid token always gets `401`, even when its body is broken. `main.py` checks the token before reporting a body error.

---

## 12. Testing

The tests run against a separate database, `app_db_test`, never `app_db`. PostgreSQL must be running (`docker compose up -d db`).

```powershell
uv run pytest                                   # all tests
uv run pytest -k loan                           # only tests whose name contains "loan"
uv run pytest tests/test_loans.py               # one file
uv run pytest --cov=loan_application --cov-report=term-missing   # with coverage
```

| File | Covers |
|---|---|
| `tests/conftest.py` | Fixtures: test database, client, officer, signup, profileless; helpers |
| `tests/test_customers.py` | Creating and reading customers, summary, ownership, validation |
| `tests/test_loans.py` | EMI, every eligibility rule, risk bands, apply/get/list, pagination, full journey |
| `tests/test_users.py` | Register, login, tokens, 400/401/403/404 on every endpoint, logging, health, seed script |
| `tests/test_transactions.py` | Rollback, mapping a conflict to 409, the row lock, two concurrent loan applications |

How isolation works:
1. `conftest.py` switches the database URL to `app_db_test` before the engine is created, and stops if the name doesn't end in `_test`.
2. The schema is dropped and rebuilt with the Alembic migrations once per run.
3. Each test runs inside a transaction that is rolled back afterwards, so nothing it writes survives the test.

---

## 13. Code quality and CI

```powershell
uv run ruff check .            # lint
uv run ruff check . --fix      # auto-fix
uv run black .                 # format
uv run pre-commit install      # once: run ruff + black on every commit
```

CI runs `.github/workflows/ci.yml` on every pull request and every push to `main`:

| Job | What it does |
|---|---|
| Lint | `ruff check .` and `black --check .` |
| Tests | Starts a PostgreSQL 16 service and runs `pytest --cov --cov-fail-under=80` with a random JWT secret |
| Docker | `docker build .`, so a broken Dockerfile fails the PR |

Run the same checks before you push:

```powershell
uv run ruff check . ; uv run black --check . ; uv run pytest --cov=loan_application --cov-fail-under=80
```

---

## 14. Database

### Tables

| Table | Key columns |
|---|---|
| `customers` | `id`, `name`, `email` (unique), `phone`, `date_of_birth`, `monthly_income`, `address`, `created_at` |
| `loans` | `id`, `customer_id` → customers, `amount`, `tenure_months`, `interest_rate`, `emi`, `status`, `rejection_reason`, `applied_on` |
| `users` | `id`, `username` (unique), `password_hash`, `role`, `customer_id` → customers (unique, `ON DELETE SET NULL`), `is_active`, `created_at` |

### Migrations

```powershell
uv run alembic upgrade head          # apply all migrations
uv run alembic current               # which version the database is on
uv run alembic history               # list migrations
uv run alembic downgrade -1          # undo the last one
uv run alembic revision --autogenerate -m "describe change"   # new migration from model changes
```

Autogenerate does not detect CHECK constraints, so add those to the migration by hand.

### Browse the data (DBeaver)

New connection → PostgreSQL, host `localhost`, port `5433`, database `app_db`, user `kowshick`, password = `POSTGRES_PASSWORD`.

---

## 15. Command cheat sheet

```powershell
docker compose up --build -d                       # start db + api in Docker
docker compose up -d db                            # start only the database
docker compose ps                                  # status + health
docker compose logs -f api                         # follow the api logs
docker compose down                                # stop (data kept); add -v to delete data
uv sync                                            # install / update packages
uv run fastapi dev src/loan_application/main.py    # run the API locally with reload
uv run alembic upgrade head                        # apply migrations
uv run python -m loan_application.scripts.seed     # create / reset officer1
uv run pytest                                      # run tests
uv run ruff check . ; uv run black .               # lint + format
```

---

## 16. Troubleshooting

| Problem | Fix |
|---|---|
| `docker: command not found` / `cannot connect to the Docker daemon` | Start Docker Desktop and wait for *Engine running*; open a new terminal. |
| `set JWT_SECRET_KEY in .env` when running compose | Copy `.env.example` to `.env` and fill in every value. |
| `jwt_secret_key ... at least 32 characters` | Use a longer secret (see [5.3](#53-create-env)). |
| `database_url Field required` | Run the command from the project root (where `.env` is), or set `DATABASE_URL`. |
| `password authentication failed for user "kowshick"` | The password in `DATABASE_URL` must equal the one the volume was created with. Fix `.env`, or `docker compose down -v` to start fresh. |
| `connection refused` on port 5433 | Start the database: `docker compose up -d db`. |
| Tests fail with `database "app_db_test" does not exist` | The test database is only created on a new volume. Create it once: `docker compose exec db psql -U kowshick -d app_db -c "CREATE DATABASE app_db_test;"` |
| Tests fail with `relation "users" does not exist` | Another pytest run is using `app_db_test` at the same time. Run one test session at a time. |
| Port 8000 already in use | The Docker `api` container is running. Use it, or run `docker compose stop api` before `fastapi dev`. |
| `401 INVALID_CREDENTIALS` for officer1 | Set `SEED_OFFICER_PASSWORD` and run the seed script again (it resets the password). |
| `403 CUSTOMER_PROFILE_REQUIRED` | Create the profile with `POST /api/customers` first. |
| `400 VALIDATION_FAILED` "username is required" on login | `/auth/login` takes a form body (`x-www-form-urlencoded`), not JSON. |
| `uv sync --locked` fails in CI / Docker | `uv.lock` is out of date: run `uv lock` and commit it. |

# ADR 0001: JWT bearer tokens instead of server-side sessions

**Status:** Accepted · **Date:** 2026-10-16 (Week 2 Thursday)

## Context

Every loan and customer endpoint needs a logged-in user whose role (OFFICER or
CUSTOMER) decides what they may see. Callers are API clients (Swagger, Postman,
tests), the service runs in Docker with config only from environment
variables, and we may run more than one API container. Options: server-side
sessions (a session id in a cookie, looked up in a table or Redis on every
request) or signed JWTs (no session store).

## Decision

Use **JWT access tokens** (`Authorization: Bearer`) from `POST /auth/login`
(OAuth2 password flow): HS256, secret only from `JWT_SECRET_KEY`, claims
`sub`, `role`, `iat`, `exp`, valid 30 minutes. Each request still loads the
user from the database and uses **its** `role` and `is_active`.

## Consequences

- **Good:** no session store to run or clean up; any container can verify any
  token; works directly with API clients and Swagger; no cookies, so no CSRF.
- **Cost:** a token cannot be revoked before it expires. Reloading the user
  makes deactivation and role changes take effect at once, so only a stolen
  token stays valid, for at most 30 minutes. Logout is client-side only.
- **Cost:** whoever holds the secret can mint tokens; rotate it if leaked
  (everyone is logged out). Move to RS256 if other services must verify tokens.
- **Revisit** if we need refresh tokens, "log out everywhere", or a browser
  front end, where an HttpOnly session cookie may be simpler.

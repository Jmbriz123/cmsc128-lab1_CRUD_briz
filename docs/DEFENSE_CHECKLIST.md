# Activity 2 defense checklist

## Before the defense

- Confirm the public repository and `act2-accounts` branch contain your final commits.
- Configure real SMTP credentials locally, authorize the sender, and successfully receive a reset email in an inbox you control.
- Open the running frontend and the psql inspection tool. Know the difference between port 5432 inside Docker and the configured host PostgreSQL port.
- Run backend tests including the PostgreSQL checks, frontend tests, and the production build.
- Rehearse the explanation below without notes or AI assistance; those are not permitted during the actual defense.
- Make the final submission checkpoint with `cmsc128-Indiv-Act2` after verifying the deliverables.

## Live demonstration

1. Register an account. Show required-field validation, invalid email rejection, and duplicate-email rejection.
2. Inspect its ID, email, display name, and Argon2 hash prefix through psql.
3. Show an invalid login, then a successful login and `Hello, <display name>` on Profile.
4. Refresh; navigate back/forward; restart the backend with `docker compose restart backend`; verify the account remains signed in.
5. Change the display name and email. Demonstrate current-password verification for email changes and duplicate-email rejection. Refresh and inspect the stored values.
6. Edit a profile field, navigate away, and demonstrate the unsaved-change warning.
7. Show the shared task workspace while signed in. Explain that user ownership will be added in the next activity.
8. Change the password. Verify the old password fails and the new password works.
9. Request recovery, receive the real email, and open its link. Choose another password; show old-password rejection, successful new-password login, and reset-link reuse rejection.
10. Log out. Use the Back button and attempt a protected API operation; the application must not expose protected data.
11. Repeat database inspection after a backend restart to distinguish account persistence from session persistence.

## Explain these code paths

| Topic | What to trace |
|---|---|
| Registration | Form → API client → request schema → account service → Argon2 hash → unique database record |
| Login | Rate limit → email lookup → password verification → persistent session hash → HttpOnly cookie |
| Authentication | Cookie → SHA-256 lookup → expiry condition → current user dependency → protected endpoint |
| Logout | Delete session row → clear cookie → clear frontend state → guard future navigation |
| Profile | Current user ID → locked user row → password verification for email → uniqueness constraint → commit |
| Password reset | Generic acknowledgment → background SMTP task → hashed token → user-row lock → conditional consumption → new hash and session revocation in one transaction |
| Concurrency | Two simultaneous reset requests cannot both consume one token; the PostgreSQL test proves this |
| Frontend state | In-memory user data is a display cache; `/auth/me` and the database decide authentication |
| Configuration | Secrets stay in ignored `.env`; Compose passes them into backend settings; `.env.example` contains no usable credentials |
| Future ownership | Use `get_current_user` and a future `todos.user_id` foreign key to scope every read/write, including restore |

## Know the limits

- Shared tasks are intentional for this activity; login gating is not owner-based access control.
- SMTP background tasks and rate-limit counters are not durable/distributed queues or stores.
- Without configured SMTP, recovery returns 503. Automated email mocks do not prove real inbox delivery.
- Sessions expire after the configured lifetime and are deliberately invalidated by logout/password changes.
- HTTP cookies are allowed only for local development. Remote hosting needs HTTPS, Secure cookies, exact origins, and a reachable frontend URL.
- Email verification, MFA, and account deletion are outside this activity's scope.

# Environment reference

Run `python scripts/setup_dev.py` to create ignored development files with random secrets. The script never overwrites existing configuration. Commit only `.env.example` files. Read root `.env` from the repository root when running API commands.

| Variable | Default / requirement | Purpose |
| --- | --- | --- |
| APP_ENV | development; development/test/production | Production enforces PostgreSQL and HTTPS browser origins |
| DATABASE_URL | sqlite:///./faultline.db | SQLAlchemy connection URL; production uses postgresql+psycopg://user:password@host/database |
| JWT_SECRET | Required, at least 32 characters | Backend signing key; use a random key, rotate to invalidate outstanding access tokens |
| JWT_ISSUER | faultline-api | Required JWT issuer |
| JWT_AUDIENCE | faultline-mobile | Required JWT audience |
| ACCESS_MINUTES | 10; allowed 1–60 | Access token lifetime |
| REFRESH_DAYS | 30; allowed 1–90 | Absolute session-family lifetime; rotation does not extend it |
| ALLOWED_ORIGINS | localhost:8081 and 127.0.0.1:8081 HTTP origins | JSON array of exact web origins; native requests do not use browser CORS |
| AUTH_RATE_LIMIT | 20 | Attempts per IP and, for login/registration, normalized email per fixed window and action |
| AUTH_RATE_WINDOW_SECONDS | 300 | Shared database throttle window; responses include Retry-After |
| REDIS_URL | unset | Optional M1 readiness check; Compose configures redis://redis:6379/0. Job processing begins in M2 |
| POSTGRES_PASSWORD | Required by Compose | Generate a URL-safe password; Compose interpolates it into the internal database URL |
| EXPO_PUBLIC_API_URL | http://localhost:8000 | Mobile **public** config in apps/mobile/.env; never put credentials here |
| TEST_DATABASE_URL | unset | Dedicated disposable PostgreSQL database for tests; tests migrate up and down and erase their tables |

For Android emulators use `http://10.0.2.2:8000`. For physical devices use the development computer's LAN IP and bind the API to `0.0.0.0`. Use HTTP only on a trusted development network. Restart Expo after public environment changes. Production mobile builds require an HTTPS API endpoint.

GitHub, Sentry, Vercel, model, push, encryption-key, and executor configuration is deliberately absent from M1. No provider is connected. Add and document those values with their feature milestones; never place them in Expo configuration.

Do not use development secrets in deployment. Inject secrets from a secret manager in production. Keep database, Redis, and API credentials scoped to their processes; do not log connection URLs or tokens. Terminate TLS at a trusted ingress, bound request sizes there, and disable arbitrary forwarded-header trust. Rate limiting uses the socket peer address; configure a trusted proxy integration before scaling behind a load balancer.

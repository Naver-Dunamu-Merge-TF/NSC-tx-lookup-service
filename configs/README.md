# Environment configuration

Rules
- Use `APP_ENV` to select `local`, `dev`, or `prod`.
- `local` defaults are safe for Docker Compose (no secrets committed).
- `dev`/`prod` must set all connection values via environment variables or secret stores.
- Follow 12-factor practices: never commit credentials.

Required variables (current skeleton)
- `APP_ENV`: `local` | `dev` | `prod`
- `LOG_LEVEL`: `INFO` by default
- `DATABASE_URL`: Backoffice DB connection string
- `KAFKA_BROKERS`: Kafka bootstrap servers
- `SERVICE_NAME`: service identifier for logs/metrics

Examples
- Copy `configs/env.example` and export values in your shell.

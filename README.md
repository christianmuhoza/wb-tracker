# wb-tracker

## Test password reset locally

The Docker Compose setup sends reset email to Mailpit instead of a real inbox.
Start the app and Mailpit from the repository root:

```powershell
docker compose up --build
```

Open the app at <http://localhost> and Mailpit at <http://localhost:8025>. A
reset email sent by the app appears in Mailpit; its link opens the local app.
The local SMTP settings are defined in `docker-compose.yml`, so no mail account
or SMTP credentials are needed.

For a backend/frontend run outside Docker, start Mailpit with
`docker compose up mailpit`, keep `SMTP_HOST=localhost` and `SMTP_PORT=1025` in
`backend/.env`, then run the backend and Vite frontend normally. Set
`APP_BASE_URL=http://localhost:5173` in that case.

The initial admin can receive reset emails when `ADMIN_EMAIL` is set before the
first database bootstrap. For an existing account, sign in to the API docs at
<http://localhost:8000/docs> and use `PUT /api/auth/users/{username}` with an
`email` field to add an address. The database migration runs on backend startup.

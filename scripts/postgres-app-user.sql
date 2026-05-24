-- Optional least-privilege DB user for production (run once as superuser).
-- Replace placeholders before executing. Application DATABASE_URL must use hatecrime_app.

CREATE USER hatecrime_app WITH PASSWORD 'REPLACE_STRONG_PASSWORD';
GRANT CONNECT ON DATABASE hatecrime TO hatecrime_app;
GRANT USAGE ON SCHEMA public TO hatecrime_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hatecrime_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hatecrime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hatecrime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hatecrime_app;

-- Example URL:
-- postgresql+asyncpg://hatecrime_app:REPLACE_STRONG_PASSWORD@db:5432/hatecrime

FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM openpolicyagent/opa:1.22.2-static AS opa
FROM node:24-slim AS dashboard
WORKDIR /dashboard
COPY apps/dashboard/package.json apps/dashboard/package-lock.json ./
RUN npm ci
COPY apps/dashboard ./
RUN npm run build

FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY agents ./agents
COPY apps ./apps
COPY data ./data
COPY deployments ./deployments
COPY evaluations ./evaluations
COPY gateways ./gateways
COPY integrations ./integrations
COPY knowledge ./knowledge
COPY observability ./observability
COPY orchestration ./orchestration
COPY security ./security
RUN uv sync --locked --no-dev

FROM python:3.12-slim
ENV PATH="/app/.venv/bin:${PATH}" \
    AWS_SANDBOX_MODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp
RUN groupadd --system app && useradd --system --gid app --uid 10001 app
WORKDIR /app
COPY --from=build /app /app
COPY --from=dashboard /dashboard/dist /app/apps/dashboard/dist
COPY --from=opa /opa /usr/local/bin/opa
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_PATH=/data/compvvd.sqlite3 COOKIE_SECURE=true
WORKDIR /srv/compvvd
RUN groupadd --gid 10001 compvvd && useradd --uid 10001 --gid compvvd --no-create-home compvvd && mkdir /data && chown compvvd:compvvd /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=compvvd:compvvd app ./app
USER compvvd
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", "--timeout", "60", "--access-logfile", "-", "app.web:create_app()"]

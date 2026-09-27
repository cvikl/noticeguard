# NoticeGuard: FastAPI + rules engine + committed LLM cache. Runs the demo fully offline; live uploads need an API key in .env.
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
COPY data ./data
COPY cache ./cache
COPY bench ./bench
COPY README.md ./
ENV PYTHONUNBUFFERED=1 NOTICEGUARD_CACHE=1 NOTICEGUARD_DB=/data/cases.db
EXPOSE 8790
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8790", "--proxy-headers", "--forwarded-allow-ips", "*"]

FROM python:3.12-slim
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && apt-get -o APT::Update::Error-Mode=any -o Acquire::Retries=0 -o Acquire::https::Timeout=20 update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=10001:10001 app.py egress.py ./
COPY --chown=10001:10001 static ./static
RUN useradd --uid 10001 --create-home reelsave
USER reelsave
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]

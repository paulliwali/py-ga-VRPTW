FROM python:3.12-slim

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "server.py"]

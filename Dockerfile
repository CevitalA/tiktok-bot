FROM python:3.11-slim

WORKDIR /app

# منع تجميع بايثون للكاش لتخفيف المساحة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# المنفذ الافتراضي الذي تستمع إليه منصة Koyeb
ENV PORT=8000
EXPOSE 8000

CMD ["python", "run.py"]

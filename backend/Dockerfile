FROM python:3.11-slim

WORKDIR /app

# Install backend deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt fastapi uvicorn

# Copy backend app code
COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

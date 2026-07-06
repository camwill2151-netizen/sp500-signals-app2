FROM python:3.11-slim

WORKDIR /app

# Install frontend deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt streamlit requests pandas plotly

# Copy frontend app code
COPY . /app

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

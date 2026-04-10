# ---- Base image ----
FROM python:3.11-slim

# ---- Environment settings ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# ---- System dependencies ----
# build-essential is needed for some Python wheels
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libicu-dev \
    fontconfig \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

# ---- Working directory ----
WORKDIR /app

# ---- Install Python dependencies first (better layer caching) ----
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy application code ----
COPY . .

# ---- Create data directory (SQLite + ChromaDB live here) ----
RUN mkdir -p data

# ---- Expose Streamlit port ----
EXPOSE 8501

# ---- Run the app ----
CMD ["streamlit", "run", "app/home.py"]

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/leadify/ui
RUN npm install
RUN npm run build

WORKDIR /app
EXPOSE 8000

CMD ["uvicorn", "leadify.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

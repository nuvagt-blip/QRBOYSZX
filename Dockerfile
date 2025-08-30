FROM python:3.13-slim

# Instala dependencias del sistema para pyzbar
RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot_qr.py"]

# Usamos una imagen de Python oficial
FROM python:3.11-slim

# Instalamos FFmpeg y herramientas necesarias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libffi-dev \
    libnacl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Creamos la carpeta de trabajo
WORKDIR /app

# Copiamos el archivo de requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Comando para arrancar el bot (ajusta 'bot.py' si tu archivo se llama distinto)
CMD ["python", "bot.py"]
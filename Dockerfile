# Usa un'immagine ufficiale di Python
FROM python:3.11-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY . .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Variabile d'ambiente per Python logging
ENV PYTHONUNBUFFERED=1

# Avvia il bot
CMD ["python", "telegram_timer.py"]
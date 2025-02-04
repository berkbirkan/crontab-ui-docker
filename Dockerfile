FROM python:3.9-slim

WORKDIR /app

# Gereksinim dosyasını kopyala ve paketleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm uygulama dosyalarını kopyala
COPY . .

EXPOSE 5000

# Gunicorn ile uygulamayı başlat (app.py içerisinde app global olarak tanımlı)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"] 
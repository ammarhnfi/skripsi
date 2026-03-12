# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Set direktori kerja di dalam container
WORKDIR /app

# Copy file requirements dulu dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa kode aplikasi
COPY . .

# Perintah untuk menjalankan aplikasi
# "final" adalah nama file final.py
# "server" adalah nama variabel (server = app.server)
# Port 7860 adalah port default yang didengar oleh Hugging Face Spaces
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "final:server"]
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps msedge

COPY . .

# Diretório de logs (será sobrescrito por volume no EasyPanel)
RUN mkdir -p /app/logs

EXPOSE 5000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "5000"]

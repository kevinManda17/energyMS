FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# Run the local API + background sync loop. The MQTT subscriber can be run
# separately with: python mqtt_subscriber.py
CMD ["uvicorn", "sync_service:app", "--host", "0.0.0.0", "--port", "8001"]

#!/bin/sh

# Wait for postgres to be ready using Python
echo "Waiting for postgres..."
python -c "
import socket
import time
while True:
    try:
        with socket.create_connection(('postgres', 5432), timeout=1):
            break
    except OSError:
        time.sleep(0.1)
"
echo "PostgreSQL started"

# Run migrations/schema
echo "Creating Schema..."
python reset_schema.py

# Run ingestion
echo "Ingesting Data..."
python load_data.py

# Start the actual FastAPI server
echo "Starting Backend Server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
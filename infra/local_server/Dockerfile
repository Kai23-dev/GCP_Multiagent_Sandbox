FROM python:3.11-slim

WORKDIR /app

# Copy the requirements file
COPY infra/local_server/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the agent code
COPY infra/ /app/infra/

# Expose port 8000
EXPOSE 8000

# Run the FastAPI server
CMD ["python", "infra/local_server/main.py"]

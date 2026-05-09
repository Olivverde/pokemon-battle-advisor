FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY api/ ./api/
COPY models/ ./models/

# Handler de Mangum para Lambda
CMD ["python", "-m", "awslambdaric", "api.main.handler"]
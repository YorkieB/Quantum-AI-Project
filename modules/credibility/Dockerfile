FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    scikit-learn \
    numpy \
    torch --index-url https://download.pytorch.org/whl/cpu \
    lambeq \
    spacy \
    && python -m spacy download en_core_web_sm

# Copy module code
COPY . /app/

# Expose port
EXPOSE 3031

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3031/api/credibility/health || exit 1

# Start service
CMD ["python", "service.py"]
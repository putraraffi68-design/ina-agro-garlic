# Untuk Hugging Face Spaces (SDK: Docker) atau hosting Docker lain
FROM python:3.12-slim
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    DATA_MODE=riil AGROGARLIC_DB=/tmp/agrogarlic.db
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY --chown=user . .
EXPOSE 7860
CMD ["sh", "-c", "cd app && uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]

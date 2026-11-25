FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    if ! python -c "import triangle" 2>/dev/null; then \
        git clone --depth 1 --recurse-submodules --shallow-submodules -b v20250106 https://github.com/drufat/triangle.git /tmp/triangle && \
        pip install --no-cache-dir /tmp/triangle && \
        rm -rf /tmp/triangle; \
    fi

# Copy the full source code, including the `mesh_api` package and its modules.
COPY . .

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 2 --timeout 120 app:application"]

FROM parrotsec/security:7.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the standalone installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.uv/bin:/root/.local/bin:$PATH"

# Copy only the files needed for installation
# pyproject.toml is required for pip install
# README.md is referenced in pyproject.toml
COPY pyproject.toml README.md /app/

# Create a virtual environment using uv
ENV VIRTUAL_ENV=/app/venv
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies first (this layer will be cached if pyproject.toml doesn't change)
RUN uv pip install ".[cli,docker]"

# Now copy the source code
COPY exodus/ /app/exodus/

# Reinstall in editable mode to ensure scripts point to the copied source
RUN uv pip install --no-deps -e .

# Copy and configure the entrypoint script
COPY docker/exodus_security_executor/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

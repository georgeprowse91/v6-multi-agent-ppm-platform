FROM mcr.microsoft.com/devcontainers/python:3.11

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm

COPY requirements-dev.txt requirements-dev.txt
RUN pip install -r requirements-dev.txt

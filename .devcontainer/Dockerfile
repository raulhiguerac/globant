FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

ARG NODE_VERSION=20

RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /usr/local/bin/

RUN npm install -g pnpm

RUN curl -fsSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz | tar -xz -C /opt \
    && /opt/google-cloud-sdk/install.sh --quiet --path-update=true \
    && ln -s /opt/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud \
    && ln -s /opt/google-cloud-sdk/bin/gsutil /usr/local/bin/gsutil

WORKDIR /workspace

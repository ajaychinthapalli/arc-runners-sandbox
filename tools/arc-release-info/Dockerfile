FROM python:3.12-slim
# Pass the real version: --build-arg HELM_VERSION=$(helm version --short | cut -d+ -f1)
# (leaving the placeholder makes the download 404 - see logs/09)
ARG HELM_VERSION=v4.2.4
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz | tar -xz -C /tmp \
 && mv /tmp/linux-${TARGETARCH}/helm /usr/local/bin/helm \
 && apt-get purge -y curl && rm -rf /var/lib/apt/lists/* /tmp/*
# mcp pinned below 2: SDK 2.x renamed FastMCP (see logs/10)
RUN pip install --no-cache-dir "mcp[cli]<2" httpx kubernetes pyyaml
COPY server.py /app/server.py
ENV HOME=/tmp PYTHONUNBUFFERED=1
USER 65534
EXPOSE 8080
CMD ["python", "/app/server.py"]

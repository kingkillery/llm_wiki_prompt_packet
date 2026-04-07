FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-pip \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN git config --system --add url."https://github.com/".insteadOf ssh://git@github.com/ \
    && git config --system --add url."https://github.com/".insteadOf git@github.com:

RUN npm install -g byterover-cli

RUN useradd --create-home --shell /bin/bash llmwiki

WORKDIR /opt/llm-wiki

COPY . /opt/llm-wiki

RUN chmod +x /opt/llm-wiki/docker/entrypoint.sh \
    && chmod +x /opt/llm-wiki/support/scripts/*.sh \
    && chmod +x /opt/llm-wiki/installers/assets/vault/scripts/*.sh \
    && chown -R llmwiki:llmwiki /opt/llm-wiki /home/llmwiki

USER llmwiki

ENV HOME=/home/llmwiki
ENV NPM_CONFIG_PREFIX=/home/llmwiki/.npm-global
ENV NPM_CONFIG_CACHE=/tmp/llmwiki-npm-cache
ENV PATH=/opt/llm-wiki/node_modules/.bin:/home/llmwiki/.npm-global/bin:/home/llmwiki/.local/bin:/usr/local/bin:/usr/bin:/bin
ENV PYTHON_BIN=python3

EXPOSE 8181

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/llm-wiki/docker/entrypoint.sh"]
CMD ["serve"]

FROM python:3.12.14 AS base
RUN apt update
RUN apt upgrade -y

RUN adduser --uid 10000 app
RUN mkdir -p /usr/app
RUN chown app:app /usr/app


FROM base AS terraform
# Install terraform
RUN apt-get update
RUN apt-get install -y wget unzip zip
RUN rm -rf /var/lib/apt/lists/*
RUN wget --quiet https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
RUN unzip terraform_1.6.6_linux_amd64.zip
RUN mv terraform /usr/bin/
RUN rm terraform_1.6.6_linux_amd64.zip


FROM terraform AS npx
# Install npx
RUN apt-get install -y curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*


FROM npx AS cloud-sql-proxy
# Install cloud-sql-proxy
RUN apt-get install -y curl \
    && curl -o /usr/local/bin/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.1.1/cloud-sql-proxy.linux.amd64 \
    && chmod +x /usr/local/bin/cloud-sql-proxy


FROM cloud-sql-proxy AS gcloud
# Install gcloud
USER 10000
WORKDIR /usr/app

COPY --chown=app:app ./.devcontainer/install_gcloud.sh .
RUN sed -i 's/\r$//' ./install_gcloud.sh && \
    chmod +x ./install_gcloud.sh
RUN ./install_gcloud.sh


FROM gcloud AS devcontainer
ENV ISDEVCONTAINER=true

COPY --chown=app:app ./requirements.txt .
COPY --chown=app:app ./.devcontainer/dev-requirements.txt .
COPY --chown=app:app ./.devcontainer/cli-requirements.txt .
COPY --chown=app:app ./.devcontainer/webapp-requirements.txt .
COPY --chown=app:app ./.devcontainer/api-requirements.txt .
COPY --chown=app:app ./.devcontainer/python_setup.sh .

RUN sed -i 's/\r$//' ./python_setup.sh && \
    chmod +x ./python_setup.sh
RUN ./python_setup.sh

COPY --chown=app:app ./.devcontainer/post_create_commands.sh .
RUN sed -i 's/\r$//' ./post_create_commands.sh && \
    chmod +x ./post_create_commands.sh

COPY --chown=app:app ./.devcontainer/launch_cloud_sql_proxy.sh .
RUN sed -i 's/\r$//' ./launch_cloud_sql_proxy.sh && \
    chmod +x ./launch_cloud_sql_proxy.sh

WORKDIR /home/app
COPY ./.devcontainer/bashrc.sh .
RUN sed -i 's/\r$//' ./bashrc.sh && \
    chmod +x ./bashrc.sh
RUN cat ./bashrc.sh >> .bashrc


FROM base AS web-app
USER 10000
WORKDIR /usr/app

COPY --chown=app:app ./src ./src
COPY --chown=app:app ./requirements.txt .
COPY --chown=app:app ./.devcontainer/webapp-requirements.txt .
COPY --chown=app:app ./.devcontainer/python_setup.sh .

RUN sed -i 's/\r$//' ./python_setup.sh && \
    chmod +x ./python_setup.sh
RUN ./python_setup.sh

ENV PATH="/usr/app/venv/bin:${PATH}"
ENV PYTHONPATH="/usr/app:/usr/app/src/entrypoints/webapp:${PYTHONPATH}"

CMD ["gunicorn", "-b", "0.0.0.0:8080", "src.entrypoints.webapp.app:server"]


FROM base AS web-api
USER 10000
WORKDIR /usr/app

COPY --chown=app:app ./src ./src
COPY --chown=app:app ./requirements.txt .
COPY --chown=app:app ./.devcontainer/api-requirements.txt .
COPY --chown=app:app ./.devcontainer/python_setup.sh .

RUN sed -i 's/\r$//' ./python_setup.sh && \
    chmod +x ./python_setup.sh
RUN ./python_setup.sh

ENV PATH="/usr/app/venv/bin:${PATH}"
ENV PYTHONPATH="/usr/app:/usr/app/src/entrypoints/webapi:${PYTHONPATH}"

CMD ["gunicorn", "-b", "0.0.0.0:8080", "src.entrypoints.webapi.app:server"]


FROM base AS cli-app
USER 10000
WORKDIR /usr/app

COPY --chown=app:app ./src ./src
COPY --chown=app:app ./entrypoint.sh .
COPY --chown=app:app ./requirements.txt .
COPY --chown=app:app ./.devcontainer/cli-requirements.txt .
COPY --chown=app:app ./.devcontainer/python_setup.sh .

RUN sed -i 's/\r$//' ./python_setup.sh && \
    chmod +x ./python_setup.sh
RUN ./python_setup.sh

ENV PYTHONPATH="/usr/app/src/entrypoints:${PYTHONPATH}"

ENTRYPOINT [ "./entrypoint.sh" ]
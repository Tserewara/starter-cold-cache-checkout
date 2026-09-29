FROM python:3.12.8-slim
RUN pip install --no-cache-dir "psycopg[binary]==3.2.3" redis==5.2.1
WORKDIR /tools
COPY tools/ .

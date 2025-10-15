FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install uv
RUN uv pip install --system . 

ENTRYPOINT ["mnemex"]

FROM python:3.10-slim-buster

RUN apt-get update && apt-get install -y \
bash curl mc git iputils-ping telnet\
&& rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

WORKDIR /app

ENV PYTHONPATH="$PATH:/app"

COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

COPY *.py /app/

ENTRYPOINT ["python", "aio_pika_run.py"]

STOPSIGNAL SIGINT

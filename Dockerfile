FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    g++ \
    python3 \
    python3-pip \
    && apt-get clean

WORKDIR /app

COPY bgmi.c .
COPY bgmibot.py .

RUN g++ -O3 -pthread -std=c++11 -o bgmi_beast bgmi.c && \
    chmod +x bgmi_beast

RUN pip3 install python-telegram-bot==20.7

CMD ["python3", "bgmibot.py"]

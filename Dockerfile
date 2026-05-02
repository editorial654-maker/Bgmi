FROM alpine:3.19

RUN apk add --no-cache g++ python3 py3-pip

WORKDIR /app

COPY bgmi.c .
COPY bgmibot.py .

RUN g++ -O3 -pthread -std=c++11 -o bgmi_beast bgmi.c && \
    chmod +x bgmi_beast

RUN pip3 install python-telegram-bot==20.7

CMD ["python3", "bgmibot.py"]

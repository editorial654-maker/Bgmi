FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    g++ \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bgmi.c .
COPY bgmibot.py .
COPY requirements.txt .

RUN g++ -O3 -pthread -std=c++11 -o bgmi_beast bgmi.c && \
    chmod +x bgmi_beast && \
    pip3 install -r requirements.txt

CMD ["python3", "bgmibot.py"]

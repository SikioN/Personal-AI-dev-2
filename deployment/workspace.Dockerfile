FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

LABEL maintainer="m.menschikov@skoltech.ru"

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*
RUN apt-get clean
RUN apt-get --assume-yes update
RUN apt-get --assume-yes upgrade

RUN apt-get --assume-yes install pip
RUN apt-get --assume-yes install curl

RUN apt-get --assume-yes install cron
RUN apt-get --assume-yes install nano
RUN apt-get --assume-yes install --reinstall rsyslog
RUN apt-get --assume-yes install systemctl
RUN apt-get --assume-yes install wsl
RUN systemctl enable cron
RUN systemctl start cron

WORKDIR /home

RUN apt-get --assume-yes install python3.10
RUN apt-get --assume-yes install libicu-dev python3-icu pkg-config

RUN python3 --version
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

#RUN useradd -rm -d /home/workspace -s /bin/bash -g root -G sudo -u 4200235 m.menschikov
#RUN useradd -rm -d /home/workspace -s /bin/bash -g root -G sudo -u 1000 dzigen
#ARG APP_DIR=/home/m.menschikov/workspace
#ENV PYTHONPATH "${PYTHONPATH}:${APP_DIR}"
#USER m.menschikov

USER root

CMD ["sh", "-c", "sleep infinity"]

FROM --platform=linux/amd64 ubuntu:22.04
ARG WEBOTS_RELEASE=R2025a
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates wget python3 && \
    wget -q https://github.com/cyberbotics/webots/releases/download/${WEBOTS_RELEASE}/webots_2025a_amd64.deb -O /tmp/webots.deb && \
    apt-get install -y --no-install-recommends /tmp/webots.deb && \
    rm -rf /tmp/webots.deb /var/lib/apt/lists/*
ENV WEBOTS_HOME=/usr/local/webots
WORKDIR /controller
COPY robot_controller.py start.sh ./
RUN chmod +x start.sh
ENTRYPOINT ["/controller/start.sh"]

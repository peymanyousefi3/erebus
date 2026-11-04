FROM cyberbotics/webots:R2025a-ubuntu22.04
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /erebus
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt
COPY game ./game
COPY scripts/prepare_world.py ./scripts/prepare_world.py
COPY docker/competition/start_server.py ./start_server.py
RUN python3 scripts/prepare_world.py && useradd --create-home --uid 1000 organizer && mkdir -p /erebus/match-results && chown -R organizer:organizer /erebus
USER organizer
ENV WEBOTS_HOME=/usr/local/webots
ENTRYPOINT ["python3", "/erebus/start_server.py"]

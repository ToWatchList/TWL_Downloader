FROM kmb32123/youtube-dl-server

RUN mkdir -p /usr/src/twl
WORKDIR /usr/src/twl
COPY twl_downloader.py requirements.txt /usr/src/twl/

RUN pip install --no-cache-dir -r requirements.txt && \
    python3

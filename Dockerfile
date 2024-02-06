# Use python:slim as base image
FROM python:slim

# Set work directory
WORKDIR /app/twigram

# Copy current directory into work directory
COPY . /app/twigram/

# Install git, clean apt cache and install python dependencies
RUN <<EOF
apt-get update
apt-get upgrade -y
apt-get install -y git
pip install --no-cache-dir -r requirements.txt
apt-get remove -y git
apt-get purge -y git
apt-get autoremove -y
apt-get clean all
rm -rf /var/lib/apt/lists/*
find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
chmod +x /app/twigram/run.sh
EOF

ENV DEBUG ""
ENV TOKEN ""
ENV INTERVAL "30"           # interval for polling mode
ENV WEB_URL_ENABLE ""       # enable webhook mode, set to True/TRUE to enable
ENV WEB_URL ""              # your web url for webhook mode, e.g. https://twigram.example.com
ENV PORT "8080"             # port for local listening, you need a reverse proxy to forward traffic to this port
ENV CERT_FILE ""
ENV KEY_FILE ""
ENV TWITTER_USERNAME ""
ENV TWITTER_EMAIL ""
ENV TWITTER_PASSWORD ""
ENV TWITTER_COOKIE ""
ENV PROCESS_COUNT 1
ENV QUOTE "False"

CMD /app/twigram/run.sh

# Use python:slim as base image
FROM python:slim

# Set work directory
WORKDIR /app/twigram

# Copy current directory into work directory
COPY . /app/twigram/

# Install git, clean apt cache and install python dependencies
RUN <<EOF
apt-get update
apt-get install -y git
pip install --no-cache-dir -r requirements.txt
apt-get remove -y git
apt-get purge -y git
apt-get autoremove -y
apt-get clean all
rm -rf /var/lib/apt/lists/*
EOF

ENV DEBUG ""
ENV TOKEN ""
ENV INTERVAL "30"           # interval for polling mode
ENV WEB_URL ""              # you web url for webhook mode, e.g. https://twigram.example.com
ENV PORT "8080"             # port for local listening, you need a reverse proxy to forward traffic to this port
ENV TWITTER_USERNAME ""
ENV TWITTER_EMAIL ""
ENV TWITTER_PASSWORD ""
ENV TWITTER_COOKIE ""

CMD ["python3", "main.py"]

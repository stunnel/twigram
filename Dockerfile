# Use python:slim as base image
FROM python:slim

# Set work directory
WORKDIR /app/tftb

# Copy current directory into work directory
COPY . /app/twigram/

# Install git, clean apt cache and install python dependencies
RUN <<EOF
apt-get update
apt-get install -y git
apt-get clean all
rm -rf /var/lib/apt/lists/*
pip install --no-cache-dir -r requirements.txt
EOF

ENV DEBUG ""
ENV TOKEN ""
ENV INTERVAL "30"
ENV TWITTER_USER_NAME ""
ENV TWITTER_EMAIL ""
ENV TWITTER_PASSWORD ""
ENV TWITTER_COOKIE ""

CMD ["python3", "main.py"]

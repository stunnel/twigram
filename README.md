# Twigram

This projects aims to make a [Telegram](https://telegram.org) bot that forwards [Twitter](https://twitter.com/) to Telegram

## How to run

### Credentials

**Telegram bot token**

You **MUST** provide a valid Telegram Bot TOKEN to run the bot.

**Twitter credentials**

The Twitter username, email and password are **optional**.  
**NOTE**: Credentials logins may be subject to risk control restrictions.  
Or you can provide a Twitter cookie instead.  
Cookie format: `{"auth_token": "xxx", "ct0": "yyy"}`

If you don't provide any of these, the bot will use a anonymous session.  
But it may be subject to rate limit.

**Webhook**
If you set `WEB_URL_ENABLE` to True, and provide `WEB_URL` and `PORT`, the bot will run a webhook server for Telegram server to send updates.  
Otherwise, it will run a polling bot.

As a webhook server, you must provide a https web with valid certificate, and can be accessed by Telegram server.  
You can run in http mode and use a reverse proxy.  
Or you can provide valid certificate and key, the bot will run in https.

IMPORTANT: Ports currently supported for webhooks: 443, 80, 88, 8443.
ref: https://core.telegram.org/bots/api#setwebhook

### Docker

1. Clone this repo
2. Build image:
    ```
    docker build -t twigram:latest .
    ```
3. Run container:
    ```
    docker run -d --network host \
        --name twigram --restart=on-failure \
        -e TOKEN=<telegram_token> \
        -e INTERVAL=<polling_interval_in_seconds> \
        -e TWITTER_USERNAME=<twitter_username> \
        -e TWITTER_EMAIL=<twitter_email> \
        -e TWITTER_PASSWORD=<twitter_password> \
        -e TWITTER_COOKIE=<twitter_token> \
        -e WEB_URL_ENABLE=<TRUE or FALSE> \
        -e WEB_URL=<https_web_url> \
        -e CERT_FILE=<cert file> \
        -e KEY_FILE=<key file> \
        -e PORT=8080 \
        -e PROCESS_COUNT=1 \
        -e DEBUG=false \
        twigram:latest
    ```

### Manually

1. Clone this repo
2. Create venv:
    ```
    python3 -m venv venv
    ```
3. `venv/bin/pip install -r requirements.txt`
4. Run `venv/bin/python main.py`  
   Or using systemd
   ```
   [Unit]
   Description=Twigram - Telegram bot that forwards Twitter to Telegram
   After=syslog.target network-online.target nss-lookup.target

   [Service]
   Type=forking
   Environment=TOKEN=<telegram_token>
   Environment=INTERVAL=<polling_interval_in_seconds>
   Environment=TWITTER_USERNAME=<twitter_username>
   Environment=TWITTER_EMAIL=<twitter_email>
   Environment=TWITTER_PASSWORD=<twitter_password>
   Environment=TWITTER_COOKIE=<twitter_token>
   Environment=WEB_URL_ENABLE=<TRUE or FALSE>
   Environment=WEB_URL=<https_web_url>
   Environment=CERT_FILE=<cert file>
   Environment=KEY_FILE=<key file>
   Environment=PORT=8080
   Environment=PROCESS_COUNT=1
   Environment=DEBUG=false
   ExecStart=/bin/bash run.sh
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

### Deploy to fly.io

1. Clone this repo
2. Install `Docker`, `flyctl` and login to `fly.io`
3. Auth `registry.fly.io` for docker
    ```
    flyctl auth docker
    ```
4. Create a fly app
    ```
    app_name="your_app_name"
    flyctl apps create "${app_name}"
    ```
5. Build image locally, and push to fly
   ```
    docker build -t "${app_name}":latest .
    docker tag "${app_name}":latest registry.fly.io/"${app_name}":latest
    docker push registry.fly.io/"${app_name}":latest;
    ```
6. Deploy
    ```
    flyctl deploy --app "${app_name}" \
      --env "TOKEN=1423456789:AAAA" \
      --env "WEB_URL_ENABLE=<TRUE or FALSE>" \
      --env "WEB_URL=https://${app_name}.fly.dev" \
      --env "CERT_FILE=<cert file>" \
      --env "KEY_FILE=<key file>" \
      --env "PORT=8080" \
      --env "INTERVAL=30" \
      --env "TWITTER_COOKIE=" \
      --env "INTERVAL=<polling_interval_in_seconds>" \
      --env "TWITTER_USERNAME=<twitter_username>" \
      --env "TWITTER_EMAIL=<twitter_email>" \
      --env "TWITTER_PASSWORD=<twitter_password>" \
      --env "TWITTER_COOKIE=<twitter_token>" \
      --env "PROCESS_COUNT=1" \
      --env "DEBUG=false" \
      --image registry.fly.io/"${app_name}":latest
    ```

## References

This is based on former work:
- [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot)
- [twitter-api-client](https://github.com/trevorhobenshield/twitter-api-client)  
   The [forked](https://github.com/junyilou/twitter-api-client) version deprecated `asyncio.run`

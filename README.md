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
If you provide `WEB_URL` and `PORT`, the bot will run a webhook server for Telegram server to send updates.  
Otherwise, it will run a polling bot.  
As a webhook server, you must provide a https web with valid certificate, and can be accessed by Telegram server.

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
        -e INTERVAL=<interval_in_seconds> \
        -e TWITTER_USERNAME=<twitter_username> \
        -e TWITTER_EMAIL=<twitter_email> \
        -e TWITTER_PASSWORD=<twitter_password> \
        -e TWITTER_COOKIE=<twitter_token> \
        -e WEB_URL=<https_web_url> \
        -e PORT=8080 \
        -e DEBUG=false \
        twigram:latest
    ```

### Manually

1. Clone this repo
2. Create venv:
    ```
    python3 -m venv venv
    . venv/bin/activate
    ```
3. `pip install -r requirements.txt`
4. Run `python main.py`  
   Or using systemd
   ```
   [Unit]
   Description=Twigram - Telegram bot that forwards Twitter to Telegram
   After=syslog.target network-online.target nss-lookup.target

   [Service]
   Type=simple
   Environment=TOKEN=<telegram_token>
   Environment=INTERVAL=<interval_in_seconds>
   Environment=TWITTER_USERNAME=<twitter_username>
   Environment=TWITTER_EMAIL=<twitter_email>
   Environment=TWITTER_PASSWORD=<twitter_password>
   Environment=TWITTER_COOKIE=<twitter_token>
   Environment=WEB_URL=<https_web_url>
   Environment=PORT=8080
   Environment=DEBUG=false
   ExecStart=/path/to/venv/bin/python /path/to/main.py
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
      --env "WEB_URL=https://${app_name}.fly.dev" \
      --env "PORT=8080" \
      --env "INTERVAL=30" \
      --env "TWITTER_COOKIE=" \
      --env "INTERVAL=<interval_in_seconds>" \
      --env "TWITTER_USERNAME=<twitter_username>" \
      --env "TWITTER_EMAIL=<twitter_email>" \
      --env "TWITTER_PASSWORD=<twitter_password>" \
      --env "TWITTER_COOKIE=<twitter_token>" \
      --env "DEBUG=false" \
      --image registry.fly.io/"${app_name}":latest
    ```

## References

This is based on former work:
- [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot)
- [twitter-api-client](https://github.com/trevorhobenshield/twitter-api-client)  
   The [forked](https://github.com/junyilou/twitter-api-client) version deprecated `asyncio.run`

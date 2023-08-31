# Twigram

This projects aims to make a [Telegram](https://telegram.org) bot that forwards [Twitter](https://twitter.com/) to Telegram

## How to run

### Docker

1. Clone this repo
2. Build image:
    ```
    docker build -t twigram:latest .
    ```
3. Run container:
    ```
    docker run -d --network host \
        --name twigram --restart=al[docker-compose.yml](docker-compose.yml)ways \
        -e TOKEN=<telegram_token> \
        -e INTERVAL=<interval_in_seconds> \
        -e TWITTER_USERNAME=<twitter_username> \
        -e TWITTER_EMAIL=<twitter_email> \
        -e TWITTER_PASSWORD=<twitter_password> \
        -e TWITTER_COOKIE=<twitter_token> \
        -e DEBUG=false \
        twigram:latest
    ```
   You must provide a valid Telegram Bot TOKEN to run the bot, otherwise it will exit with error.  
   The username, email and password are optional.  
   **NOTE**: Credentials logins may be subject to risk control restrictions.  
   Or you can provide a cookie instead.
   Cookie format: `{"auth_token": "xxx", "ct0": "yyy"}`


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
   Environment=DEBUG=false
   ExecStart=/path/to/venv/bin/python /path/to/main.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

## References

This is based on former work:
- [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot)
- [twitter-api-client](https://github.com/trevorhobenshield/twitter-api-client)  
   The [forked](https://github.com/junyilou/twitter-api-client) version deprecated `asyncio.run`

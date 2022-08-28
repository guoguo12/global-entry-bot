# Global Entry Appointment Bot

A Twitter bot that announces open Global Entry interview slots.

Based largely on [oliversong/goes-notifier](https://github.com/oliversong/goes-notifier),
[mvexel/next_global_entry](https://github.com/mvexel/next_global_entry),
and [this comment](https://github.com/oliversong/goes-notifier/issues/5#issuecomment-336966190).

This project is (obviously) not affiliated with U.S. Customs and Border Protection.

## Installation

Install dependencies with

```
pip install -r requirements.txt
```

You will need to supply your Twitter API credentials. You can do this in two ways. The first is with environment variables:
```
CONSUMER_KEY=consumer_key CONSUMER_SECRET=consumer_secret ACCESS_TOKEN_KEY=access_token_key ACCESS_TOKEN_SECRET=access_token_secret python main.py
```

Or by providing a file with the credentials to the application using the `--credentials`/`-c` flag. The file is formatted in this way:
```
[twitter]
consumer_key = consumer_key
consumer_secret = consumer_secret
access_token_key = access_token_key
access_token_secret = access_token_secret
```

To check for new appointment slots, run `main.py`. I suggest automating this using Cron.

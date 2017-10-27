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

Then put your Twitter API credentials in a file called `secrets.py`, which should define `twitter_credentials`:

```python
twitter_credentials = dict(consumer_key='',
                           consumer_secret='',
                           access_token_key='',
                           access_token_secret='')
```

To check for new appointment slots, run `main.py`. I suggest automating this using Cron.

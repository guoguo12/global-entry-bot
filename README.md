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

## Usage

To check for new appointment slots, run `main.py`. The application accpes a `-h`/`--help` flag to see usage. I suggest automating this using Cron.

### Credentials

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
### Locations

You will need to supply what enrollment centers will be polled as command line arguments. You can poll as many as you wish. The format is as `NAME,CODE` comma-separated token. For instance, LAX is `LAX,5180` and SFO is `SFO,5001`. For instance:

```
python main.py A,B C,D
```

### Docker

A Dockerfile is supplied. It can be built with:
```
docker build -t global-entry-bot .
```

and run with e.g.

```
docker run --rm -v /host/path/to/twitter_credentials.ini:/config/twitter_credentials.ini global-entry-bot --verbose -c /config/twitter_credentials.ini SFO,5001
```

### TL;DR

Here's an example command to run the application:
```
python main.py -c /path/to/twitter/creds.ini LAX,5180
```

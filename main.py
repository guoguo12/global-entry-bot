import argparse
import configparser
from datetime import datetime, timedelta
import logging
import os
import sys
from typing import NamedTuple

import requests
import twitter


LOGGING_FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'

DELTA_WEEKS = 4

SCHEDULER_API_URL = 'https://ttp.cbp.dhs.gov/schedulerapi/locations/{location}/slots?startTimestamp={start}&endTimestamp={end}'
TTP_TIME_FORMAT = '%Y-%m-%dT%H:%M'

NOTIF_MESSAGE = 'New appointment slot open at {location}: {date}'
MESSAGE_TIME_FORMAT = '%A, %B %d, %Y at %I:%M %p'

class Location(NamedTuple):
    name: str
    code: int

    @staticmethod
    def parse(location_str):
        name, code = location_str.split(",")
        return Location(name, int(code))


class TwitterApiCredentials(NamedTuple):
    consumer_key: str
    consumer_secret: str
    access_token_key: str
    access_token_secret: str

    @staticmethod
    def from_file(credentials_file):
        with credentials_file:
            credentials_config = configparser.ConfigParser()
            credentials_config.read_file(credentials_file)

            if 'twitter' not in credentials_config:
                raise ValueError("Must provide credentials under 'twitter' heading")
            twitter_api_config = credentials_config['twitter']
            if set(twitter_api_config.keys()) != set(TwitterApiCredentials._fields):
                raise ValueError(f"credentials defined with fields '{','.join(TwitterApiCredentials._fields)}'")
            return TwitterApiCredentials(**twitter_api_config)

    @staticmethod
    def from_env():
        env_variables = tuple(field.upper() for field in TwitterApiCredentials._fields)
        if not all(v in os.environ for v in env_variables):
            msg = f"Expected environment variables { ', '.join(env_variables) } to be set"
            raise RuntimeError(msg)
        credentials = {field: os.environ[field.upper()] for field in TwitterApiCredentials._fields}
        return TwitterApiCredentials(**credentials)


class AppointmentTweeter(object):

    @staticmethod
    def from_credentials(credentials, test_mode=True):
        api = twitter.Api(
            consumer_key=credentials.consumer_key,
            consumer_secret=credentials.consumer_secret,
            access_token_key=credentials.access_token_key,
            access_token_secret=credentials.access_token_secret
        )
        return AppointmentTweeter(api, test_mode)

    def __init__(self, api, test_mode):
        self._test_mode = test_mode
        self._api = api

    def tweet(self, location_name, localized_time):
        timestamp = datetime.strptime(localized_time, TTP_TIME_FORMAT)
        message = NOTIF_MESSAGE.format(location=location_name,
                                        date=timestamp.strftime(MESSAGE_TIME_FORMAT))
        logging.info('Message: ' + message)
        if not self._test_mode:
            self._tweet(message)

    def _tweet(self, message):
        logging.info('Tweeting: ' + message)
        try:
            self._api.PostUpdate(message)
        except twitter.TwitterError as e:
            if len(e.message) == 1 and e.message[0]['code'] == 187:
                logging.info('Tweet rejected (duplicate status)')
            else:
                logging.exception('Error when communicating with Twitter API: %s', e.message[0]['message'])
                raise

def check_for_openings(location_name, location_code, appointment_tweeter):
    start = datetime.now()
    end = start + timedelta(weeks=DELTA_WEEKS)

    url = SCHEDULER_API_URL.format(location=location_code,
                                   start=start.strftime(TTP_TIME_FORMAT),
                                   end=end.strftime(TTP_TIME_FORMAT))
    try:
        results = requests.get(url).json()  # List of flat appointment objects
    except requests.ConnectionError:
        logging.exception('Could not connect to scheduler API')
        sys.exit(1)

    for result in results:
        if result['active'] > 0:
            logging.info('Opening found for {}'.format(location_name))

            appointment_tweeter.tweet(location_name, result['timestamp'])
            return  # Halt on first match

    logging.info('No openings for {}'.format(location_name))


def read_credentials(credentials_file):
    if credentials_file:
        logging.info('Loading twitter credentials from file')
        return TwitterApiCredentials.from_file(credentials_file)
    else:
        logging.info('Loading twitter credentials from env')
        return TwitterApiCredentials.from_env()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', '-t', action='store_true', default=False)
    parser.add_argument('--verbose', '-v', action='store_true', default=False)
    parser.add_argument('--credentials', '-c', type=argparse.FileType('r'),
                        help='File with Twitter API credentials [default: use ENV variables]')
    parser.add_argument('locations', nargs='+', metavar='NAME,CODE', type=Location.parse,
                        help="Locations to check, as a name and code (e.g. 'SFO,5446')")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format=LOGGING_FORMAT,
                            level=logging.INFO,
                            stream=sys.stdout)

    credentials = read_credentials(args.credentials)
    tweeter = AppointmentTweeter.from_credentials(credentials, args.test)

    logging.info('Starting checks (locations: {})'.format(len(args.locations)))
    for location_name, location_code in args.locations:
        check_for_openings(location_name, location_code, tweeter)

if __name__ == '__main__':
    main()

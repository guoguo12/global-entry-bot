import argparse
import configparser
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from functools import cache, cached_property
import itertools
import logging
import os
import sys
from zoneinfo import ZoneInfo

import requests
import twitter


LOGGING_FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'

START_TIME_UTC = datetime.now(timezone.utc)
END_TIME_UTC = START_TIME_UTC + timedelta(weeks=12)

LOCATION_DETAIL_URL = 'https://ttp.cbp.dhs.gov/schedulerapi/locations/'
SCHEDULER_API_URL = 'https://ttp.cbp.dhs.gov/schedulerapi/locations/{location}/slots?startTimestamp={start}&endTimestamp={end}'
TTP_TIME_FORMAT = '%Y-%m-%dT%H:%M'

NOTIF_MESSAGE = 'New appointment slot open at {location}: {date}'
MESSAGE_TIME_FORMAT = '%A, %B %d, %Y at %I:%M %p'


@cache
def _location_details():
    try:
        results = requests.get(LOCATION_DETAIL_URL).json()
    except requests.ConnectionError:
        logging.exception('Could not connect to location details endpoint')
        raise
    return {
        location_detail['id']: location_detail
        for location_detail in results
        if 'id 'in location_detail
    }


@dataclass(frozen=True)
class Location:
    name: str
    code: int

    @staticmethod
    def parse(location_str):
        name, code = location_str.split(",")
        return Location(name, int(code))

    @cached_property
    def timezone(self):
        tz_string = _location_details().get('tzData', 'UTC')
        return ZoneInfo(tz_string)


@dataclass(frozen=True)
class Appointment:
    location: Location
    time: datetime

    @cached_property
    def human_readable_time(self):
        return self.time.strftime(MESSAGE_TIME_FORMAT)


@dataclass(frozen=True)
class TwitterApiCredentials:
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
            if set(twitter_api_config.keys()) != set(TwitterApiCredentials.fields()):
                raise ValueError(f"credentials defined with fields '{','.join(TwitterApiCredentials.fields())}'")
            return TwitterApiCredentials(**twitter_api_config)

    @staticmethod
    def from_env():
        env_variables = tuple(field.upper() for field in TwitterApiCredentials.fields())
        if not all(v in os.environ for v in env_variables):
            msg = f"Expected environment variables { ', '.join(env_variables) } to be set"
            raise RuntimeError(msg)
        credentials = {field: os.environ[field.upper()] for field in TwitterApiCredentials.fields()}
        return TwitterApiCredentials(**credentials)

    @staticmethod
    def fields():
        return [field.name for field in fields(TwitterApiCredentials)]


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

    @staticmethod
    def _compose_message(appointment):
        return NOTIF_MESSAGE.format(location=appointment.location.name,
                                    date=appointment.human_readable_time)

    def tweet(self, appointment):
        message = self._compose_message(appointment)
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


def get_appointments(location):
    start = START_TIME_UTC.astimezone(location.timezone)
    end = END_TIME_UTC.astimezone(location.timezone)

    url = SCHEDULER_API_URL.format(location=location.code,
                                   start=start.strftime(TTP_TIME_FORMAT),
                                   end=end.strftime(TTP_TIME_FORMAT))
    try:
        results = requests.get(url).json()  # List of flat appointment objects
    except requests.ConnectionError:
        logging.exception('Could not connect to scheduler API')
        raise

    active_slots = [result for result in results if result.get('active', 0) > 0]
    logging.info('Found %s appointments at %s', len(active_slots), location.name)

    for result in active_slots:
        appointment_time = datetime.strptime(result['timestamp'], TTP_TIME_FORMAT).replace(tzinfo=location.timezone)
        appointment = Appointment(location, appointment_time)
        logging.info('Appointment found in %s at %s', location.name, appointment.human_readable_time)
        yield appointment


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
    appointments = itertools.chain.from_iterable(
        get_appointments(location) for location in args.locations
    )
    for appointment in appointments:
        tweeter.tweet(appointment)


if __name__ == '__main__':
    main()

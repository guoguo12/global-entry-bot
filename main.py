import argparse
from datetime import datetime, timedelta
import logging
import sys
from typing import NamedTuple

import requests
import twitter

from secrets import twitter_credentials

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


class AppointmentTweeter(object):

    def __init__(self, test_mode, consumer_key, consumer_secret, access_token_key, access_token_secret):
        self._test_mode = test_mode
        self._api = twitter.Api(
            consumer_key=consumer_key, consumer_secret=consumer_secret,
            access_token_key=access_token_key, access_token_secret=access_token_secret
        )

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
                raise


def check_for_openings(location_name, location_code, test_mode=True):
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

    appointment_tweeter = AppointmentTweeter(test_mode=test_mode, **twitter_credentials)

    for result in results:
        if result['active'] > 0:
            logging.info('Opening found for {}'.format(location_name))

            appointment_tweeter.tweet(location_name, result['timestamp'])
            return  # Halt on first match

    logging.info('No openings for {}'.format(location_name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', '-t', action='store_true', default=False)
    parser.add_argument('--verbose', '-v', action='store_true', default=False)
    parser.add_argument('locations', nargs='+', metavar='NAME,CODE', type=Location.parse,
                        help="Locations to check, as a name and code (e.g. 'SFO,5446')")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format=LOGGING_FORMAT,
                            level=logging.INFO,
                            stream=sys.stdout)

    logging.info('Starting checks (locations: {})'.format(len(args.locations)))
    for location_name, location_code in args.locations:
        check_for_openings(location_name, location_code, args.test)

if __name__ == '__main__':
    main()

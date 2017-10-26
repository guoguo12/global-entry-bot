import argparse
from datetime import datetime, timedelta

import requests
import twitter

from secrets import twitter_credentials

LOCATIONS = [
    ('SFO', 5446)
]

DELTA = 4  # Weeks

SCHEDULER_API_URL = 'https://ttp.cbp.dhs.gov/schedulerapi/locations/{location}/slots?startTimestamp={start}&endTimestamp={end}'
TTP_TIME_FORMAT = '%Y-%m-%dT%H:%M'

NOTIF_MESSAGE = 'New appointment slot open at {location}: {date}'
MESSAGE_TIME_FORMAT = '%A, %B %d, %Y at %I:%M %p'

def tweet(message):
    api = twitter.Api(**twitter_credentials)
    api.PostUpdate(message)

def check_for_openings(location_name, location_code, test_mode=True):
    start = datetime.now()
    end = start + timedelta(weeks=DELTA)

    url = SCHEDULER_API_URL.format(location=location_code,
                                   start=start.strftime(TTP_TIME_FORMAT),
                                   end=end.strftime(TTP_TIME_FORMAT))
    results = requests.get(url).json()  # List of flat appointment objects

    for result in results:
        if result['active'] > 0:
            timestamp = datetime.strptime(result['timestamp'], TTP_TIME_FORMAT)
            message = NOTIF_MESSAGE.format(location=location_name,
                                           date=timestamp.strftime(MESSAGE_TIME_FORMAT))
            if test_mode:
                print(message)
            else:
                tweet(message)
            return  # Halt on first match

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', default=False)
    args = parser.parse_args()

    for location_name, location_code in LOCATIONS:
        check_for_openings(location_name, location_code, args.test)

if __name__ == '__main__':
    main()

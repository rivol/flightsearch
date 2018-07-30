#!/usr/bin/env python3

from datetime import datetime

import click
import requests


@click.command()
@click.argument('url')
def booking_info(url: str):
    """ Takes URL of Kiwi booking info API and prints out nicely formatted brief info """

    print("Fetching data...")
    r = requests.get(url)
    r.raise_for_status()
    data: dict = r.json()

    print(f"Kiwi booking {data['bid']}")

    for flight_data in data['flights']:
        # TODO: datetime.utcfromtimestamp() works here and .fromtimestamp() doesn't... but not 100% sure it's correct...
        dep_time = datetime.utcfromtimestamp(flight_data['departure']['when']['local'])
        arr_time = datetime.utcfromtimestamp(flight_data['arrival']['when']['local'])
        dep_airport = flight_data['departure']['where']['code']
        arr_airport = flight_data['arrival']['where']['code']
        full_flight_no = f"{flight_data['airline']['iata']}-{flight_data['flight_no']}"

        print(f"- {dep_time.strftime('%a %m-%d  %H:%M')} - {arr_time.strftime('%H:%M')}: "
              f"flight {dep_airport}-{arr_airport}  "
              f"{full_flight_no:7s} ({flight_data['airline']['name']}); "
              f"{flight_data['reservation_number']}")


if __name__ == '__main__':
    booking_info()

#!/usr/bin/env python3

from datetime import date, datetime
from typing import List, Dict

import click
import iso8601

from kiwi import KiwiApi, Journey, Hop


def format_time(secs: int) -> str:
    h = int(secs / 3600)
    m = int(secs / 60 % 60)
    return f"{h:2d}h{m:02d}"


def print_hops(title: str, hops: List[Hop], airlines_names: Dict[str, str]):
    print(title)
    for hop in hops:
        print(f"    {hop.dep_time.isoformat(' ')}  {hop.dep_airport} - {hop.arr_airport}  {hop.arr_time.isoformat(' ')}"
              f"  - {format_time(hop.duration_secs)} {airlines_names[hop.airline_id]}")


def print_journey(journey: Journey, airlines_names: Dict[str, str]):
    flights_short = ','.join(f'{flight.dep_airport}-{flight.arr_airport}' for flight in journey.flights)
    print(f"### {flights_short}  {journey.price:.0f}€  {format_time(journey.duration_secs)}")
    if hasattr(journey, '_score_components'):
        print(f"    S:  {sum(journey._score_components):.0f} = {' + '.join('%.0f' % s for s in journey._score_components)}")

    for flight in journey.flights:
        title = f"  # {flight.dep_time.isoformat(' ')}  {flight.dep_airport} - {flight.arr_airport}  {flight.arr_time.isoformat(' ')}" \
                f"  - {format_time(flight.duration_secs)}" \
                f"  {flight.price:.0f}€"
        print_hops(title, flight.hops, airlines_names)
        print()

    # print('-' * 100)


def print_journey_summaries(journeys: List[Journey], sort: bool = True) -> None:
    if sort:
        journeys = sort_journeys(journeys)

    for journey in journeys:
        assert hasattr(journey, '_score_components')

        score = sum(journey._score_components)
        flights_short = ','.join(f'{flight.dep_airport}-{flight.arr_airport}' for flight in journey.flights)
        print(f"S: {score:.0f}  |  {journey.price:4.0f} €  |  {format_time(journey.duration_secs)}  |  {flights_short}")


def journey_score(journey: Journey) -> float:
    hourly_cost = 15
    ext_hourly_cost = 2*hourly_cost
    airport_costs = {
        'HEL': 20 + 20 + 10 + 4*ext_hourly_cost,    # boat + local transport + food
        'RIX': 25 + 5 + 5 + 5*ext_hourly_cost,      # bus + local transport + food
    }

    score_components = [
        journey.price,
        airport_costs.get(journey.flights[0].dep_airport, 0),
        airport_costs.get(journey.flights[-1].arr_airport, 0),
        journey.duration_secs / 3600 * hourly_cost,
    ]

    setattr(journey, '_score_components', score_components)
    return sum(score_components)


def sort_journeys(journeys: List[Journey]) -> List[Journey]:
    return sorted(journeys, key=journey_score)


@click.group()
def cli():
    pass


@cli.command()
def main():
    api = KiwiApi()
    departureDates = (date(2018, 8, 19), date(2018, 8, 22))
    returnDates = (date(2018, 9, 3), date(2018, 9, 10))
    finalDates = (date(2018, 9, 15), date(2018, 9, 25))
    intermediate_airports = [
        'PNH',  # Phnom Penh, CM
        'MNL',  # Manila, PH
        'PPS',  # Palawan island, PH
        'SIN',  # Singapore, SN
        'BKK',  # Bangkok, TH
        'HKT',  # Phuket City, TH
        'CNX',  # Chiang Mai, TH
        'HAN',  # Hanoi, VN
        'DAD',  # Da Nang, VN
        'SGN',  # HCMC, VN
    ]

    airlines_names = api.airline_names()

    # journeys = api.flights('TLL,HEL,RIX', 'SYD', departureDates, returnDates, maxFlyDuration=36)

    all_journeys = []
    for intermediate_airport in intermediate_airports:
        journeys = api.flights_multi([
            {'from': 'TLL,HEL,RIX', 'to': 'SYD', 'dates': departureDates, 'maxFlyDuration': 32},
            {'from': 'MEL', 'to': intermediate_airport, 'dates': returnDates},
            {'from': intermediate_airport, 'to': 'TLL,HEL,RIX', 'dates': finalDates},
            # {'from': 'melbourne_vi_au', 'to': 'TLL,HEL,RIX', 'dates': returnDates},
        ], maxFlyDuration=32)

        print(f"{'-' * 50}  via {intermediate_airport}  {'-' * 50}")
        print(f"Found {len(journeys)} journeys")
        journeys = sort_journeys(journeys)
        for journey in journeys[:2]:
            print_journey(journey, airlines_names)

        all_journeys.append(journeys)

    print()
    print("SUMMARIES:")
    print_journey_summaries([journeys[0] for journeys in all_journeys if journeys])


@cli.command()
@click.argument('fly_from')
@click.argument('fly_to')
@click.argument('departure_date')
@click.argument('return_date')
def single(fly_from, fly_to, departure_date, return_date):
    departure_dt = iso8601.parse_date(departure_date)
    return_dt = iso8601.parse_date(return_date) if return_date else None

    api = KiwiApi()
    airlines_names = api.airline_names()
    journeys = api.flights(fly_from, fly_to, (departure_dt, departure_dt), (return_dt, return_dt))

    print(f"Found {len(journeys)} journeys; top 3:")
    journeys = sort_journeys(journeys)
    for journey in journeys[:2]:
        print_journey(journey, airlines_names)


if __name__ == '__main__':
    cli()

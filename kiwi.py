import json
from datetime import date, datetime
from typing import Tuple, Dict, List

import attr
import redis
import requests


@attr.s
class Hop:
    dep_airport: str = attr.ib()
    arr_airport: str = attr.ib()

    dep_time: datetime = attr.ib()
    arr_time: datetime = attr.ib()
    dep_time_utc: datetime = attr.ib()
    arr_time_utc: datetime = attr.ib()

    airline_id: str = attr.ib()

    @property
    def duration_secs(self) -> float:
        return (self.arr_time_utc - self.dep_time_utc).total_seconds()


@attr.s
class Flight:
    hops: List[Hop] = attr.ib()

    price: float = attr.ib()

    @property
    def duration_secs(self) -> float:
        return (self.arr_time_utc - self.dep_time_utc).total_seconds()

    @property
    def dep_airport(self):
        return self.hops[0].dep_airport

    @property
    def arr_airport(self):
        return self.hops[-1].arr_airport

    @property
    def dep_time(self):
        return self.hops[0].dep_time

    @property
    def dep_time_utc(self):
        return self.hops[0].dep_time_utc

    @property
    def arr_time(self):
        return self.hops[-1].arr_time

    @property
    def arr_time_utc(self):
        return self.hops[-1].arr_time_utc


@attr.s
class Journey:
    flights: List[Flight] = attr.ib()

    @property
    def duration_secs(self) -> float:
        return sum(flight.duration_secs for flight in self.flights)

    @property
    def price(self) -> float:
        return sum(flight.price for flight in self.flights)


class KiwiApi:
    BASE_URL = 'https://api.skypicker.com'
    DATE_FMT = '%d/%m/%Y'

    def __init__(self) -> None:
        super().__init__()
        self.cache = redis.StrictRedis(host='localhost', port=6379, db=0)

    def flights(self, flyFrom: str, flyTo: str, departureDates: Tuple[date, date], returnDates: Tuple[date, date], *,
                maxFlyDuration: int = None) \
            -> List[Journey]:
        data = self.flights_data(flyFrom, flyTo, departureDates, returnDates, maxFlyDuration=maxFlyDuration)

        journeys = [self.convert_single_flight(flight_data) for flight_data in data['data']]
        return journeys

    def flights_data(self, flyFrom: str, flyTo: str, departureDates: Tuple[date, date], returnDates: Tuple[date, date], *,
                maxFlyDuration: int = None) \
            -> dict:
        params = {
            'partner': 'picky',
            'flyFrom': flyFrom,
            'to': flyTo,
            'dateFrom': departureDates[0].strftime(self.DATE_FMT),
            'dateTo': departureDates[1].strftime(self.DATE_FMT),
            'returnFrom': returnDates[0].strftime(self.DATE_FMT),
            'returnTo': returnDates[1].strftime(self.DATE_FMT),
            'typeFlight': 'round',
        }
        if maxFlyDuration is not None:
            params['maxFlyDuration'] = maxFlyDuration

        return self.request('get', f'{self.BASE_URL}/flights', params=params)

    def flights_multi(self, flight_params: List[dict], maxFlyDuration: int = None) -> List[Journey]:
        data = self.flights_multi_data(flight_params, maxFlyDuration=maxFlyDuration)

        journeys = [self.convert_multi_flight_journey(journey_data) for journey_data in data]
        return journeys

    def flights_multi_data(self, flight_params: List[dict], maxFlyDuration: int = None) -> dict:
        data = []
        for flight in flight_params:
            flight_dates = flight.pop('dates')
            params = {
                'flyFrom': flight.pop('from'),
                'to': flight.pop('to'),
                'dateFrom': flight_dates[0].strftime(self.DATE_FMT),
                'dateTo': flight_dates[1].strftime(self.DATE_FMT),
                'typeFlight': 'oneway',
            }
            if maxFlyDuration is not None:
                params['maxFlyDuration'] = maxFlyDuration
            params.update(flight)

            data.append(params)

        data = {'requests': data}
        print(data)
        return self.request('post', f'{self.BASE_URL}/flights_multi', data=data)

    def airline_names(self) -> Dict[str, str]:
        airlines: list = self.request('GET', f'{self.BASE_URL}/airlines')
        return {airline['id']: airline['name'] for airline in airlines}

    def request(self, method: str, url: str, *, params: dict = None, data: object = None) -> dict:
        print(f"Request: {method} {url}...")
        cache_key = json.dumps([method, url, params, data], sort_keys=True)
        response = self.cache.get(cache_key)
        if response is not None:
            print("  ... cache hit!")
            return json.loads(response)

        r = requests.request(method, url, params=params, json=data)
        print(f"  ... done: {r.status_code}")
        if 400 <= r.status_code < 600:
            print("ERROR:", r.text)
            r.raise_for_status()

        response = r.json()
        self.cache.set(cache_key, json.dumps(response), 3600)
        return response

    def convert_single_flight(self, data: dict) -> Journey:
        hops_a_data = [h for h in data['route'] if h['return'] == 0]
        hops_b_data = [h for h in data['route'] if h['return'] == 1]
        hops_a = [self.convert_hop(d) for d in hops_a_data]
        hops_b = [self.convert_hop(d) for d in hops_b_data]

        price = float(data['price'])
        flights = [
            Flight(hops=hops_a, price=price / 2),
            Flight(hops=hops_b, price=price / 2),
        ]

        return Journey(flights=flights)

    def convert_multi_flight_journey(self, data: dict) -> Journey:
        flights = []
        for flight_data in data['route']:
            hops = [self.convert_hop(d) for d in flight_data['route']]
            flights.append(Flight(hops=hops, price=flight_data['price']))

        return Journey(flights=flights)

    def convert_hop(self, data: dict) -> Hop:
        return Hop(
            dep_airport=data['flyFrom'], arr_airport=data['flyTo'],
            dep_time=datetime.fromtimestamp(data['dTime']), dep_time_utc=datetime.fromtimestamp(data['dTimeUTC']),
            arr_time=datetime.fromtimestamp(data['aTime']), arr_time_utc=datetime.fromtimestamp(data['aTimeUTC']),
            airline_id=data['airline'],
        )

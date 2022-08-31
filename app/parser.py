from datetime import datetime
import json
import re
import requests
import os
from time import strptime, mktime
from datetime import datetime

from redis import Redis
from redis import asyncio as aioredis
import asyncio
import aiohttp


DB_HOURS = {
    'H_7': 1,
    'H_19': 2
}


class EmptyLegsParser:
    
    def __init__(self) -> None:
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': os.environ.get('API_TOKEN')
        }
        self.current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
        self.current_hour = f'H_{datetime.now().strftime("%H")}'
        
        self.get_availabilities()

    def get_availabilities(self) -> None:
        asyncio.run(self.get_availabilities_async())
    
    async def get_availabilities_async(self) -> None:
        redis = aioredis.from_url(url='redis://redis_service',
                                       port=6379,
                                       db=DB_HOURS.get(self.current_hour),
                                       encoding='utf-8',
                                       decode_responses=True)

        # Clear old data
        await redis.flushdb()

        # Page number count
        request_url = f'https://dir.aviapages.com/api/availabilities/?from_date_utc={self.current_time}'
        request = requests.get(url=request_url, headers=self.headers)
        if request.status_code == 200:
            request_json = request.json()
            if request_json.get('count') > 0:
                page_count = request_json.get('count') // request_json.get('per_page') + 1
                async with aiohttp.ClientSession(headers=self.headers, trust_env=True) as session:
                    tasks = []
                    for i in range(page_count):
                        tasks.append(asyncio.create_task(self.parse_availabilities_page(i, session, redis)))
                    await asyncio.gather(*tasks)
                    await redis.close()

    
    async def parse_availabilities_page(self, page_number: int, session, redis) -> None:
        request_url = f'https://dir.aviapages.com/api/availabilities/?from_date_utc={self.current_time}&page={page_number}'
        async with session.get(request_url) as request:
            if request.status == 200:
                request_json = await request.json()
                if request_json.get('count') > 0:
                    for result in request_json.get('results'):
                        date_from_struct = strptime(result.get('from_date_utc'), '%Y-%m-%dT%H:%M')
                        date_from = datetime.fromtimestamp(mktime(date_from_struct)).strftime('%d.%b')
                        date_to_struct = strptime(result.get('to_date_utc'), '%Y-%m-%dT%H:%M')
                        date_to = datetime.fromtimestamp(mktime(date_to_struct)).strftime('%d.%b')

                        value = json.dumps({
                            'aircraft_type': result.get('aircraft_type'),
                            'company': result.get('company'),
                            'dates': f'{date_from}-{date_to}',
                            'dep_airport_icao': result.get('dep_airport_icao'),
                            'arrival_airport_icao': result.get('arrival_airport_icao'),
                            'comment': result.get('comment')
                        })
                        
                        await redis.lpush(self.current_hour, value)

    def get_new_availabilities(self) -> list:
        new_availabilities = []
        current_redis = Redis.from_url(url='redis://redis_service',
                                        port=6379,
                                        db=DB_HOURS.get(self.current_hour),
                                        encoding='utf-8',
                                        decode_responses=True)        
        
        previous_hour = 'H_7' if self.current_hour == 'H_19' else 'H_19'
        previous_redis = Redis.from_url(url='redis://redis_service',
                                        port=6379,
                                        db=DB_HOURS.get(previous_hour),
                                        encoding='utf-8',
                                        decode_responses=True)
        
        # Iterating over current period of time
        for key in current_redis.scan_iter():
            for value in current_redis.lrange(key, 0, current_redis.llen(key)):
                
                data_found = False
                
                # Iterating over previous period of time
                for key2 in previous_redis.scan_iter():
                    for value2 in previous_redis.lrange(key2, 0, previous_redis.llen(key2)):
                        if value == value2:
                            data_found = True
                            break
                    if data_found:
                        break

                if not data_found:
                    new_availabilities.append(json.loads(value))
                
        return new_availabilities

if __name__ == '__main__':
    print('Only for import!')

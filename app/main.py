from parser import EmptyLegsParser
import requests
import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

LINES_LIMIT=30


def main():

    parser = EmptyLegsParser()

    availabilities = parser.get_new_availabilities()

    messages = generate_messages(availabilities)
    for message in messages:
        api_request = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&parse_mode=HTML&text={message}'
        requests.get(api_request)


def generate_messages(availabilities: list) -> list:
    messages = []
    
    count = 0
    message = ''
    
    for empty_leg in availabilities:
        
        comment = '' if empty_leg.get("comment") == None else empty_leg.get("comment")
        
        message += f'<b>{empty_leg.get("aircraft_type")}</b> {empty_leg.get("company")}, {empty_leg.get("dates")}, <b>{empty_leg.get("dep_airport_icao")}-{empty_leg.get("arrival_airport_icao")}</b> <i>{comment}</i>%0A'
        count += 1
        if count == LINES_LIMIT:
            count = 0
            messages.append(message)
            message = ''
    
    if count > 0:
        messages.append(message)
            
    return messages


if __name__ == '__main__':
    main()
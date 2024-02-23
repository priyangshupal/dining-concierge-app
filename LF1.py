import boto3
import datetime
import dateutil.parser
import json
import logging
import math
import os
import time
from botocore.vendored import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


""" --- Functions that control the bot's behavior --- """


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


def lambda_handler(event, context):
    # TODO implement
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)


def dispatch(intent_request):
    logger.debug(
        'dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    intent_name = intent_request['currentIntent']['name']
    
    if intent_name == 'SuggestRestaurant':
        return dining_suggestion_intent(intent_request)
    elif intent_name == "PreviousReco":
        return previous_reco_intent(intent_request)
    

    raise Exception('Intent with name ' + intent_name + ' not supported')



def validate_dining_suggestion(location, cuisine, num_people, date, time):
# Check if location is Valid.
    locs = ["manhattan"]
    if location is not None and location.lower() not in locs:
        return build_validation_result(False,
                                      'Location',
                                      'Location not supported. Please try one of the five boroughs')

# Checking if Valid Cuisine
    cuisines = ['italian', 'chinese', 'indian']
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                      'Cuisine',
                                      'Cuisine not available. Please try another cuisine')

# Check if the count of people is Under 20. Capping Table size at 20
    if num_people is not None:
        num_people = int(num_people)
        if num_people > 20 or num_people < 0:
            return build_validation_result(False,
                                           'NumberOfPeople',
                                           'Maximum 20 people allowed. Try again')
# Check if the date is valid
    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date',
                                           'I did not understand that, what date would you like to book?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'Date', 'Sorry Invalid Date, please enter a valid date')

# Check if the time is valid 
    if time is not None:
        
        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
        
            return build_validation_result(False, 'Time', 'Not a valid time')

        if hour < 10 or hour > 20:
            # Outside of business hours
            return build_validation_result(False, 'Time',
                                           'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    return build_validation_result(True, None, None)

def previous_reco_intent(intent_request):
        
    email = intent_request['userId']
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='restaurant-request')
    msg = {"email": email}
    response = queue.send_message(
    MessageAttributes={
    'email': {
                    'DataType': 'String',
                    'StringValue': email
    }},
            MessageBody=json.dumps(msg),
    )
    return close(intent_request['sessionAttributes'],
                'Fulfilled',
                {'contentType': 'PlainText',
                'content': 'Thank you! You will recieve the suggestion shortly'})


    

        

def dining_suggestion_intent(intent_request):
    location = get_slots(intent_request)["Location"]
    cuisine = get_slots(intent_request)["Cuisine"]
    num_people = get_slots(intent_request)["TableSize"]
    date = get_slots(intent_request)["Date"]
    time = get_slots(intent_request)["Time"]
    email = get_slots(intent_request)["Email"]
    source = intent_request['invocationSource']
    print(source)
    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)

        validation_result = validate_dining_suggestion(location, cuisine, num_people, date, time)

        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        
        if intent_request[
            'sessionAttributes'] is not None:
            output_session_attributes = intent_request['sessionAttributes']
        else:
            output_session_attributes = {}

        return delegate(output_session_attributes, get_slots(intent_request))
    
    if source  == "FulfillmentCodeHook":
        if cuisine is not None and email is not None and location is not None:
            sqs = boto3.resource('sqs')
            queue = sqs.get_queue_by_name(QueueName='restaurant-request')
            msg = {"cuisine": cuisine, "email": email, "location": location, "time": time, "num_people": num_people, "date": date}
            response = queue.send_message(
                MessageAttributes={
                    'cuisine': {
                        'DataType': 'String',
                        'StringValue': cuisine
                    },
                    'email': {
                        'DataType': 'String',
                        'StringValue': email
                    },
                    'location': {
                        'DataType': 'String',
                        'StringValue': location
                    },
                    'time': {
                        'DataType': 'String',
                        'StringValue': time
                    },
                    'num_people': {
                        'DataType': 'String',
                        'StringValue': num_people
                    },
                    'date': {
                        'DataType': 'String',
                        'StringValue': date
                    }
                },
                MessageBody=json.dumps(msg),
            )
            
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thank you! You will recieve the suggestion shortly'})

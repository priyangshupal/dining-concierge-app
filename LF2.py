import boto3
import json
import requests
from requests.auth import HTTPBasicAuth
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    poll_sqs()

def search_recommendation(cuisine):
  url = 'https://search-yelp-restaurants-stdbh4kdqgmea75qrmmfw3wv2q.aos.us-east-1.on.aws/restaurants/_search'
  headers = {"Content-Type": "application/json"}
  body = {
    "size": 3,
    "query": {
        "bool": {
            "must": [
                { "match": { "cuisine": cuisine }}
            ]
        }
    }
  }

  response = requests.get(
    url,
    data=json.dumps(body),
    headers=headers,
    auth=HTTPBasicAuth('pp2833', 'Elastic@123')
  )
  if response.status_code == 200:
    recommendation = response.json()['hits']['hits']
    if len(recommendation) > 0:
      restaurants = []
      for restaurant_source in recommendation:
        restaurants.append(restaurant_source['_source']['restaurantID'])
      return restaurants
    else:
      print('No record found')
  else:
    print('Error while calling Elastic Search')

def scan_dynamo(restaurantIDs):
  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('yelp-restaurants')
  restaurants = []
  for restaurantID in restaurantIDs:
    response = table.query(KeyConditionExpression=Key('id').eq(restaurantID))
    restaurants.append({
      'address': response['Items'][0]['address'],
      'name': response['Items'][0]['name'],
    })
  return restaurants

def suggest_restaurant(cuisine):
  restaurantIDs = search_recommendation(cuisine)
  restaurants = scan_dynamo(restaurantIDs)
  return restaurants

def send_email_prev(previous_recommendation, email):
  if previous_recommendation != '' and email != '':
    client = boto3.client('ses')
    response = client.send_email(
      Source='pp2833@nyu.edu',
      Destination={
        'ToAddresses': [ email ]
      },
      Message={
        'Subject': {
          'Data': 'Your restaurant recommendations',
          'Charset': 'UTF-8'
        },
        'Body': {
          'Text': {
            'Data': previous_recommendation,
            'Charset': 'UTF-8'
          }
        }
      }
    )  

def send_email(restaurants, email, cuisine, num_people, date, time):
  client = boto3.client('ses')    
  messageBody = f"Hello! Here are my {cuisine} restaurant suggestions for {num_people} people, for {date} at {time}:\n"
  for idx, restaurant in enumerate(restaurants):
    messageBody += f"{idx + 1}. {restaurant['name']}, located at {restaurant['address']}\n"
  
  add_past_recommendation(email, messageBody)
  
  response = client.send_email(
    Source='pp2833@nyu.edu',
    Destination={
      'ToAddresses': [ email ]
    },
    Message={
      'Subject': {
        'Data': 'Your restaurant recommendations',
        'Charset': 'UTF-8'
      },
      'Body': {
        'Text': {
          'Data': messageBody,
          'Charset': 'UTF-8'
        }
      }
    }
  )

def add_past_recommendation(email, emailContent):
  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('past-recommendations')
  dynamoItem = {
    'email': email,
    'past_recommendation': emailContent
  }
  table.put_item(Item=dynamoItem)

def get_previous_recommendation(email):
  response = ""
  if email is not None:
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('past-recommendations')
    past_recommendation = table.get_item(TableName='past-recommendations', Key={'email': email})
    response = past_recommendation['Item']['past_recommendation'] + '\n'
  return response

def poll_sqs():
  session = boto3.session.Session()
  client = session.client('sqs', region_name='us-east-1')
  queues = client.list_queues(QueueNamePrefix='restaurant-request')
  queueUrl = queues['QueueUrls'][0]
  response = client.receive_message(
      QueueUrl=queueUrl,
      AttributeNames=['All'],
      MaxNumberOfMessages=10,
      MessageAttributeNames=['All'],
      VisibilityTimeout=30,
      WaitTimeSeconds=0
  )
  if 'Messages' in response:
    for message in response['Messages']:
      messages_attributes = message.get('MessageAttributes')
      if ('previousReco' in messages_attributes):
        email = messages_attributes.get('previousReco').get('StringValue')
        previous_recommendation = get_previous_recommendation(email)
        send_email_prev(previous_recommendation, email)
      else:
        cuisine = messages_attributes.get('cuisine').get('StringValue')
        email = messages_attributes.get('email').get('StringValue')
        date = messages_attributes.get('date').get('StringValue')
        time = messages_attributes.get('time').get('StringValue')
        num_people = messages_attributes.get('num_people').get('StringValue')
        send_email(suggest_restaurant(str(cuisine).lower()), email, cuisine, num_people, date, time)
      delete_response = client.delete_message(
        QueueUrl=queueUrl,
        ReceiptHandle=message.get('ReceiptHandle')
      )
  else:
    print('No messages in queue')

poll_sqs()
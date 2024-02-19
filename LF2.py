import boto3
import json
import requests
from functions import read_secret
from requests.auth import HTTPBasicAuth
from boto3.dynamodb.conditions import Key

def search_recommendation(cuisine):
  url = 'https://search-yelp-6o3kvujuuy2tkt6rcjrei6o4wq.aos.us-east-1.on.aws/restaurants/_search'
  headers = {"Content-Type": "application/json"}
  body = {
    "size": 1,
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
    auth=HTTPBasicAuth(read_secret('elasticsearch_user'), read_secret('elasticsearch_password'))
  )
  if response.status_code == 200:
    recommendation = response.json()['hits']['hits']
    if len(recommendation) > 0:
      return recommendation[0]['_source']['restaurantID']
    else:
      print('No record found')
  else:
    print('Error while calling Elastic Search')

def scan_dynamo(restaurantID):
  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('yelp-restaurants')
  response = table.query(KeyConditionExpression=Key('id').eq(restaurantID))
  return response.get('Items')[0]

def suggest_restaurant(cuisine):
  restaurantID = search_recommendation(cuisine)
  restaurant = scan_dynamo(restaurantID)
  return restaurant

def send_email(restaurant, email):
  client = boto3.client('ses')
  response = client.send_email(
    Source=read_secret('source_email'),
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
          'Data': 'Your recommended restaurant is: ' + restaurant,
          'Charset': 'UTF-8'
        }
      }
    }
  )

def poll_sns():
  client = boto3.client('sqs', region_name='us-east-1')
  queues = client.list_queues(QueueNamePrefix='Q1')
  queueUrl = queues['QueueUrls'][0]
  response = client.receive_message(
      QueueUrl=queueUrl,
      AttributeNames=['All'],
      MaxNumberOfMessages=10,
      MessageAttributeNames=['All'],
      VisibilityTimeout=30,
      WaitTimeSeconds=0
  )
  for message in response['Messages']:
    messages_attributes = message.get('MessageAttributes')
    cuisine = messages_attributes.get('cuisine')
    email = messages_attributes.get('email')
  
  send_email(suggest_restaurant(cuisine), email)

poll_sns()
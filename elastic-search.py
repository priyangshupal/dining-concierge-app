import json
import boto3
import requests
from functions import read_secret
from requests.auth import HTTPBasicAuth

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('yelp-restaurants')

res = table.scan()

for idx, item in enumerate(res['Items']):
  print('Inserting item', idx + 1)
  
  url = 'https://search-yelp-restaurants-stdbh4kdqgmea75qrmmfw3wv2q.aos.us-east-1.on.aws/restaurants/_doc'
  headers = {"Content-Type": "application/json"}
  body = {"restaurantID": item['id'], "cuisine": item['cuisine']}
  
  response = requests.post(
    url, 
    data=json.dumps(body).encode("utf-8"), 
    headers=headers, 
    auth=HTTPBasicAuth(read_secret('elasticsearch_user'), read_secret('elasticsearch_password'))
  )
  print('Inserted item', idx + 1)
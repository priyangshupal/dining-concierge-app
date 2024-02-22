import boto3
import json
from decimal import Decimal
import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('yelp-restaurants')

with open('restaurants_compressed.json', 'r') as file:
  d = json.load (file)
  
  for idx, item in enumerate(d['restaurants']):
    print ('Inserting item', idx + 1)

    dynamoItem = {
      'id': item['id'],
      'name': item['name'],
      'coordinates': {
        'latitude': Decimal(str(item["coordinates"]["latitude"])),
        'longitude': Decimal(str(item["coordinates"]["longitude"]))
      },
      'rating': Decimal(str(item['rating'])),
      'review_count': Decimal(str(item['review_count'])),
      'distance': Decimal(str(item['distance'])),
      'insertedAtTimestamp': str(datetime.datetime.now()),
      'address': item['location']['address1'],
      'zipcode': item['location']['zip_code'],
      'cuisine': item['cuisine']
    }
    
    table.put_item(Item=dynamoItem)
    print ('Inserted item', idx + 1)
import requests
import json
from functions import read_secret

def get_restaurants():
    headers = {'Authorization': read_secret('auth_token') }
    url = 'https://api.yelp.com/v3/businesses/search'
    data = []
    cuisines = ['italian', 'chinese', 'indian', 'american', 'mexican']
    for cuisine in cuisines:
      for offset in range(0, 1000, 50):
        params = {
          'limit': 50,
          'location': 'Manhattan',
          'term': cuisine,
          'offset': offset
        }
        response = requests.get(url, headers=headers, params=params)
        res = response.json()
        res['cuisine'] = cuisine
        if response.status_code == 200:
            for business in res['businesses']:
                business['cuisine'] = cuisine
                data.append(business)
        else:
            print('Error')
            break
    
    return { 'restaurants' : data }

with open("restaurants.json", "w") as file:
    json.dump(get_restaurants(), file)

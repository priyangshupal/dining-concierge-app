import boto3
import json

client = boto3.client('lex-runtime')


def lambda_handler(event, context):
    last_user_message = "Hello"
    body = json.loads(event.get("body", "{}"))
    messages = body.get("messages", [])
    
    
    last_user_message = messages[0]['unstructured']['text']
    
    botMessage = "Please try again.";
    
    
    user = "temp1"
    
    if last_user_message is None or len(last_user_message) < 1:
        
        return {
            'statusCode': 200,
              headers: {
            "Access-Control-Allow-Headers" : "*",
            "Access-Control-Allow-Origin": "*", 
            "Access-Control-Allow-Methods": "*" 
            },
            'body': json.dumps(botMessage)
        }
    
    
    response = client.post_text(botName='RestaurantSuggestion',
                                botAlias='testBot',
                                userId=user,
                                inputText=last_user_message)

    if response['message'] is not None or len(response['message']) > 0:
        last_user_message = response['message']
    else:
        last_user_message = "System is Down!"

    # Return the response with a 200 status code
    return {
        "statusCode": 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',  # Allow all origins
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',  # Adjust methods according to your needs
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',  # Adjust headers according to your needs
        # },
        # "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(last_user_message)
    }
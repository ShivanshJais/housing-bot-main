import json
import os

import boto3

from main import HousingBot


def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    bot = HousingBot(responses=[], categories=[
        ("city", "NNP"), ("budget", "CD")])  # NNP: Proper noun, singular; CD: Cardinal number
    body = bot.respond(message['Body'])
    sns = boto3.client('sns')
    return sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Message=json.dumps({
            'Body': body,
            'RecipientId': message['RecipientId']
        })
    )

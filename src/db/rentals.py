import logging
import sys
import boto3
from boto3 import dynamodb
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Rentals:
    """Encapsulates an Amazon DynamoDB table of rentals data."""

    dyn_resource = boto3.resource("dynamodb")
    table = dyn_resource.Table("ScraperHistory")

    @classmethod
    def query(cls, city, budget=None):
        """
        Queries for rentals in the specified city.

        :param city: The city to query for.
        :param budget: The maximum budget to query for.
        :return: A list of rental items.
        """
        try:
            response = cls.table.query(
                KeyConditionExpression=Key("City").eq(city), FilterExpression=Key("Price").lt(budget))
        except ClientError as e:
            logger.error(
                f"Couldn't query for cities in {city}. Here's why: {e.response['Error']['Code']}: {e.response['Error']['Message']}"
            )
            raise
        else:
            return response["Items"]


if __name__ == "__main__":
    logger.info(Rentals.query("Kitchener", 1000))

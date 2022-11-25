import logging
import sys

from cli.chatbot import ChatBot, EntityNotFoundError
from db.rentals import Rentals


class HousingBot(ChatBot):
    def respond(self, user_msg: str) -> str:
        """Return a response to the user message."""
        if self.make_exit(user_msg):
            return "Bye!"
        else:
            try:
                best_response = self.find_intent_match(user_msg)
                entities = self.find_entities(user_msg)
                city = next(best_match for category,
                            best_match in entities if category == "city")
                budget = int(next(best_match for category,
                                  best_match in entities if category == "budget"))

                items = Rentals.query(city=city, budget=budget)
                response = f"I found {len(items)} items in {city} for less than {budget}."
                for item in items:
                    response += f"\n{item['Title']} is {item['Price']} at {item['URL']}."
                return response
            except EntityNotFoundError:
                logging.error(f"Entity not found in {user_msg}.")
                return "Sorry, I didn't understand."


if __name__ == "__main__":
    # Doctest
    import doctest
    doctest.testmod()
    ###

    # Logging
    import logging
    logging.basicConfig(filename="chatbot.log", level=logging.DEBUG)
    ###

    responses = []

    # optional command line argument to load responses from a file
    if len(sys.argv) > 1:
        responses_file = sys.argv[1]
        with open(responses_file, "r") as f:
            responses = f.read().splitlines()

    bot = HousingBot(responses=responses, categories=[
        ("city", "NNP"), ("budget", "CD")])  # NNP: Proper noun, singular; CD: Cardinal number
    while True:
        user_msg = input("Enter your message: ")
        print(bot.respond(user_msg))
        if bot.make_exit(user_msg):
            break

"""
A command line interface to run the chatbot locally.
"""
import logging
import re
import spacy
from spacy.tokens import Doc as SpacyDoc
from collections import Counter
from nltk import pos_tag as nltk_pos_tag
from nltk.tokenize import word_tokenize as nltk_word_tokenize
from nltk.corpus import stopwords as nltk_stopwords
from typing import List, Tuple


class EntityNotFoundError(Exception):
    """Raised when an entity is not found in the user input."""
    pass


class ChatBot:
    # Signals to the chatbot that the user wants to exit the conversation.
    exit_commands = ("quit", "pause", "exit", "goodbye", "bye", "later")
    stopwords = set(nltk_stopwords.words("english"))
    word2vec = spacy.load("en_core_web_sm")

    def __init__(self, responses=None, categories: List[Tuple[str, str]] = None):
        """Initialize the chatbot with a list of responses.
        >>> c1 = ChatBot()
        >>> c1.responses
        []
        >>> c2 = ChatBot(["Hello!"])
        >>> c2.responses
        ['Hello!']
        """
        self.responses = responses or []
        # Categories of entities that the chatbot will extract from the user message.
        # TODO: Limit POS tags to Penn tagset.
        self.categories = categories or []

    def __preprocess(self, msg: str) -> List[str]:
        """Preprocess the message to remove punctuation and tokenize."""
        msg = msg.lower()
        msg = re.sub(r'[^\w\s]', '', msg)  # remove punctuation
        tokens = nltk_word_tokenize(msg)
        # remove stopwords
        tokens = [token for token in tokens if token not in self.stopwords]
        logging.debug("tokens: [%s]", tokens)
        return tokens

    def __compare_bow(self, bow_user_msg: Counter, bow_response: Counter) -> float:
        """Return the similarity of the user message and the response."""
        return sum([bow_user_msg[token] for token in bow_user_msg if token in bow_response]) / len(bow_user_msg)

    # TODO: Return a list of named tuples instead.
    def __compute_similarity(self, tokens: List[SpacyDoc], category: SpacyDoc) -> List[Tuple[str, float]]:
        """Return a list of similarities between the tokens and the category."""
        return [(token.text, token.similarity(category)) for token in tokens]

    def make_exit(self, user_msg: str) -> bool:
        """Return true if the user wants to exit the chatbot.

        >>> c = ChatBot()
        >>> c.make_exit("I want to quit")
        True
        >>> c.make_exit("Bye!")
        True
        """
        processed_msg = user_msg.lower()
        for exit_command in self.exit_commands:
            if exit_command in processed_msg:
                return True
        return False

    def find_intent_match(self, user_msg: str) -> str:
        """Return the intent that matches the user message."""
        if self.responses == []:
            return ""
        bow_user_msg = Counter(self.__preprocess(user_msg))
        processed_responses = [self.__preprocess(
            response) for response in self.responses]
        similarity_list = [self.__compare_bow(
            bow_user_msg, bow_response) for bow_response in processed_responses]
        return self.responses[similarity_list.index(max(similarity_list))]

    def find_entities(self, user_msg: str) -> List[Tuple[str, str]]:
        """Return a list of entities in the user message."""

        tagged_user_msg = nltk_pos_tag(user_msg.split())
        logging.debug("tagged_user_msg: [%s]", tagged_user_msg)

        entities = []

        for category, pos_tag in self.categories:
            logging.debug("category: [%s]", category)
            logging.debug("pos_tag: [%s]", pos_tag)

            matching_tokens = [token for token,
                               tag in tagged_user_msg if tag == pos_tag]

            logging.debug("matching_tokens: [%s]", matching_tokens)

            if not matching_tokens:
                raise EntityNotFoundError

            token_docs = self.word2vec(" ".join(matching_tokens))
            category_doc = self.word2vec(category)

            word2vec_result = self.__compute_similarity(
                token_docs, category_doc)
            word2vec_result.sort(key=lambda x: x[1], reverse=True)
            logging.debug("word2vec_result: %s", word2vec_result)

            best_match = word2vec_result[0]
            entities.append((category, best_match[0]))

        return entities

    def respond(self, user_msg: str) -> str:
        """Return a response to the user message."""
        if self.make_exit(user_msg):
            return "Bye!"
        else:
            try:
                best_response = self.find_intent_match(user_msg)
                entities = self.find_entities(user_msg)
                # TODO: Find a better way to do this.
                return best_response.format(*[entity[1] for entity in entities])
            except EntityNotFoundError:
                logging.error(f"Entity not found in {user_msg}.")
                return "Sorry, I didn't understand."

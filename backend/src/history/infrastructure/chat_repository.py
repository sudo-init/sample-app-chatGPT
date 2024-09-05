# history/infrastructure/chat_repository.py

from history.domain.chat_domain import Message

class InMemoryChatRepository:
    def __init__(self):
        self.history = []

    def save(self, message: Message):
        self.history.append(message)

    def find_all(self):
        return self.history

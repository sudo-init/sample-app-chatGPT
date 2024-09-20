import uuid
from datetime import datetime

class Conversation:
    def __init__(self, user_id: str, title: str = ''):
        self.id = str(uuid.uuid4())
        self.type = 'conversation'
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        self.user_id = user_id
        self.title = title

    def to_dict(self):
        """
        Converts the Conversation object to a dictionary.
        This is useful for saving to Cosmos DB or other storage.
        """
        return {
            'id': self.id,
            'type': self.type,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'userId': self.user_id,
            'title': self.title
        }

    def update_timestamp(self):
        """
        Updates the 'updatedAt' field to the current UTC time.
        """
        self.updated_at = datetime.utcnow().isoformat()


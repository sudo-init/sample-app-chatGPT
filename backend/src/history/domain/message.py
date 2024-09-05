

class Message:
    def __init__(self, id: str, role: str, content: str, user_id: str, conversation_id: str, feedback: str = ''):
        self.id = id
        self.role = role
        self.content = content
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        self.feedback = feedback
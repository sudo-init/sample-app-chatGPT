

class Conversation:
    def __init__(self, id: str, user_id: str, title: str = '', created_at: str = None, updated_at: str = None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.created_at = created_at if created_at else datetime.utcnow().isoformat()
        self.updated_at = updated_at if updated_at else datetime.utcnow().isoformat()
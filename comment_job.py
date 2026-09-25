class CommentJob:
    def __init__(self, post_url, comment, campaign_id=None):
        self.post_url = post_url
        self.comment = comment
        self.campaign_id = campaign_id
        self.success = False

from langgraph.checkpoint.redis import RedisSaver
from redis import Redis
from .config import settings

def get_checkpointer():
    """
    Returns a RedisSaver instance connected to the configured Redis URL.
    """
    # Create Redis connection
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    # create checkpointer
    checkpointer = RedisSaver(redis_client)
    return checkpointer

import redis
import json
from pawnlib.config import ConsoleLoggerAdapter

class RedisHelper:
    def __init__(self, host='localhost', port=6379, db=0, logger=None, verbose=False):
        """
        Initialize RedisHelper with Redis connection details.
        :param host: Redis server host (default: localhost)
        :param port: Redis server port (default: 6379)
        :param db: Redis database number (default: 0)
        :param logger: Custom logger instance (optional). If None, a default logger will be created.
        :param verbose: If True, enables verbose logging.
        """
        self.logger = ConsoleLoggerAdapter(logger, "RedisHelper", verbose > 0)

        try:
            self.client = redis.StrictRedis(host=host, port=port, db=db)
            if not self.client.ping():
                raise ConnectionError("Unable to connect to Redis server.")
            self.logger.info("Successfully connected to Redis.")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def get(self, key, as_json=False):
        """
        Get a value from Redis for a given key.
        :param key: The Redis key to retrieve.
        :param as_json: If True, attempts to parse the value as JSON.
        :return: The value stored in Redis, optionally as a dictionary if stored in JSON format.
        """
        try:
            value = self.client.get(key)
            if value is not None:
                decoded_value = value.decode()
                if as_json:
                    try:
                        return json.loads(decoded_value)
                    except json.JSONDecodeError:
                        self.logger.error(f"Invalid JSON format for key {key}. Returning raw value.")
                        return decoded_value
                return decoded_value
            return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve key {key} from Redis: {e}")
            return None

    def set(self, key, value, as_json=False, ttl=None):
        """
        Set a value in Redis for a given key.
        :param key: The Redis key to set.
        :param value: The value to store.
        :param as_json: If True, stores the value as JSON.
        :param ttl: Optional time-to-live (TTL) in seconds.
        """
        try:
            if as_json:
                value = json.dumps(value)
            self.client.set(key, value)
            if ttl:
                self.client.expire(key, ttl)
            self.logger.info(f"Successfully set key {key} in Redis.")
            self.logger.info(f"set {key}")
        except Exception as e:
            self.logger.error(f"Failed to set key {key} in Redis: {e}")

    def set_with_ttl(self, key, value, ttl):
        """
        Set a key in Redis with a time-to-live (TTL).
        :param key: The Redis key to set.
        :param value: The value to store.
        :param ttl: The time-to-live (TTL) in seconds.
        """
        self.set(key, value)
        self.client.expire(key, ttl)

    def exists(self, key):
        """
        Check if a key exists in Redis.
        :param key: The Redis key to check.
        :return: True if the key exists, False otherwise.
        """
        try:
            exists = self.client.exists(key)
            self.logger.info(f"Key {key} exists: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Failed to check existence of key {key}: {e}")
            return False

    def delete(self, key):
        """
        Delete a key from Redis.
        :param key: The Redis key to delete.
        """
        try:
            self.client.delete(key)
            self.logger.info(f"Successfully deleted key {key} from Redis.")
        except Exception as e:
            self.logger.error(f"Failed to delete key {key} from Redis: {e}")

    def lpush(self, key, *values):
        """
        Push one or more values onto the left side of a Redis list.
        :param key: The Redis key (list) to push values onto.
        :param values: One or more values to push.
        """
        try:
            self.client.lpush(key, *values)
            self.logger.info(f"Successfully pushed values to list {key}.")
        except Exception as e:
            self.logger.error(f"Failed to push values to list {key}: {e}")

    def lrange(self, key, start=0, end=-1):
        """
        Retrieve a range of values from a Redis list.
        :param key: The Redis key (list) to retrieve values from.
        :param start: Start index (default: 0).
        :param end: End index (default: -1 for all values).
        :return: A list of values from the Redis list.
        """
        try:
            values = self.client.lrange(key, start, end)
            self.logger.info(f"Successfully retrieved values from list {key}.")
            return values
        except Exception as e:
            self.logger.error(f"Failed to retrieve values from list {key}: {e}")
            return []

    def transactional_update(self, updates):
        """
        Perform a transactional update using Redis pipeline.
        :param updates: A list of (key, value) pairs to update.
        """
        try:
            pipe = self.client.pipeline()
            for key, value in updates:
                pipe.set(key, value)
            pipe.execute()
            self.logger.info("Successfully executed transactional update.")
        except Exception as e:
            self.logger.error(f"Failed to execute transactional update: {e}")

    def hset(self, key, field, value):
        """
        Set a field value in a Redis hash.
        :param key: The Redis key (hash).
        :param field: The field name within the hash.
        :param value: The value to set for the field.
        """
        try:
            self.client.hset(key, field, value)
            self.logger.info(f"Successfully set field {field} in hash {key}.")
        except Exception as e:
            self.logger.error(f"Failed to set field {field} in hash {key}: {e}")

    def hget(self, key, field):
        """
        Retrieve a field value from a Redis hash.
        :param key: The Redis key (hash).
        :param field: The field name within the hash.
        :return: The value stored in the hash field, or None if the field does not exist.
        """
        try:
            value = self.client.hget(key, field)
            if value is None:
                self.logger.warning(f"Field {field} not found in hash {key}.")
                return None
            return value.decode()
        except Exception as e:
            self.logger.error(f"Failed to retrieve field {field} from hash {key}: {e}")
            return None

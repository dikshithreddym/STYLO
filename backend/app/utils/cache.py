"""
Caching utilities for STYLO backend.
Provides Redis-based caching and in-memory LRU caching for improved performance.
"""
import os
import json
import hashlib
import logging
from functools import lru_cache
from typing import Optional, Dict, Any, List
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Try to import Redis, but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Caching will use in-memory only.")


# In-memory caches (fallback when Redis is unavailable)
_in_memory_caches: Dict[str, TTLCache] = {}

# Redis client (initialized lazily)
_redis_client: Optional[Any] = None


def get_redis_client():
    """Get or create Redis client with connection pooling."""
    global _redis_client
    if not REDIS_AVAILABLE:
        logger.debug("Redis library not available")
        return None
    
    if _redis_client is None:
        try:
            # Check for REDIS_URL first (Render/cloud provider format)
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                logger.info(f"Attempting Redis connection via REDIS_URL: {redis_url[:50]}...")
                # Parse Redis URL format: redis://host:port or redis://:password@host:port
                _redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                ping_result = _redis_client.ping()
                logger.info(f"✅ Redis connected via REDIS_URL (ping: {ping_result})")
            else:
                # Fallback to individual environment variables
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', '6379'))
                redis_db = int(os.getenv('REDIS_DB', '0'))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                
                logger.info(f"Attempting Redis connection: {redis_host}:{redis_port}/{redis_db}")
                _redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                ping_result = _redis_client.ping()
                logger.info(f"✅ Redis connected: {redis_host}:{redis_port}/{redis_db} (ping: {ping_result})")
        except Exception as e:
            logger.warning(f"❌ Redis connection failed: {e}. Using in-memory cache only.", exc_info=True)
            _redis_client = None
    
    return _redis_client


def get_in_memory_cache(cache_name: str, maxsize: int = 100, ttl: int = 300) -> TTLCache:
    """Get or create an in-memory TTL cache."""
    if cache_name not in _in_memory_caches:
        _in_memory_caches[cache_name] = TTLCache(maxsize=maxsize, ttl=ttl)
    return _in_memory_caches[cache_name]


def _generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from prefix and arguments."""
    # Create a hash of all arguments
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


def cache_get(key: str, cache_name: str = "default") -> Optional[Any]:
    """Get value from cache (Redis or in-memory)."""
    # Try Redis first
    redis_client = get_redis_client()
    if redis_client:
        try:
            cached = redis_client.get(key)
            if cached:
                logger.debug(f"✅ Redis cache HIT for key: {key[:50]}...")
                return json.loads(cached)
            else:
                logger.debug(f"❌ Redis cache MISS for key: {key[:50]}...")
        except Exception as e:
            logger.warning(f"Redis get failed for key {key[:50]}...: {e}")
    else:
        logger.debug(f"Redis not available, trying in-memory cache for key: {key[:50]}...")
    
    # Fallback to in-memory cache
    try:
        in_mem_cache = get_in_memory_cache(cache_name)
        result = in_mem_cache.get(key)
        if result:
            logger.debug(f"✅ In-memory cache HIT for key: {key[:50]}...")
        else:
            logger.debug(f"❌ In-memory cache MISS for key: {key[:50]}...")
        return result
    except Exception as e:
        logger.warning(f"In-memory cache get failed for key {key[:50]}...: {e}")
    
    return None


def cache_set(key: str, value: Any, ttl: int = 300, cache_name: str = "default") -> bool:
    """Set value in cache (Redis or in-memory)."""
    # Try Redis first
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.setex(key, ttl, json.dumps(value))
            logger.debug(f"✅ Redis cache SET for key: {key[:50]}... (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Redis set failed for key {key[:50]}...: {e}")
    else:
        logger.debug(f"Redis not available, using in-memory cache for key: {key[:50]}...")
    
    # Fallback to in-memory cache
    try:
        in_mem_cache = get_in_memory_cache(cache_name, ttl=ttl)
        in_mem_cache[key] = value
        logger.debug(f"✅ In-memory cache SET for key: {key[:50]}... (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"In-memory cache set failed for key {key[:50]}...: {e}")
    
    return False


def cache_delete(key: str) -> bool:
    """Delete value from cache."""
    # Try Redis first
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {e}")
    
    # Delete from all in-memory caches
    for cache in _in_memory_caches.values():
        try:
            if key in cache:
                del cache[key]
        except Exception:
            pass
    
    return True


def cache_clear_pattern(pattern: str) -> int:
    """Clear all cache keys matching a pattern."""
    deleted = 0
    
    # Try Redis first
    redis_client = get_redis_client()
    if redis_client:
        try:
            keys = redis_client.keys(pattern)
            if keys:
                deleted = redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis pattern delete failed for {pattern}: {e}")
    
    # Clear from in-memory caches
    for cache in _in_memory_caches.values():
        keys_to_delete = [k for k in cache.keys() if pattern.replace('*', '') in str(k)]
        for key in keys_to_delete:
            try:
                del cache[key]
                deleted += 1
            except Exception:
                pass
    
    return deleted


# Specific cache functions for different use cases

def get_cached_suggestion(query: str, wardrobe_hash: str) -> Optional[Dict]:
    """Get cached outfit suggestion."""
    key = _generate_cache_key("suggestion", query, wardrobe_hash)
    return cache_get(key, cache_name="suggestions")


def set_cached_suggestion(query: str, wardrobe_hash: str, result: Dict, ttl: int = 300) -> bool:
    """Cache outfit suggestion."""
    key = _generate_cache_key("suggestion", query, wardrobe_hash)
    return cache_set(key, result, ttl=ttl, cache_name="suggestions")


def get_cached_intent(query: str) -> Optional[Any]:
    """Get cached intent classification result."""
    key = _generate_cache_key("intent", query)
    return cache_get(key, cache_name="intents")


def set_cached_intent(query: str, result: Any, ttl: int = 3600) -> bool:
    """Cache intent classification result."""
    key = _generate_cache_key("intent", query)
    return cache_set(key, result, ttl=ttl, cache_name="intents")


def get_cached_wardrobe_list(cache_key: str) -> Optional[List[Dict]]:
    """Get cached wardrobe list."""
    key = f"wardrobe_list:{cache_key}"
    return cache_get(key, cache_name="wardrobe")


def set_cached_wardrobe_list(cache_key: str, items: List[Dict], ttl: int = 60) -> bool:
    """Cache wardrobe list."""
    key = f"wardrobe_list:{cache_key}"
    return cache_set(key, items, ttl=ttl, cache_name="wardrobe")


def get_cached_embedding(item_id: int) -> Optional[List[float]]:
    """Get cached embedding for an item."""
    key = f"embedding:{item_id}"
    return cache_get(key, cache_name="embeddings")


def set_cached_embedding(item_id: int, embedding: List[float], ttl: int = 86400) -> bool:
    """Cache embedding for an item (24 hour TTL)."""
    key = f"embedding:{item_id}"
    return cache_set(key, embedding, ttl=ttl, cache_name="embeddings")


# In-memory cache for model instance (using functools.lru_cache)
@lru_cache(maxsize=1)
def get_embedder_instance():
    """Get cached embedder instance (singleton pattern)."""
    from ..reco.embedding import Embedder
    return Embedder.instance()


def clear_all_caches():
    """Clear all caches (useful for testing or cache invalidation)."""
    # Clear Redis
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.flushdb()
        except Exception as e:
            logger.warning(f"Redis flush failed: {e}")
    
    # Clear in-memory caches
    for cache in _in_memory_caches.values():
        cache.clear()
    
    logger.info("All caches cleared")


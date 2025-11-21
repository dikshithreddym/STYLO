"""
Service for computing and persisting embeddings for wardrobe items.
Handles async background updates to avoid blocking API requests.
"""
import asyncio
import logging
from typing import List, Optional
import numpy as np
from sqlalchemy.orm import Session

from ..database import WardrobeItem
from ..reco.embedding import Embedder


def _create_searchable_text(item: WardrobeItem) -> str:
    """Create searchable text representation of a wardrobe item"""
    parts = []
    if item.type:
        parts.append(item.type)
    if item.color:
        parts.append(item.color)
    if item.image_description:
        parts.append(item.image_description)
    if item.category:
        parts.append(item.category)
    return " ".join(parts).strip()

logger = logging.getLogger(__name__)

# Background task queue for embedding updates
_embedding_queue: asyncio.Queue = asyncio.Queue()
_embedding_worker_running = False


def _embedding_to_list(embedding: np.ndarray) -> List[float]:
    """Convert numpy array to list of floats for JSON storage"""
    return embedding.tolist()


def _list_to_embedding(embedding_list: List[float]) -> np.ndarray:
    """Convert list of floats back to numpy array"""
    return np.array(embedding_list, dtype=np.float32)


def compute_embedding_for_item(item: WardrobeItem) -> Optional[List[float]]:
    """
    Compute embedding for a single wardrobe item.
    
    Args:
        item: WardrobeItem instance
        
    Returns:
        List of floats representing the embedding, or None if computation fails
    """
    try:
        emb = Embedder.instance()
        searchable_text = _create_searchable_text(item)
        
        if not searchable_text:
            logger.warning(f"Item {item.id} has no searchable text, skipping embedding")
            return None
        
        # Compute embedding
        embedding_vector = emb.encode([searchable_text])[0]
        
        # Convert to list for JSON storage
        return _embedding_to_list(embedding_vector)
    except Exception as e:
        logger.error(f"Failed to compute embedding for item {item.id}: {e}")
        return None


def persist_embedding(db: Session, item_id: int, embedding: List[float]) -> bool:
    """
    Persist embedding to database.
    
    Args:
        db: Database session
        item_id: ID of the wardrobe item
        embedding: List of floats representing the embedding
        
    Returns:
        True if successful, False otherwise
    """
    try:
        item = db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
        if not item:
            logger.warning(f"Item {item_id} not found for embedding update")
            return False
        
        item.embedding = embedding
        db.commit()
        logger.debug(f"Persisted embedding for item {item_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to persist embedding for item {item_id}: {e}")
        db.rollback()
        return False


def get_stored_embedding(item: WardrobeItem) -> Optional[np.ndarray]:
    """
    Retrieve stored embedding from database item.
    
    Args:
        item: WardrobeItem instance with embedding field
        
    Returns:
        Numpy array of the embedding, or None if not available
    """
    if not item.embedding:
        return None
    
    try:
        return _list_to_embedding(item.embedding)
    except Exception as e:
        logger.warning(f"Failed to deserialize embedding for item {item.id}: {e}")
        return None


async def refresh_embedding_async(item_id: int, db_session_factory=None):
    """
    Asynchronously refresh embedding for a wardrobe item.
    This function can be called from API endpoints without blocking.
    
    Args:
        item_id: ID of the wardrobe item to refresh
        db_session_factory: Function that returns a database session (for background tasks)
    """
    try:
        # Create a new session for background task
        if db_session_factory:
            db = db_session_factory()
        else:
            from ..database import SessionLocal
            db = SessionLocal()
        
        try:
            item = db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
            if not item:
                logger.warning(f"Item {item_id} not found for async embedding refresh")
                return
            
            # Compute embedding
            embedding = compute_embedding_for_item(item)
            if embedding:
                persist_embedding(db, item_id, embedding)
                logger.info(f"Async embedding refresh completed for item {item_id}")
            else:
                logger.warning(f"Failed to compute embedding for item {item_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in async embedding refresh for item {item_id}: {e}")


def queue_embedding_refresh(item_id: int):
    """
    Queue an embedding refresh task to be processed asynchronously.
    This is a non-blocking way to trigger embedding updates.
    
    Args:
        item_id: ID of the wardrobe item to refresh
    """
    try:
        _embedding_queue.put_nowait(item_id)
        logger.debug(f"Queued embedding refresh for item {item_id}")
    except asyncio.QueueFull:
        logger.warning(f"Embedding queue full, dropping refresh request for item {item_id}")


async def _embedding_worker():
    """
    Background worker that processes embedding refresh tasks from the queue.
    This runs continuously and processes items as they are queued.
    """
    global _embedding_worker_running
    from ..database import SessionLocal
    
    logger.info("Embedding worker started")
    _embedding_worker_running = True
    
    while True:
        try:
            # Wait for item ID from queue (with timeout to allow graceful shutdown)
            try:
                item_id = await asyncio.wait_for(_embedding_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            
            # Process the embedding refresh
            await refresh_embedding_async(item_id, SessionLocal)
            _embedding_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error in embedding worker: {e}")
            await asyncio.sleep(1)  # Brief pause before retrying


def start_embedding_worker():
    """Start the background embedding worker if not already running.
    This should be called from an async context (e.g., FastAPI startup event).
    """
    global _embedding_worker_running
    
    if not _embedding_worker_running:
        try:
            # Create task in the current event loop
            asyncio.create_task(_embedding_worker())
            logger.info("Embedding worker task created")
        except Exception as e:
            logger.warning(f"Could not start embedding worker: {e}. Embeddings will be computed on-demand.")


def batch_refresh_embeddings(db: Session, item_ids: Optional[List[int]] = None) -> int:
    """
    Batch refresh embeddings for multiple items (synchronous, for admin/migration use).
    
    Args:
        db: Database session
        item_ids: List of item IDs to refresh (None = refresh all items without embeddings)
        
    Returns:
        Number of embeddings successfully refreshed
    """
    if item_ids:
        items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(item_ids)).all()
    else:
        # Refresh items that don't have embeddings yet
        items = db.query(WardrobeItem).filter(WardrobeItem.embedding.is_(None)).all()
    
    refreshed = 0
    for item in items:
        embedding = compute_embedding_for_item(item)
        if embedding:
            if persist_embedding(db, item.id, embedding):
                refreshed += 1
    
    logger.info(f"Batch refresh completed: {refreshed}/{len(items)} embeddings refreshed")
    return refreshed


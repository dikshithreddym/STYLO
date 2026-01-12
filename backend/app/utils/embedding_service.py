"""
Service for computing and persisting embeddings for wardrobe items.
Handles async background updates to avoid blocking API requests.
"""
import asyncio
import logging
import os
from typing import List, Optional
import numpy as np
from sqlalchemy.orm import Session

from ..database import WardrobeItem
from ..reco.embedding import Embedder
from ..config import settings


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

# Batch processing configuration (use settings if available, fallback to env vars)
def get_batch_size() -> int:
    """Get batch size from settings or environment"""
    try:
        return settings.EMBEDDING_BATCH_SIZE
    except (AttributeError, TypeError):
        return int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

def get_batch_timeout() -> float:
    """Get batch timeout from settings or environment"""
    try:
        return settings.EMBEDDING_BATCH_TIMEOUT
    except (AttributeError, TypeError):
        return float(os.getenv("EMBEDDING_BATCH_TIMEOUT", "2.0"))


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


def compute_embeddings_batch(items: List[WardrobeItem]) -> List[tuple[int, List[float]]]:
    """
    Compute embeddings for multiple items in a single batch operation.
    This is much more efficient than computing one-by-one.
    
    Args:
        items: List of WardrobeItem instances
        
    Returns:
        List of tuples (item_id, embedding_list) for successfully computed embeddings
    """
    if not items:
        return []
    
    try:
        emb = Embedder.instance()
        
        # Prepare texts for batch encoding
        item_texts = []
        valid_items = []
        
        for item in items:
            searchable_text = _create_searchable_text(item)
            if searchable_text:
                item_texts.append(searchable_text)
                valid_items.append(item)
            else:
                logger.warning(f"Item {item.id} has no searchable text, skipping")
        
        if not item_texts:
            return []
        
        # Batch encode all items at once (much faster)
        embedding_vectors = emb.encode(item_texts)
        
        # Convert to list format and pair with item IDs
        results = []
        for item, embedding_vec in zip(valid_items, embedding_vectors):
            embedding_list = _embedding_to_list(embedding_vec)
            results.append((item.id, embedding_list))
        
        logger.debug(f"Batch computed {len(results)} embeddings")
        return results
        
    except Exception as e:
        logger.error(f"Failed to compute batch embeddings: {e}")
        return []


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


def persist_embeddings_batch(db: Session, embeddings: List[tuple[int, List[float]]]) -> int:
    """
    Persist multiple embeddings to database in a single transaction.
    This is much more efficient than committing one-by-one.
    
    Args:
        db: Database session
        embeddings: List of tuples (item_id, embedding_list)
        
    Returns:
        Number of successfully persisted embeddings
    """
    if not embeddings:
        return 0
    
    try:
        # Get all item IDs
        item_ids = [item_id for item_id, _ in embeddings]
        
        # Fetch all items in one query
        items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(item_ids)).all()
        item_map = {item.id: item for item in items}
        
        # Update items with embeddings
        updated = 0
        for item_id, embedding in embeddings:
            if item_id in item_map:
                item_map[item_id].embedding = embedding
                updated += 1
            else:
                logger.warning(f"Item {item_id} not found for batch embedding update")
        
        # Single commit for all updates
        db.commit()
        logger.debug(f"Batch persisted {updated} embeddings")
        return updated
        
    except Exception as e:
        logger.error(f"Failed to persist batch embeddings: {e}")
        db.rollback()
        return 0


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
    Uses batch processing for improved efficiency.
    """
    global _embedding_worker_running
    from ..database import SessionLocal
    
    batch_size = get_batch_size()
    batch_timeout = get_batch_timeout()
    logger.info(f"Embedding worker started (batch size: {batch_size}, timeout: {batch_timeout}s)")
    _embedding_worker_running = True
    
    while True:
        try:
            # Collect batch of item IDs
            batch = []
            batch_start_time = asyncio.get_event_loop().time()
            
            # Get first item (blocking)
            try:
                item_id = await asyncio.wait_for(_embedding_queue.get(), timeout=batch_timeout)
                batch.append(item_id)
            except asyncio.TimeoutError:
                # No items in queue, continue to next iteration
                continue
            
            # Try to collect more items up to batch_size or timeout
            while len(batch) < batch_size:
                elapsed = asyncio.get_event_loop().time() - batch_start_time
                remaining_timeout = max(0.1, batch_timeout - elapsed)
                
                try:
                    item_id = await asyncio.wait_for(_embedding_queue.get(), timeout=remaining_timeout)
                    batch.append(item_id)
                except asyncio.TimeoutError:
                    # Timeout reached, process current batch
                    break
            
            # Process batch
            if batch:
                await _process_embedding_batch(batch, SessionLocal)
                # Mark all tasks as done
                for _ in batch:
                    _embedding_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error in embedding worker: {e}")
            await asyncio.sleep(1)  # Brief pause before retrying


async def _process_embedding_batch(item_ids: List[int], db_session_factory):
    """
    Process a batch of embedding updates efficiently.
    
    Args:
        item_ids: List of item IDs to process
        db_session_factory: Function that returns a database session
    """
    db = db_session_factory()
    try:
        # Fetch all items in one query
        items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(item_ids)).all()
        
        if not items:
            logger.warning(f"No items found for batch: {item_ids}")
            return
        
        # Compute embeddings in batch (much faster)
        embedding_results = compute_embeddings_batch(items)
        
        if embedding_results:
            # Persist all embeddings in single transaction
            persisted = persist_embeddings_batch(db, embedding_results)
            logger.info(f"Batch processed {persisted}/{len(item_ids)} embeddings")
        else:
            logger.warning(f"Failed to compute embeddings for batch: {item_ids}")
            
    except Exception as e:
        logger.error(f"Error processing embedding batch: {e}")
    finally:
        db.close()


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


def batch_refresh_embeddings(db: Session, item_ids: Optional[List[int]] = None, batch_size: int = None) -> int:
    """
    Batch refresh embeddings for multiple items (synchronous, for admin/migration use).
    Uses optimized batch processing for better performance.
    
    Args:
        db: Database session
        item_ids: List of item IDs to refresh (None = refresh all items without embeddings)
        batch_size: Number of items to process per batch (None = use default BATCH_SIZE)
        
    Returns:
        Number of embeddings successfully refreshed
    """
    if item_ids:
        items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(item_ids)).all()
    else:
        # Refresh items that don't have embeddings yet
        items = db.query(WardrobeItem).filter(WardrobeItem.embedding.is_(None)).all()
    
    if not items:
        logger.info("No items to refresh")
        return 0
    
    # Use provided batch size or default from config
    process_batch_size = batch_size or get_batch_size()
    
    total_refreshed = 0
    total_items = len(items)
    
    # Process in batches for better memory efficiency
    for i in range(0, total_items, process_batch_size):
        batch = items[i:i + process_batch_size]
        
        # Compute embeddings for batch
        embedding_results = compute_embeddings_batch(batch)
        
        if embedding_results:
            # Persist batch
            persisted = persist_embeddings_batch(db, embedding_results)
            total_refreshed += persisted
            
            logger.info(f"Processed batch {i//process_batch_size + 1}: {persisted}/{len(batch)} embeddings refreshed")
    
    logger.info(f"Batch refresh completed: {total_refreshed}/{total_items} embeddings refreshed")
    return total_refreshed


async def batch_refresh_embeddings_async(db, item_ids: Optional[List[int]] = None, batch_size: int = None) -> int:
    """
    Async batch refresh embeddings for multiple items.
    Works with AsyncSession.
    
    Args:
        db: AsyncSession database session
        item_ids: List of item IDs to refresh (None = refresh all items without embeddings)
        batch_size: Number of items to process per batch (None = use default BATCH_SIZE)
        
    Returns:
        Number of embeddings successfully refreshed
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    
    if item_ids:
        result = await db.execute(
            select(WardrobeItem).where(WardrobeItem.id.in_(item_ids))
        )
        items = result.scalars().all()
    else:
        # Refresh items that don't have embeddings yet
        result = await db.execute(
            select(WardrobeItem).where(WardrobeItem.embedding.is_(None))
        )
        items = result.scalars().all()
    
    if not items:
        logger.info("No items to refresh")
        return 0
    
    # Use provided batch size or default from config
    process_batch_size = batch_size or get_batch_size()
    
    total_refreshed = 0
    total_items = len(items)
    
    # Process in batches for better memory efficiency
    for i in range(0, total_items, process_batch_size):
        batch = items[i:i + process_batch_size]
        
        # Compute embeddings for batch (CPU-bound, runs sync)
        embedding_results = compute_embeddings_batch(batch)
        
        if embedding_results:
            # Persist batch using async session
            persisted = await persist_embeddings_batch_async(db, embedding_results)
            total_refreshed += persisted
            
            logger.info(f"Processed batch {i//process_batch_size + 1}: {persisted}/{len(batch)} embeddings refreshed")
    
    logger.info(f"Async batch refresh completed: {total_refreshed}/{total_items} embeddings refreshed")
    return total_refreshed


async def persist_embeddings_batch_async(db, embeddings: List[tuple[int, List[float]]]) -> int:
    """
    Persist multiple embeddings to database in a single transaction (async version).
    
    Args:
        db: AsyncSession database session
        embeddings: List of tuples (item_id, embedding_list)
        
    Returns:
        Number of successfully persisted embeddings
    """
    from sqlalchemy import select
    
    if not embeddings:
        return 0
    
    try:
        # Get all item IDs
        item_ids = [item_id for item_id, _ in embeddings]
        
        # Fetch all items in one query
        result = await db.execute(
            select(WardrobeItem).where(WardrobeItem.id.in_(item_ids))
        )
        items = result.scalars().all()
        item_map = {item.id: item for item in items}
        
        # Update items with embeddings
        updated = 0
        for item_id, embedding in embeddings:
            if item_id in item_map:
                item_map[item_id].embedding = embedding
                updated += 1
            else:
                logger.warning(f"Item {item_id} not found for batch embedding update")
        
        # Single commit for all updates
        await db.commit()
        logger.debug(f"Async batch persisted {updated} embeddings")
        return updated
        
    except Exception as e:
        logger.error(f"Failed to persist async batch embeddings: {e}")
        await db.rollback()
        return 0


"""
Retrieval-Augmented Generation (RAG) module for outfit suggestions.
Retrieves only relevant wardrobe items based on semantic similarity to user queries.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session

from .embedding import Embedder
from ..database import WardrobeItem
from ..config import settings
from ..utils.profiler import get_profiler
from ..utils.embedding_service import get_stored_embedding, compute_embedding_for_item, persist_embedding

logger = logging.getLogger(__name__)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors (0 = no similarity, 1 = identical)"""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


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


def retrieve_relevant_items(
    query: str,
    db: Session,
    user_id: int,
    limit_per_category: Optional[int] = None,
    min_items_per_category: Optional[int] = None,
    min_total_items: Optional[int] = None,
    use_intent_boost: bool = True
) -> List[WardrobeItem]:
    """
    Retrieve relevant wardrobe items using semantic search.
    
    Args:
        query: User's outfit request (e.g., "business meeting", "casual date")
        db: Database session
        user_id: ID of the user to filter items for
        limit_per_category: Maximum items to retrieve per category (None = auto-calculate from data volume)
        min_items_per_category: Minimum items required per category before fallback (None = auto-calculate)
        min_total_items: Minimum total items required before fallback to full wardrobe (None = auto-calculate)
        use_intent_boost: Whether to boost items based on intent classification (default: True)
    
    Returns:
        List of WardrobeItem objects, filtered by semantic relevance
    """
    try:
        profiler = get_profiler()
        
        # OPTIMIZATION: First get count to determine if we need RAG filtering
        # This avoids loading all items into memory if wardrobe is small
        with profiler.measure("db_query_count"):
            total_count = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).count()
        
        if total_count == 0:
            logger.info("No wardrobe items found in database")
            return []
        
        # Calculate adaptive thresholds based on data volume if not provided
        if limit_per_category is None or min_items_per_category is None or min_total_items is None:
            adaptive_thresholds = settings.get_adaptive_rag_thresholds(total_count)
            limit_per_category = limit_per_category or adaptive_thresholds["limit_per_category"]
            min_items_per_category = min_items_per_category or adaptive_thresholds["min_items_per_category"]
            min_total_items = min_total_items or adaptive_thresholds["min_total_items"]
            logger.debug(f"Adaptive RAG thresholds for {total_count} items: "
                        f"limit_per_category={limit_per_category}, "
                        f"min_items_per_category={min_items_per_category}, "
                        f"min_total_items={min_total_items}")
        
        # If wardrobe is small, return all items (no need for filtering)
        if total_count < min_total_items:
            logger.info(f"Wardrobe size ({total_count}) is below minimum ({min_total_items}), returning all items")
            with profiler.measure("db_query_all_items"):
                return db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
        
        # OPTIMIZATION: Only query items with embeddings first (RAG requires embeddings)
        # This reduces memory usage and speeds up processing for large wardrobes
        with profiler.measure("db_query_items_with_embeddings"):
            all_items = db.query(WardrobeItem).filter(
                WardrobeItem.user_id == user_id,
                WardrobeItem.embedding.isnot(None)
            ).all()
        
        # If no items have embeddings, fallback to all items
        if not all_items:
            logger.warning("No items with embeddings found, falling back to all items")
            with profiler.measure("db_query_all_items"):
                all_items = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
        
        # Initialize embedder
        emb = Embedder.instance()
        
        # Compute query embedding
        with profiler.measure("embedding_query"):
            query_embedding = emb.encode([query])[0]
        
        # Optionally compute intent embedding for hybrid scoring
        intent_embedding = None
        if use_intent_boost:
            try:
                with profiler.measure("embedding_intent"):
                    from .intent import classify_intent_zero_shot
                    intent_obj = classify_intent_zero_shot(query)
                    intent_label = getattr(intent_obj, "label", "casual")
                    intent_embedding = emb.encode([intent_label])[0]
            except Exception as e:
                logger.warning(f"Failed to compute intent embedding: {e}")
        
        # Group items by category
        items_by_category: Dict[str, List[Tuple[WardrobeItem, float]]] = {}
        
        # Score all items - use stored embeddings when available
        item_objects = []
        item_embeddings_list = []
        items_needing_embedding = []
        item_texts_needing_embedding = []
        
        for item in all_items:
            searchable_text = _create_searchable_text(item)
            if not searchable_text:
                continue
            
            # Try to use stored embedding first
            stored_embedding = get_stored_embedding(item)
            if stored_embedding is not None:
                item_objects.append(item)
                item_embeddings_list.append(stored_embedding)
            else:
                # Queue for batch computation
                items_needing_embedding.append(item)
                item_texts_needing_embedding.append(searchable_text)
        
        # Compute embeddings for items that don't have stored embeddings
        if items_needing_embedding:
            try:
                with profiler.measure("embedding_items_batch"):
                    computed_embeddings = emb.encode(item_texts_needing_embedding)
                
                # Store computed embeddings asynchronously (non-blocking)
                for item, embedding_vec in zip(items_needing_embedding, computed_embeddings):
                    item_objects.append(item)
                    item_embeddings_list.append(embedding_vec)
                    # Queue async persistence (non-blocking)
                    from ..utils.embedding_service import queue_embedding_refresh
                    queue_embedding_refresh(item.id)
            except Exception as e:
                logger.error(f"Failed to compute item embeddings: {e}")
                # Fallback: include items without embeddings (they'll be scored as 0)
                item_objects.extend(items_needing_embedding)
                # Create zero embeddings for failed items
                if item_objects:
                    embedding_dim = len(item_embeddings_list[0]) if item_embeddings_list else 384
                    zero_emb = np.zeros(embedding_dim, dtype=np.float32)
                    item_embeddings_list.extend([zero_emb] * len(items_needing_embedding))
        
        if not item_objects:
            logger.warning("No items with searchable text found")
            return all_items  # Fallback to all items
        
        item_embeddings = np.array(item_embeddings_list)
        
        # Score items by similarity
        for item, item_emb in zip(item_objects, item_embeddings):
            # Compute similarity to query
            query_similarity = _cosine(query_embedding, item_emb)
            
            # Optionally boost by intent similarity
            if intent_embedding is not None:
                intent_similarity = _cosine(intent_embedding, item_emb)
                # Weighted combination: 70% query, 30% intent
                final_score = 0.7 * query_similarity + 0.3 * intent_similarity
            else:
                final_score = query_similarity
            
            # Get item category (normalize to lowercase)
            category = (item.category or "unknown").lower()
            
            # Group by category
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append((item, final_score))
        
        # Sort by score within each category and take top-k
        retrieved_items = []
        required_categories = ["top", "bottom", "footwear"]
        
        for category, scored_items in items_by_category.items():
            # Sort by score (descending)
            scored_items.sort(key=lambda x: x[1], reverse=True)
            
            # Take top-k per category
            top_items = [item for item, score in scored_items[:limit_per_category]]
            retrieved_items.extend(top_items)
            
            # Log category stats
            if category in required_categories:
                logger.debug(f"Category '{category}': retrieved {len(top_items)} items (top score: {scored_items[0][1]:.3f})")
        
        # Check if we have minimum items in required categories
        category_counts = {}
        for item in retrieved_items:
            cat = (item.category or "unknown").lower()
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Check if any required category has too few items
        has_insufficient_items = False
        for req_cat in required_categories:
            count = category_counts.get(req_cat, 0)
            if count < min_items_per_category:
                logger.warning(f"Required category '{req_cat}' has only {count} items (minimum: {min_items_per_category})")
                has_insufficient_items = True
        
        # Fallback to full wardrobe if insufficient items
        if has_insufficient_items or len(retrieved_items) < min_total_items:
            logger.info(f"Retrieved {len(retrieved_items)} items, but minimum not met. Falling back to full wardrobe ({len(all_items)} items)")
            return all_items # all_items is already filtered by user_id
        
        logger.info(f"Retrieved {len(retrieved_items)} items from {len(all_items)} total (reduction: {100 * (1 - len(retrieved_items) / len(all_items)):.1f}%)")
        return retrieved_items
        
    except Exception as e:
        logger.error(f"Error in retrieve_relevant_items: {e}", exc_info=True)
        # Fallback to all items on error
        try:
            return db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
        except Exception:
            return []


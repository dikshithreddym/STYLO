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
    limit_per_category: int = 20,
    min_items_per_category: int = 3,
    min_total_items: int = 10,
    use_intent_boost: bool = True
) -> List[WardrobeItem]:
    """
    Retrieve relevant wardrobe items using semantic search.
    
    Args:
        query: User's outfit request (e.g., "business meeting", "casual date")
        db: Database session
        limit_per_category: Maximum items to retrieve per category (default: 20)
        min_items_per_category: Minimum items required per category before fallback (default: 3)
        min_total_items: Minimum total items required before fallback to full wardrobe (default: 10)
        use_intent_boost: Whether to boost items based on intent classification (default: True)
    
    Returns:
        List of WardrobeItem objects, filtered by semantic relevance
    """
    try:
        # Get all wardrobe items from database
        all_items = db.query(WardrobeItem).all()
        
        if not all_items:
            logger.info("No wardrobe items found in database")
            return []
        
        # If wardrobe is small, return all items (no need for filtering)
        if len(all_items) < min_total_items:
            logger.info(f"Wardrobe size ({len(all_items)}) is below minimum, returning all items")
            return all_items
        
        # Initialize embedder
        emb = Embedder.instance()
        
        # Compute query embedding
        query_embedding = emb.encode([query])[0]
        
        # Optionally compute intent embedding for hybrid scoring
        intent_embedding = None
        if use_intent_boost:
            try:
                from .intent import classify_intent_zero_shot
                intent_obj = classify_intent_zero_shot(query)
                intent_label = getattr(intent_obj, "label", "casual")
                intent_embedding = emb.encode([intent_label])[0]
            except Exception as e:
                logger.warning(f"Failed to compute intent embedding: {e}")
        
        # Group items by category
        items_by_category: Dict[str, List[Tuple[WardrobeItem, float]]] = {}
        
        # Score all items
        item_texts = []
        item_objects = []
        
        for item in all_items:
            searchable_text = _create_searchable_text(item)
            if not searchable_text:
                continue
            item_texts.append(searchable_text)
            item_objects.append(item)
        
        if not item_texts:
            logger.warning("No items with searchable text found")
            return all_items  # Fallback to all items
        
        # Compute embeddings for all items in batch
        try:
            item_embeddings = emb.encode(item_texts)
        except Exception as e:
            logger.error(f"Failed to compute item embeddings: {e}")
            return all_items  # Fallback to all items
        
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
            return all_items
        
        logger.info(f"Retrieved {len(retrieved_items)} items from {len(all_items)} total (reduction: {100 * (1 - len(retrieved_items) / len(all_items)):.1f}%)")
        return retrieved_items
        
    except Exception as e:
        logger.error(f"Error in retrieve_relevant_items: {e}", exc_info=True)
        # Fallback to all items on error
        try:
            return db.query(WardrobeItem).all()
        except Exception:
            return []


"""
Retrieval-Augmented Generation engine using FAISS and SentenceTransformers.
"""
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from .regulation_parser import RegulationClause

logger = get_logger("rag_engine")


class RAGEngine:
    """RAG engine for regulation retrieval and grounding."""
    
    def __init__(self):
        """Initialize RAG engine."""
        self.config = get_config()
        
        self.embedding_model = None
        self.index = None
        self.clauses: List[RegulationClause] = []
        self.chunk_texts: List[str] = []
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize embedding model and FAISS."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                model_name = self.config.get('rag.embedding_model', 'all-MiniLM-L6-v2')
                self.embedding_model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")
        else:
            logger.warning("SentenceTransformers not available")
    
    def build_index(self, clauses: List[RegulationClause]) -> bool:
        """
        Build FAISS index from regulation clauses.
        
        Args:
            clauses: List of regulation clauses
            
        Returns:
            True if successful
        """
        self.clauses = clauses
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not FAISS_AVAILABLE:
            logger.warning("RAG dependencies not available. Using keyword search.")
            return False
        
        if self.embedding_model is None:
            logger.warning("Embedding model not available")
            return False
        
        try:
            logger.info("Building FAISS index")
            
            # Prepare texts for embedding
            self.chunk_texts = []
            for clause in clauses:
                text = f"{clause.clause_id}: {clause.text}"
                self.chunk_texts.append(text)
            
            if not self.chunk_texts:
                logger.warning("No clauses to index")
                return False
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(
                self.chunk_texts,
                show_progress_bar=False
            )
            
            # Normalize embeddings
            faiss.normalize_L2(embeddings)
            
            # Build FAISS index
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(embeddings)
            
            logger.info(f"Built index with {len(self.chunk_texts)} clauses")
            return True
            
        except Exception as e:
            logger.error(f"Error building index: {e}")
            return False
    
    def retrieve(self, query: str, top_k: int = None) -> List[Tuple[RegulationClause, float]]:
        """
        Retrieve relevant clauses for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (clause, score) tuples
        """
        if top_k is None:
            top_k = self.config.get('rag.top_k', 5)
        
        # Use FAISS if available
        if self.index is not None and self.embedding_model is not None:
            return self._retrieve_faiss(query, top_k)
        
        # Fallback to keyword search
        return self._retrieve_keyword(query, top_k)
    
    def _retrieve_faiss(self, query: str, top_k: int) -> List[Tuple[RegulationClause, float]]:
        """Retrieve using FAISS."""
        try:
            # Encode query
            query_embedding = self.embedding_model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.clauses):
                    clause = self.clauses[idx]
                    score = float(scores[0][i])
                    results.append((clause, score))
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS retrieval error: {e}")
            return []
    
    def _retrieve_keyword(self, query: str, top_k: int) -> List[Tuple[RegulationClause, float]]:
        """Fallback keyword-based retrieval."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_clauses = []
        for clause in self.clauses:
            clause_text = clause.text.lower()
            clause_words = set(clause_text.split())
            
            # Calculate overlap
            overlap = len(query_words & clause_words)
            score = overlap / max(len(query_words), 1)
            
            if score > 0:
                scored_clauses.append((clause, score))
        
        # Sort by score
        scored_clauses.sort(key=lambda x: x[1], reverse=True)
        
        return scored_clauses[:top_k]
    
    def validate_claim(self, claim: str, context_clauses: List[RegulationClause]) -> Dict[str, Any]:
        """
        Validate a claim against regulation clauses.
        
        Args:
            claim: Claim to validate
            context_clauses: Relevant regulation clauses
            
        Returns:
            Validation result
        """
        if not context_clauses:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'reason': 'No regulation context available'
            }
        
        # Simple validation: check if claim keywords match clause keywords
        claim_lower = claim.lower()
        
        supporting_clauses = []
        for clause in context_clauses:
            # Check for keyword overlap
            clause_lower = clause.text.lower()
            
            # Extract key terms
            key_terms = ['width', 'distance', 'height', 'exit', 'door', 'stair']
            
            matches = 0
            for term in key_terms:
                if term in claim_lower and term in clause_lower:
                    matches += 1
            
            if matches > 0:
                supporting_clauses.append({
                    'clause_id': clause.clause_id,
                    'text': clause.text[:200],
                    'matches': matches
                })
        
        is_valid = len(supporting_clauses) > 0
        confidence = min(len(supporting_clauses) / 3, 1.0)
        
        return {
            'is_valid': is_valid,
            'confidence': confidence,
            'supporting_clauses': supporting_clauses
        }

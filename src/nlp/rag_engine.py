"""Regulation evidence retrieval with TF-IDF and optional embeddings."""
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

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
        self.faiss = None
        self.lexical_vectorizer = None
        self.lexical_matrix = None
        
        # Heavy ML libraries are loaded lazily in build_index(). This keeps the
        # Streamlit app shell responsive on Community Cloud before users upload
        # regulations or explicitly use RAG grounding.
    
    def _initialize(self) -> None:
        """Initialize embedding model and FAISS."""
        if self.embedding_model is not None and self.faiss is not None:
            return
        if not self.config.get("rag.vector_enabled", False):
            logger.info("Vector embeddings disabled; using evaluated TF-IDF evidence retrieval.")
            return

        try:
            from sentence_transformers import SentenceTransformer
            import faiss
        except ImportError:
            logger.warning("Embedding dependencies unavailable; using TF-IDF evidence retrieval.")
            return

        self.faiss = faiss
        try:
            model_name = self.config.get('rag.embedding_model', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
    
    def build_index(self, clauses: List[RegulationClause]) -> bool:
        """
        Build FAISS index from regulation clauses.
        
        Args:
            clauses: List of regulation clauses
            
        Returns:
            True if successful
        """
        self.clauses = clauses
        self._build_lexical_index()
        self._initialize()
        
        if self.embedding_model is None or self.faiss is None:
            logger.info("Using TF-IDF lexical regulation evidence retrieval.")
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
            self.faiss.normalize_L2(embeddings)
            
            # Build FAISS index
            dimension = embeddings.shape[1]
            self.index = self.faiss.IndexFlatIP(dimension)
            self.index.add(embeddings)
            
            logger.info(f"Built index with {len(self.chunk_texts)} clauses")
            return True
            
        except Exception as e:
            logger.error(f"Error building index: {e}")
            return False

    def retrieval_mode(self) -> str:
        """Return the active evidence-retrieval mechanism."""
        if self.index is not None and self.embedding_model is not None:
            return "sentence_embeddings"
        if self.lexical_matrix is not None and self.lexical_vectorizer is not None:
            return "tfidf_lexical"
        return "unavailable"

    def _build_lexical_index(self) -> bool:
        """Build the evaluated TF-IDF fallback without loading embedding models."""
        self.chunk_texts = [f"{clause.clause_id}: {clause.text}" for clause in self.clauses]
        if not self.chunk_texts:
            self.lexical_vectorizer = None
            self.lexical_matrix = None
            return False
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.lexical_vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                sublinear_tf=True,
            )
            self.lexical_matrix = self.lexical_vectorizer.fit_transform(self.chunk_texts)
            return True
        except Exception as exc:
            logger.warning(f"Could not build TF-IDF evidence index: {exc}")
            self.lexical_vectorizer = None
            self.lexical_matrix = None
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
        
        # Fall back to evaluated lexical retrieval.
        return self._retrieve_keyword(query, top_k)
    
    def _retrieve_faiss(self, query: str, top_k: int) -> List[Tuple[RegulationClause, float]]:
        """Retrieve using FAISS."""
        try:
            # Encode query
            query_embedding = self.embedding_model.encode([query])
            self.faiss.normalize_L2(query_embedding)
            
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
        """Retrieve with the evaluated TF-IDF fallback."""
        if self.lexical_matrix is None or self.lexical_vectorizer is None:
            self._build_lexical_index()
        if self.lexical_matrix is None or self.lexical_vectorizer is None:
            return []

        query_vector = self.lexical_vectorizer.transform([query])
        scores = (query_vector @ self.lexical_matrix.T).toarray().ravel()
        ranked_indices = scores.argsort()[::-1]
        return [
            (self.clauses[index], float(scores[index]))
            for index in ranked_indices
            if scores[index] > 0
        ][:top_k]
    
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

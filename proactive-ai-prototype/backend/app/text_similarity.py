"""
Text Similarity Service.

Implements TF-IDF based text similarity for better candidate retrieval
and ranking. This provides semantic matching beyond simple keyword overlap.

Design for refactoring:
- Can be replaced with embedding-based similarity (sentence-transformers)
- Can integrate with vector databases (Pinecone, Weaviate, Milvus)
"""

import math
import re
from collections import Counter
from typing import Optional


class TextSimilarity:
    """
    TF-IDF based text similarity calculator.

    Provides semantic similarity scores between documents without
    requiring external ML libraries.
    """

    def __init__(self):
        self._document_frequencies: dict[str, int] = {}
        self._num_documents: int = 0
        self._stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'
        }

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into lowercase words, removing stopwords and punctuation.
        """
        # Convert to lowercase and split on non-alphanumeric
        words = re.findall(r'\b[a-z][a-z0-9]*\b', text.lower())
        # Remove stopwords and short words
        return [w for w in words if w not in self._stopwords and len(w) > 2]

    def compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """
        Compute term frequency for a document.

        Uses augmented frequency to prevent bias towards longer documents:
        TF(t) = 0.5 + 0.5 * (f(t) / max_f)
        """
        if not tokens:
            return {}

        counts = Counter(tokens)
        max_freq = max(counts.values())

        return {
            term: 0.5 + 0.5 * (freq / max_freq)
            for term, freq in counts.items()
        }

    def compute_idf(self, term: str) -> float:
        """
        Compute inverse document frequency for a term.

        IDF(t) = log(N / (1 + df(t)))
        """
        df = self._document_frequencies.get(term, 0)
        return math.log(self._num_documents / (1 + df))

    def build_index(self, documents: list[str]) -> None:
        """
        Build the IDF index from a corpus of documents.

        Call this once with all candidate documents to enable TF-IDF scoring.
        """
        self._num_documents = len(documents)
        self._document_frequencies = {}

        for doc in documents:
            tokens = set(self.tokenize(doc))
            for token in tokens:
                self._document_frequencies[token] = \
                    self._document_frequencies.get(token, 0) + 1

    def compute_tfidf_vector(self, text: str) -> dict[str, float]:
        """
        Compute TF-IDF vector for a document.
        """
        tokens = self.tokenize(text)
        tf = self.compute_tf(tokens)

        return {
            term: tf_score * self.compute_idf(term)
            for term, tf_score in tf.items()
        }

    def cosine_similarity(
        self,
        vec1: dict[str, float],
        vec2: dict[str, float]
    ) -> float:
        """
        Compute cosine similarity between two TF-IDF vectors.
        """
        if not vec1 or not vec2:
            return 0.0

        # Find common terms
        common_terms = set(vec1.keys()) & set(vec2.keys())

        if not common_terms:
            return 0.0

        # Compute dot product
        dot_product = sum(vec1[t] * vec2[t] for t in common_terms)

        # Compute magnitudes
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.

        Returns a score between 0 and 1.
        """
        vec1 = self.compute_tfidf_vector(text1)
        vec2 = self.compute_tfidf_vector(text2)
        return self.cosine_similarity(vec1, vec2)

    def find_similar(
        self,
        query: str,
        documents: list[tuple[str, str]],  # (id, text) pairs
        top_k: int = 10
    ) -> list[tuple[str, float]]:
        """
        Find most similar documents to a query.

        Args:
            query: The search query
            documents: List of (id, text) pairs to search
            top_k: Number of results to return

        Returns:
            List of (id, similarity_score) pairs, sorted by score descending
        """
        query_vec = self.compute_tfidf_vector(query)

        scores = []
        for doc_id, doc_text in documents:
            doc_vec = self.compute_tfidf_vector(doc_text)
            score = self.cosine_similarity(query_vec, doc_vec)
            if score > 0:
                scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class QueryExpander:
    """
    Expands user queries with related terms for better retrieval.
    """

    # Domain-specific synonyms and related terms
    EXPANSIONS = {
        'kafka': ['streaming', 'messaging', 'event-sourcing', 'pub-sub', 'queue'],
        'distributed': ['distributed-systems', 'microservices', 'scalability'],
        'database': ['sql', 'nosql', 'storage', 'persistence', 'data'],
        'ml': ['machine-learning', 'ai', 'deep-learning', 'neural-network'],
        'kubernetes': ['k8s', 'container', 'docker', 'orchestration', 'devops'],
        'rust': ['systems-programming', 'memory-safety', 'performance'],
        'async': ['concurrency', 'parallel', 'threading', 'non-blocking'],
        'api': ['rest', 'graphql', 'endpoint', 'http', 'microservice'],
        'test': ['testing', 'unit-test', 'integration', 'tdd', 'quality'],
        'security': ['auth', 'authentication', 'authorization', 'encryption'],
    }

    def expand(self, query: str) -> list[str]:
        """
        Expand a query with related terms.

        Returns list of additional terms to include in search.
        """
        words = query.lower().split()
        expansions = []

        for word in words:
            if word in self.EXPANSIONS:
                expansions.extend(self.EXPANSIONS[word])

        return list(set(expansions))


class ContentAnalyzer:
    """
    Analyzes content to extract features for recommendation.
    """

    def __init__(self):
        self.similarity = TextSimilarity()

    def extract_topics(self, text: str, top_k: int = 5) -> list[str]:
        """
        Extract main topics from text based on TF-IDF scores.
        """
        tokens = self.similarity.tokenize(text)
        tf = self.similarity.compute_tf(tokens)

        # Sort by TF score
        sorted_terms = sorted(tf.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in sorted_terms[:top_k]]

    def compute_reading_level(self, text: str) -> str:
        """
        Estimate reading difficulty level.

        Uses average word length and sentence complexity as proxies.
        """
        words = text.split()
        if not words:
            return "intermediate"

        avg_word_length = sum(len(w) for w in words) / len(words)

        # Simple heuristic based on average word length
        if avg_word_length < 5:
            return "beginner"
        elif avg_word_length < 6.5:
            return "intermediate"
        else:
            return "advanced"

    def compute_content_hash(self, text: str) -> str:
        """
        Compute a simple hash for content deduplication.
        """
        # Use first 100 chars normalized as a simple hash
        normalized = re.sub(r'\s+', ' ', text.lower().strip())[:100]
        return str(hash(normalized))

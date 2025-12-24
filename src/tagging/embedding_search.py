"""
Embedding-based Similarity Search

Provides vector similarity search for finding related questions
using pre-computed KoSBERT embeddings.
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from db.connection import get_connection


class EmbeddingSearch:
    """Search questions by embedding similarity."""

    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self._embeddings_cache = None
        self._question_ids_cache = None

    def _load_embeddings(self):
        """Load all embeddings into memory for fast search."""
        if self._embeddings_cache is not None:
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT question_id, embedding FROM embeddings
            ORDER BY question_id
        """)
        rows = cursor.fetchall()

        self._question_ids_cache = []
        embeddings_list = []

        for row in rows:
            self._question_ids_cache.append(row[0])
            # Deserialize from BLOB (768 float32 values)
            embedding = np.frombuffer(row[1], dtype=np.float32)
            embeddings_list.append(embedding)

        self._embeddings_cache = np.array(embeddings_list)
        print(f"Loaded {len(self._question_ids_cache)} embeddings")

    def get_embedding(self, question_id: str) -> np.ndarray:
        """Get embedding for a specific question."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT embedding FROM embeddings WHERE question_id = ?",
            (question_id,)
        )
        row = cursor.fetchone()
        if row:
            return np.frombuffer(row[0], dtype=np.float32)
        return None

    def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        exclude_ids: list = None,
        diagnosis_type: str = None,
    ) -> list:
        """
        Find most similar questions by cosine similarity.

        Args:
            query_embedding: Query vector (768 dimensions)
            top_k: Number of results to return
            exclude_ids: Question IDs to exclude from results
            diagnosis_type: Filter by diagnosis type (OD, LD, MA, DD)

        Returns:
            List of (question_id, similarity_score) tuples
        """
        self._load_embeddings()

        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)

        # Normalize all embeddings
        norms = np.linalg.norm(self._embeddings_cache, axis=1, keepdims=True)
        normalized = self._embeddings_cache / norms

        # Compute cosine similarities
        similarities = np.dot(normalized, query_norm)

        # Build mask for filtering
        mask = np.ones(len(similarities), dtype=bool)

        if exclude_ids:
            exclude_set = set(exclude_ids)
            for i, qid in enumerate(self._question_ids_cache):
                if qid in exclude_set:
                    mask[i] = False

        if diagnosis_type:
            # Get question IDs for this diagnosis type
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT question_id FROM questions WHERE diagnosis_type = ?",
                (diagnosis_type,)
            )
            valid_ids = set(row[0] for row in cursor.fetchall())
            for i, qid in enumerate(self._question_ids_cache):
                if qid not in valid_ids:
                    mask[i] = False

        # Apply mask
        similarities[~mask] = -1

        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Valid result
                results.append((
                    self._question_ids_cache[idx],
                    float(similarities[idx])
                ))

        return results

    def search_by_question(
        self,
        question_id: str,
        top_k: int = 10,
        same_diagnosis_only: bool = False,
    ) -> list:
        """
        Find questions similar to a given question.

        Args:
            question_id: Source question ID
            top_k: Number of results
            same_diagnosis_only: Only return same diagnosis type

        Returns:
            List of (question_id, question_text, similarity, diagnosis_type)
        """
        # Get query embedding
        query_emb = self.get_embedding(question_id)
        if query_emb is None:
            return []

        # Get diagnosis type if filtering
        diagnosis_type = None
        if same_diagnosis_only:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT diagnosis_type FROM questions WHERE question_id = ?",
                (question_id,)
            )
            row = cursor.fetchone()
            if row:
                diagnosis_type = row[0]

        # Search
        similar = self.search_similar(
            query_emb,
            top_k=top_k + 1,  # +1 because query itself will be in results
            exclude_ids=[question_id],
            diagnosis_type=diagnosis_type,
        )

        # Get question details
        cursor = self.conn.cursor()
        results = []
        for qid, score in similar[:top_k]:
            cursor.execute(
                "SELECT question_text, diagnosis_type FROM questions WHERE question_id = ?",
                (qid,)
            )
            row = cursor.fetchone()
            if row:
                results.append((qid, row[0], score, row[1]))

        return results

    def find_cluster_members(self, master_id: str) -> list:
        """Find all questions in a cluster by master question ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT q.question_id, q.question_text, q.is_representative
            FROM questions q
            WHERE q.master_question_id = ?
            ORDER BY q.is_representative DESC, q.question_id
        """, (master_id,))
        return cursor.fetchall()


def demo_search():
    """Demo the embedding search."""
    print("=" * 60)
    print("  Embedding Search Demo")
    print("=" * 60)

    searcher = EmbeddingSearch()

    # Get a sample representative question
    cursor = searcher.conn.cursor()
    cursor.execute("""
        SELECT question_id, question_text, diagnosis_type, master_question_id
        FROM questions
        WHERE is_representative = 1
        LIMIT 1
    """)
    sample = cursor.fetchone()

    if sample:
        print(f"\n[Query Question]")
        print(f"  ID: {sample[0]}")
        print(f"  Text: {sample[1][:80]}...")
        print(f"  Type: {sample[2]}")
        print(f"  Master: {sample[3]}")

        # Find similar questions
        print(f"\n[Similar Questions (Top 5)]")
        results = searcher.search_by_question(sample[0], top_k=5)
        for qid, text, score, dtype in results:
            print(f"  {score:.3f} | {dtype} | {text[:50]}...")

        # Find cluster members
        print(f"\n[Cluster Members for {sample[3]}]")
        members = searcher.find_cluster_members(sample[3])
        for qid, text, is_rep in members[:5]:
            rep_mark = "*" if is_rep else " "
            print(f"  {rep_mark} {qid}: {text[:50]}...")
        if len(members) > 5:
            print(f"  ... (+{len(members)-5} more)")

    searcher.conn.close()


if __name__ == "__main__":
    demo_search()

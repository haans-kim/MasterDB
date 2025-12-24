"""
Auto-Tagging System

Automatically suggests taxonomy tags for questions based on:
1. Similar question tags (embedding-based)
2. Cluster representative tags (for cluster members)
3. Text pattern matching (keyword-based)
"""

import sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from db.connection import get_connection
from tagging.embedding_search import EmbeddingSearch


class AutoTagger:
    """Automatic taxonomy tagging for questions."""

    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.searcher = EmbeddingSearch(self.conn)
        self._term_cache = None

    def _load_terms(self):
        """Load taxonomy terms into cache."""
        if self._term_cache is not None:
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT term_id, term, term_type, aliases
            FROM taxonomy
        """)
        self._term_cache = {}
        for row in cursor.fetchall():
            self._term_cache[row[0]] = {
                "term": row[1],
                "type": row[2],
                "aliases": row[3],
            }

    def get_question_tags(self, question_id: str) -> dict:
        """Get existing tags for a question."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.term_id, t.term, t.term_type, qt.tag_type, qt.confidence
            FROM question_tags qt
            JOIN taxonomy t ON qt.term_id = t.term_id
            WHERE qt.question_id = ?
        """, (question_id,))

        tags = {"themes": [], "concepts": [], "aspects": []}
        for row in cursor.fetchall():
            tag_type = row[3]
            if tag_type in tags:
                tags[tag_type].append({
                    "term_id": row[0],
                    "term": row[1],
                    "term_type": row[2],
                    "confidence": row[4],
                })
        return tags

    def suggest_from_similar(
        self,
        question_id: str,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> dict:
        """
        Suggest tags based on similar questions' tags.

        Args:
            question_id: Target question
            top_k: Number of similar questions to consider
            min_similarity: Minimum similarity threshold

        Returns:
            Dict with suggested tags by type, each with confidence scores
        """
        # Find similar questions
        similar = self.searcher.search_by_question(
            question_id,
            top_k=top_k,
            same_diagnosis_only=True,
        )

        # Collect tags from similar questions
        tag_votes = {
            "themes": Counter(),
            "concepts": Counter(),
            "aspects": Counter(),
        }
        similarity_weights = {}

        for sim_qid, _, similarity, _ in similar:
            if similarity < min_similarity:
                continue

            sim_tags = self.get_question_tags(sim_qid)
            for tag_type, tags in sim_tags.items():
                for tag in tags:
                    key = (tag["term_id"], tag["term"])
                    tag_votes[tag_type][key] += similarity
                    if key not in similarity_weights:
                        similarity_weights[key] = []
                    similarity_weights[key].append(similarity)

        # Convert to suggestions with confidence
        suggestions = {}
        for tag_type, votes in tag_votes.items():
            suggestions[tag_type] = []
            for (term_id, term), score in votes.most_common(5):
                avg_sim = sum(similarity_weights[(term_id, term)]) / len(similarity_weights[(term_id, term)])
                suggestions[tag_type].append({
                    "term_id": term_id,
                    "term": term,
                    "confidence": min(score / top_k, 1.0),
                    "avg_similarity": avg_sim,
                    "vote_count": len(similarity_weights[(term_id, term)]),
                })

        return suggestions

    def suggest_from_cluster(self, question_id: str) -> dict:
        """
        Suggest tags based on cluster representative's tags.

        If question is in a cluster, inherit tags from representative.
        """
        cursor = self.conn.cursor()

        # Get master question ID
        cursor.execute("""
            SELECT master_question_id, is_representative
            FROM questions
            WHERE question_id = ?
        """, (question_id,))
        row = cursor.fetchone()

        if not row or not row[0]:
            return {}

        master_id = row[0]
        is_representative = row[1]

        if is_representative:
            # This IS the representative, no inheritance needed
            return {}

        # Get representative question
        cursor.execute("""
            SELECT question_id FROM master_questions WHERE master_id = ?
        """, (master_id,))
        rep_row = cursor.fetchone()

        if not rep_row:
            return {}

        rep_question_id = rep_row[0]

        # Get representative's tags
        rep_tags = self.get_question_tags(rep_question_id)

        # Convert to suggestions
        suggestions = {}
        for tag_type, tags in rep_tags.items():
            suggestions[tag_type] = []
            for tag in tags:
                suggestions[tag_type].append({
                    "term_id": tag["term_id"],
                    "term": tag["term"],
                    "confidence": 0.9,  # High confidence from cluster
                    "source": "cluster_representative",
                })

        return suggestions

    def suggest_tags(
        self,
        question_id: str,
        include_similar: bool = True,
        include_cluster: bool = True,
    ) -> dict:
        """
        Get all tag suggestions for a question.

        Combines suggestions from:
        - Similar questions (embedding-based)
        - Cluster representative
        """
        all_suggestions = {
            "themes": [],
            "concepts": [],
            "aspects": [],
        }

        # Existing tags
        existing = self.get_question_tags(question_id)
        existing_ids = set()
        for tag_type in existing:
            for tag in existing[tag_type]:
                existing_ids.add(tag["term_id"])

        # Cluster-based suggestions
        if include_cluster:
            cluster_suggestions = self.suggest_from_cluster(question_id)
            for tag_type, tags in cluster_suggestions.items():
                for tag in tags:
                    if tag["term_id"] not in existing_ids:
                        tag["source"] = "cluster"
                        all_suggestions[tag_type].append(tag)
                        existing_ids.add(tag["term_id"])

        # Similarity-based suggestions
        if include_similar:
            similar_suggestions = self.suggest_from_similar(question_id)
            for tag_type, tags in similar_suggestions.items():
                for tag in tags:
                    if tag["term_id"] not in existing_ids:
                        tag["source"] = "similar"
                        all_suggestions[tag_type].append(tag)
                        existing_ids.add(tag["term_id"])

        return all_suggestions

    def apply_tag(
        self,
        question_id: str,
        term_id: int,
        tag_type: str,
        confidence: float = 1.0,
        is_auto: bool = True,
    ):
        """Apply a single tag to a question."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO question_tags
            (question_id, term_id, tag_type, confidence, is_auto_tagged)
            VALUES (?, ?, ?, ?, ?)
        """, (question_id, term_id, tag_type, confidence, is_auto))
        self.conn.commit()

        # Update usage count
        cursor.execute("""
            UPDATE taxonomy SET usage_count = (
                SELECT COUNT(*) FROM question_tags WHERE term_id = ?
            ) WHERE term_id = ?
        """, (term_id, term_id))
        self.conn.commit()

    def auto_tag_untagged(
        self,
        tag_type: str = "aspects",
        min_confidence: float = 0.8,
        limit: int = 100,
    ) -> int:
        """
        Automatically tag questions missing specific tag type.

        Returns number of questions tagged.
        """
        cursor = self.conn.cursor()

        # Find questions without this tag type
        cursor.execute(f"""
            SELECT q.question_id
            FROM questions q
            WHERE q.question_id NOT IN (
                SELECT question_id FROM question_tags WHERE tag_type = ?
            )
            LIMIT ?
        """, (tag_type, limit))

        questions = [row[0] for row in cursor.fetchall()]
        tagged_count = 0

        for qid in questions:
            suggestions = self.suggest_tags(qid)
            if tag_type in suggestions and suggestions[tag_type]:
                best = suggestions[tag_type][0]
                if best["confidence"] >= min_confidence:
                    self.apply_tag(
                        qid,
                        best["term_id"],
                        tag_type,
                        best["confidence"],
                        is_auto=True,
                    )
                    tagged_count += 1

        return tagged_count


def demo_auto_tagger():
    """Demo the auto-tagger."""
    print("=" * 60)
    print("  Auto-Tagger Demo")
    print("=" * 60)

    tagger = AutoTagger()
    cursor = tagger.conn.cursor()

    # Get a sample question
    cursor.execute("""
        SELECT q.question_id, q.question_text, q.diagnosis_type, q.master_question_id
        FROM questions q
        WHERE q.is_representative = 0
        AND q.master_question_id IS NOT NULL
        LIMIT 1
    """)
    sample = cursor.fetchone()

    if sample:
        print(f"\n[Target Question]")
        print(f"  ID: {sample[0]}")
        print(f"  Text: {sample[1][:80]}...")
        print(f"  Type: {sample[2]}")
        print(f"  Master: {sample[3]}")

        # Get existing tags
        existing = tagger.get_question_tags(sample[0])
        print(f"\n[Existing Tags]")
        for tag_type, tags in existing.items():
            if tags:
                print(f"  {tag_type}:")
                for t in tags:
                    print(f"    - {t['term']} (conf: {t['confidence']:.2f})")

        # Get suggestions
        print(f"\n[Tag Suggestions]")
        suggestions = tagger.suggest_tags(sample[0])
        for tag_type, tags in suggestions.items():
            if tags:
                print(f"  {tag_type}:")
                for t in tags[:3]:
                    print(f"    - {t['term']} (conf: {t['confidence']:.2f}, src: {t.get('source', 'N/A')})")

    tagger.conn.close()


if __name__ == "__main__":
    demo_auto_tagger()

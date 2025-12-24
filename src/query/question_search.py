"""
Question Search API

Provides search interface for MasterDB queries.
Supports:
- Text search (keyword matching)
- Taxonomy-based filtering
- Embedding similarity search
- Combined queries
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from db.connection import get_connection
from tagging.embedding_search import EmbeddingSearch


class QuestionSearch:
    """Search interface for questions."""

    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.embedding_search = EmbeddingSearch(self.conn)

    def search_by_text(
        self,
        keyword: str,
        diagnosis_type: str = None,
        limit: int = 20,
    ) -> list:
        """
        Search questions by keyword in text.

        Args:
            keyword: Search term
            diagnosis_type: Filter by OD, LD, MA, DD
            limit: Max results

        Returns:
            List of question dicts
        """
        cursor = self.conn.cursor()

        query = """
            SELECT q.question_id, q.question_text, q.diagnosis_type,
                   q.master_question_id, q.is_representative,
                   q.legacy_mid_category, q.legacy_sub_category
            FROM questions q
            WHERE q.question_text LIKE ?
        """
        params = [f"%{keyword}%"]

        if diagnosis_type:
            query += " AND q.diagnosis_type = ?"
            params.append(diagnosis_type)

        query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                "question_id": row[0],
                "question_text": row[1],
                "diagnosis_type": row[2],
                "master_question_id": row[3],
                "is_representative": bool(row[4]),
                "mid_category": row[5],
                "sub_category": row[6],
            })
        return results

    def search_by_taxonomy(
        self,
        term: str = None,
        term_type: str = None,
        tag_type: str = None,
        limit: int = 50,
    ) -> list:
        """
        Search questions by taxonomy term.

        Args:
            term: Taxonomy term to search for
            term_type: THEME, CONCEPT, or ASPECT
            tag_type: themes, concepts, or aspects
            limit: Max results

        Returns:
            List of question dicts with matched terms
        """
        cursor = self.conn.cursor()

        query = """
            SELECT DISTINCT q.question_id, q.question_text, q.diagnosis_type,
                   t.term, t.term_type, qt.confidence
            FROM questions q
            JOIN question_tags qt ON q.question_id = qt.question_id
            JOIN taxonomy t ON qt.term_id = t.term_id
            WHERE 1=1
        """
        params = []

        if term:
            query += " AND t.term LIKE ?"
            params.append(f"%{term}%")

        if term_type:
            query += " AND t.term_type = ?"
            params.append(term_type)

        if tag_type:
            query += " AND qt.tag_type = ?"
            params.append(tag_type)

        query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                "question_id": row[0],
                "question_text": row[1],
                "diagnosis_type": row[2],
                "matched_term": row[3],
                "term_type": row[4],
                "confidence": row[5],
            })
        return results

    def get_master_question_with_variants(self, master_id: str) -> dict:
        """
        Get a master question with all its cluster members.

        Args:
            master_id: Master question ID (e.g., OD_0001)

        Returns:
            Dict with master info and variant questions
        """
        cursor = self.conn.cursor()

        # Get master question info
        cursor.execute("""
            SELECT m.master_id, m.diagnosis_type, m.cluster_size,
                   q.question_id, q.question_text
            FROM master_questions m
            JOIN questions q ON m.question_id = q.question_id
            WHERE m.master_id = ?
        """, (master_id,))

        row = cursor.fetchone()
        if not row:
            return None

        result = {
            "master_id": row[0],
            "diagnosis_type": row[1],
            "cluster_size": row[2],
            "representative": {
                "question_id": row[3],
                "question_text": row[4],
            },
            "variants": [],
        }

        # Get all cluster members
        cursor.execute("""
            SELECT question_id, question_text, is_representative
            FROM questions
            WHERE master_question_id = ?
            ORDER BY is_representative DESC, question_id
        """, (master_id,))

        for row in cursor.fetchall():
            if not row[2]:  # Not representative
                result["variants"].append({
                    "question_id": row[0],
                    "question_text": row[1],
                })

        return result

    def get_taxonomy_tree(self, root_term: str = None) -> dict:
        """
        Get taxonomy hierarchy.

        Args:
            root_term: Starting term (default: all themes)

        Returns:
            Hierarchical dict of taxonomy
        """
        cursor = self.conn.cursor()

        if root_term:
            cursor.execute("""
                SELECT term_id, term, term_type, usage_count
                FROM taxonomy WHERE term = ?
            """, (root_term,))
        else:
            cursor.execute("""
                SELECT term_id, term, term_type, usage_count
                FROM taxonomy WHERE term_type = 'THEME'
                ORDER BY usage_count DESC
            """)

        roots = cursor.fetchall()
        tree = []

        for root in roots:
            node = {
                "term_id": root[0],
                "term": root[1],
                "term_type": root[2],
                "usage_count": root[3],
                "children": [],
            }

            # Get children
            cursor.execute("""
                SELECT t.term_id, t.term, t.term_type, t.usage_count
                FROM taxonomy t
                JOIN taxonomy_relations r ON t.term_id = r.to_term_id
                WHERE r.from_term_id = ?
                ORDER BY t.usage_count DESC
            """, (root[0],))

            for child in cursor.fetchall():
                child_node = {
                    "term_id": child[0],
                    "term": child[1],
                    "term_type": child[2],
                    "usage_count": child[3],
                    "children": [],
                }

                # Get grandchildren (aspects)
                cursor.execute("""
                    SELECT t.term_id, t.term, t.term_type, t.usage_count
                    FROM taxonomy t
                    JOIN taxonomy_relations r ON t.term_id = r.to_term_id
                    WHERE r.from_term_id = ?
                    ORDER BY t.usage_count DESC
                """, (child[0],))

                for grandchild in cursor.fetchall():
                    child_node["children"].append({
                        "term_id": grandchild[0],
                        "term": grandchild[1],
                        "term_type": grandchild[2],
                        "usage_count": grandchild[3],
                    })

                node["children"].append(child_node)

            tree.append(node)

        return tree

    def get_statistics(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.cursor()

        stats = {}

        # Table counts
        tables = ["companies", "surveys", "questions", "master_questions",
                  "embeddings", "taxonomy", "question_tags"]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]

        # Questions by diagnosis type
        cursor.execute("""
            SELECT diagnosis_type, COUNT(*) FROM questions
            GROUP BY diagnosis_type ORDER BY COUNT(*) DESC
        """)
        stats["questions_by_type"] = dict(cursor.fetchall())

        # Master questions by type
        cursor.execute("""
            SELECT diagnosis_type, COUNT(*) FROM master_questions
            GROUP BY diagnosis_type ORDER BY COUNT(*) DESC
        """)
        stats["masters_by_type"] = dict(cursor.fetchall())

        # Taxonomy terms by type
        cursor.execute("""
            SELECT term_type, COUNT(*) FROM taxonomy
            GROUP BY term_type
        """)
        stats["taxonomy_by_type"] = dict(cursor.fetchall())

        # Tags by type
        cursor.execute("""
            SELECT tag_type, COUNT(*) FROM question_tags
            GROUP BY tag_type
        """)
        stats["tags_by_type"] = dict(cursor.fetchall())

        return stats


def demo_search():
    """Demo search functionality."""
    search = QuestionSearch()

    print("=" * 60)
    print("  MasterDB Query Demo")
    print("=" * 60)

    # 1. Statistics
    print("\n[1. Database Statistics]")
    stats = search.get_statistics()
    print(f"  Questions: {stats['questions']:,}")
    print(f"  Master Questions: {stats['master_questions']:,}")
    print(f"  Taxonomy Terms: {stats['taxonomy']}")
    print(f"  Question Tags: {stats['question_tags']:,}")

    # 2. Text search
    print("\n[2. Text Search: '리더']")
    results = search.search_by_text("리더", limit=3)
    for r in results:
        print(f"  {r['question_id']} ({r['diagnosis_type']}): {r['question_text'][:50]}...")

    # 3. Taxonomy search
    print("\n[3. Taxonomy Search: term='리더십']")
    results = search.search_by_taxonomy(term="리더십", limit=3)
    for r in results:
        print(f"  {r['question_id']}: {r['matched_term']} ({r['term_type']})")

    # 4. Master question with variants
    print("\n[4. Master Question with Variants: OD_0001]")
    master = search.get_master_question_with_variants("OD_0001")
    if master:
        print(f"  Master: {master['master_id']} (cluster size: {master['cluster_size']})")
        print(f"  Representative: {master['representative']['question_text'][:60]}...")
        print(f"  Variants: {len(master['variants'])} questions")
        for v in master["variants"][:2]:
            print(f"    - {v['question_text'][:50]}...")

    # 5. Taxonomy tree sample
    print("\n[5. Taxonomy Tree: '조직진단']")
    tree = search.get_taxonomy_tree("조직진단")
    if tree:
        node = tree[0]
        print(f"  {node['term']} ({node['usage_count']} uses)")
        for child in node["children"][:3]:
            print(f"    ├─ {child['term']} ({child['usage_count']})")
            for gc in child["children"][:2]:
                print(f"    │   ├─ {gc['term']} ({gc['usage_count']})")

    search.conn.close()


if __name__ == "__main__":
    demo_search()

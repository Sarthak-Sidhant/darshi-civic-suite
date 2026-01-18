#!/usr/bin/env python3
"""
Export data from Firestore to JSON files for migration to PostgreSQL.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

# Initialize Firestore client
db = firestore.Client()

# Output directory
OUTPUT_DIR = Path("data/firestore_export")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def serialize_document(doc_dict: dict) -> dict:
    """Convert Firestore document to JSON-serializable format."""
    serialized = {}
    for key, value in doc_dict.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, list):
            serialized[key] = [
                v.isoformat() if isinstance(v, datetime) else v for v in value
            ]
        elif isinstance(value, dict):
            serialized[key] = serialize_document(value)
        else:
            serialized[key] = value
    return serialized


def export_collection(collection_name: str, output_file: str):
    """Export a Firestore collection to JSON file."""
    print(f"Exporting {collection_name}...")

    docs = []
    collection_ref = db.collection(collection_name)

    for doc in collection_ref.stream():
        doc_dict = doc.to_dict()
        doc_dict['id'] = doc.id
        docs.append(serialize_document(doc_dict))

    output_path = OUTPUT_DIR / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    print(f"  Exported {len(docs)} documents to {output_path}")
    return len(docs)


def export_subcollections():
    """Export all comments subcollections from reports."""
    print("Exporting comments subcollections...")

    all_comments = []
    reports_ref = db.collection('reports')

    for report_doc in reports_ref.stream():
        report_id = report_doc.id
        comments_ref = report_doc.reference.collection('comments')

        for comment_doc in comments_ref.stream():
            comment_dict = comment_doc.to_dict()
            comment_dict['id'] = comment_doc.id
            comment_dict['report_id'] = report_id
            all_comments.append(serialize_document(comment_dict))

    output_path = OUTPUT_DIR / 'comments.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_comments, f, indent=2, ensure_ascii=False)

    print(f"  Exported {len(all_comments)} comments to {output_path}")
    return len(all_comments)


def main():
    """Main export function."""
    print("=" * 60)
    print("Darshi Firestore Export Tool")
    print("=" * 60)
    print()

    stats = {}

    # Export main collections
    stats['users'] = export_collection('users', 'users.json')
    stats['reports'] = export_collection('reports', 'reports.json')

    # Export subcollections
    stats['comments'] = export_subcollections()

    # Export push subscriptions if they exist
    try:
        stats['push_subscriptions'] = export_collection(
            'push_subscriptions', 'push_subscriptions.json'
        )
    except Exception as e:
        print(f"  No push_subscriptions collection found: {e}")
        stats['push_subscriptions'] = 0

    print()
    print("=" * 60)
    print("Export Summary:")
    print("=" * 60)
    for collection, count in stats.items():
        print(f"  {collection}: {count} documents")
    print()
    print(f"Total documents exported: {sum(stats.values())}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print("=" * 60)


if __name__ == '__main__':
    main()

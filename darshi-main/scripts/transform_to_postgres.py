#!/usr/bin/env python3
"""
Transform exported Firestore JSON data to PostgreSQL-compatible SQL.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


INPUT_DIR = Path("data/firestore_export")
OUTPUT_DIR = Path("data/postgres_import")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def escape_sql_string(value: Any) -> str:
    """Escape string for SQL insertion."""
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        # Convert Python list to PostgreSQL array
        if not value:
            return "'{}'"
        # Escape each element
        escaped = [escape_sql_string(v).strip("'") for v in value]
        return "'{" + ','.join(f'"{e}"' for e in escaped) + "}'"
    if isinstance(value, dict):
        # Convert dict to JSON string
        return f"'{json.dumps(value)}'::jsonb"

    # String value - escape single quotes
    value_str = str(value).replace("'", "''").replace('\n', '\\n')
    return f"'{value_str}'"


def transform_users(users_data: list) -> str:
    """Transform users to SQL INSERT statements."""
    sql_lines = [
        "-- Users table import",
        "BEGIN;",
        "",
    ]

    for user in users_data:
        # Map Firestore fields to PostgreSQL columns
        username = escape_sql_string(user.get('username'))
        email = escape_sql_string(user.get('email'))
        phone = escape_sql_string(user.get('phone'))
        password_hash = escape_sql_string(user.get('password_hash'))
        role = escape_sql_string(user.get('role', 'citizen'))
        is_active = escape_sql_string(user.get('is_active', True))
        is_verified = escape_sql_string(user.get('is_verified', False))
        oauth_provider = escape_sql_string(user.get('oauth_provider'))
        oauth_id = escape_sql_string(user.get('oauth_id'))
        created_at = escape_sql_string(user.get('created_at'))
        updated_at = escape_sql_string(user.get('updated_at', user.get('created_at')))

        sql = f"""INSERT INTO users (username, email, phone, password_hash, role, is_active, is_verified, oauth_provider, oauth_id, created_at, updated_at)
VALUES ({username}, {email}, {phone}, {password_hash}, {role}, {is_active}, {is_verified}, {oauth_provider}, {oauth_id}, {created_at}, {updated_at})
ON CONFLICT (username) DO NOTHING;"""

        sql_lines.append(sql)

    sql_lines.extend(["", "COMMIT;", ""])
    return '\n'.join(sql_lines)


def transform_reports(reports_data: list) -> str:
    """Transform reports to SQL INSERT statements."""
    sql_lines = [
        "-- Reports table import",
        "BEGIN;",
        "",
    ]

    for report in reports_data:
        # Generate UUID for id (Firestore uses auto-generated IDs)
        report_id = escape_sql_string(report.get('id'))

        # Basic fields
        title = escape_sql_string(report.get('title'))
        description = escape_sql_string(report.get('description'))
        category = escape_sql_string(report.get('category'))
        severity = escape_sql_string(report.get('severity'))
        status = escape_sql_string(report.get('status', 'PENDING_VERIFICATION'))

        # Geospatial fields
        latitude = report.get('latitude')
        longitude = report.get('longitude')
        if latitude and longitude:
            location = f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)"
            lat_val = str(latitude)
            lng_val = str(longitude)
        else:
            location = 'NULL'
            lat_val = 'NULL'
            lng_val = 'NULL'

        geohash = escape_sql_string(report.get('geohash'))
        address = escape_sql_string(report.get('address'))
        city = escape_sql_string(report.get('city'))
        state = escape_sql_string(report.get('state'))
        country = escape_sql_string(report.get('country', 'India'))

        # Arrays and complex types
        image_urls = escape_sql_string(report.get('image_urls', []))
        image_hash = escape_sql_string(report.get('image_hash'))
        upvotes = escape_sql_string(report.get('upvotes', []))

        # Counts
        upvote_count = report.get('upvote_count', 0)
        comment_count = report.get('comment_count', 0)

        # References
        submitted_by = escape_sql_string(report.get('submitted_by'))
        duplicate_of = escape_sql_string(report.get('duplicate_of'))

        # JSON fields
        ai_analysis = escape_sql_string(report.get('ai_analysis', {}))
        timeline = escape_sql_string(report.get('timeline', []))

        # Timestamps
        created_at = escape_sql_string(report.get('created_at'))
        updated_at = escape_sql_string(report.get('updated_at', report.get('created_at')))
        verified_at = escape_sql_string(report.get('verified_at'))
        resolved_at = escape_sql_string(report.get('resolved_at'))

        sql = f"""INSERT INTO reports (id, title, description, category, severity, status, location, latitude, longitude, geohash, address, city, state, country, image_urls, image_hash, submitted_by, upvotes, upvote_count, comment_count, ai_analysis, duplicate_of, timeline, created_at, updated_at, verified_at, resolved_at)
VALUES ({report_id}::uuid, {title}, {description}, {category}, {severity}, {status}, {location}, {lat_val}, {lng_val}, {geohash}, {address}, {city}, {state}, {country}, {image_urls}, {image_hash}, {submitted_by}, {upvotes}, {upvote_count}, {comment_count}, {ai_analysis}, {duplicate_of}::uuid, {timeline}, {created_at}, {updated_at}, {verified_at}, {resolved_at})
ON CONFLICT (id) DO NOTHING;"""

        sql_lines.append(sql)

    sql_lines.extend(["", "COMMIT;", ""])
    return '\n'.join(sql_lines)


def transform_comments(comments_data: list) -> str:
    """Transform comments to SQL INSERT statements."""
    sql_lines = [
        "-- Comments table import",
        "BEGIN;",
        "",
    ]

    for comment in comments_data:
        comment_id = escape_sql_string(comment.get('id'))
        report_id = escape_sql_string(comment.get('report_id'))
        text = escape_sql_string(comment.get('text'))
        author = escape_sql_string(comment.get('author'))
        created_at = escape_sql_string(comment.get('created_at'))

        sql = f"""INSERT INTO comments (id, report_id, text, author, created_at)
VALUES ({comment_id}::uuid, {report_id}::uuid, {text}, {author}, {created_at})
ON CONFLICT (id) DO NOTHING;"""

        sql_lines.append(sql)

    sql_lines.extend(["", "COMMIT;", ""])
    return '\n'.join(sql_lines)


def transform_push_subscriptions(subs_data: list) -> str:
    """Transform push subscriptions to SQL INSERT statements."""
    sql_lines = [
        "-- Push subscriptions table import",
        "BEGIN;",
        "",
    ]

    for sub in subs_data:
        sub_id = escape_sql_string(sub.get('id'))
        username = escape_sql_string(sub.get('username'))
        subscription = escape_sql_string(sub.get('subscription', {}))
        created_at = escape_sql_string(sub.get('created_at'))

        sql = f"""INSERT INTO push_subscriptions (id, username, subscription, created_at)
VALUES ({sub_id}::uuid, {username}, {subscription}, {created_at})
ON CONFLICT (id) DO NOTHING;"""

        sql_lines.append(sql)

    sql_lines.extend(["", "COMMIT;", ""])
    return '\n'.join(sql_lines)


def main():
    """Main transformation function."""
    print("=" * 60)
    print("Darshi Data Transformation Tool")
    print("Firestore JSON → PostgreSQL SQL")
    print("=" * 60)
    print()

    # Load JSON data
    print("Loading Firestore exports...")

    with open(INPUT_DIR / 'users.json', 'r') as f:
        users_data = json.load(f)
    print(f"  Loaded {len(users_data)} users")

    with open(INPUT_DIR / 'reports.json', 'r') as f:
        reports_data = json.load(f)
    print(f"  Loaded {len(reports_data)} reports")

    with open(INPUT_DIR / 'comments.json', 'r') as f:
        comments_data = json.load(f)
    print(f"  Loaded {len(comments_data)} comments")

    # Load push subscriptions if exists
    push_subs_path = INPUT_DIR / 'push_subscriptions.json'
    if push_subs_path.exists():
        with open(push_subs_path, 'r') as f:
            subs_data = json.load(f)
        print(f"  Loaded {len(subs_data)} push subscriptions")
    else:
        subs_data = []
        print("  No push subscriptions found")

    print()
    print("Transforming to SQL...")

    # Transform data
    users_sql = transform_users(users_data)
    reports_sql = transform_reports(reports_data)
    comments_sql = transform_comments(comments_data)
    subs_sql = transform_push_subscriptions(subs_data) if subs_data else ""

    # Write SQL files
    print()
    print("Writing SQL files...")

    (OUTPUT_DIR / '01_users.sql').write_text(users_sql)
    print(f"  Written: 01_users.sql")

    (OUTPUT_DIR / '02_reports.sql').write_text(reports_sql)
    print(f"  Written: 02_reports.sql")

    (OUTPUT_DIR / '03_comments.sql').write_text(comments_sql)
    print(f"  Written: 03_comments.sql")

    if subs_sql:
        (OUTPUT_DIR / '04_push_subscriptions.sql').write_text(subs_sql)
        print(f"  Written: 04_push_subscriptions.sql")

    # Create master import script
    master_sql = """-- Master import script for Darshi PostgreSQL migration
-- Execute this file after creating the schema

\\set ON_ERROR_STOP on

\\echo 'Starting data import...'
\\echo ''

\\echo 'Importing users...'
\\i 01_users.sql
\\echo 'Done.'
\\echo ''

\\echo 'Importing reports...'
\\i 02_reports.sql
\\echo 'Done.'
\\echo ''

\\echo 'Importing comments...'
\\i 03_comments.sql
\\echo 'Done.'
\\echo ''
"""

    if subs_sql:
        master_sql += """\\echo 'Importing push subscriptions...'
\\i 04_push_subscriptions.sql
\\echo 'Done.'
\\echo ''
"""

    master_sql += """\\echo 'All data imported successfully!'
\\echo ''
\\echo 'Verifying counts...'
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'reports', COUNT(*) FROM reports
UNION ALL
SELECT 'comments', COUNT(*) FROM comments
UNION ALL
SELECT 'push_subscriptions', COUNT(*) FROM push_subscriptions;
"""

    (OUTPUT_DIR / '00_import_all.sql').write_text(master_sql)
    print(f"  Written: 00_import_all.sql (master script)")

    print()
    print("=" * 60)
    print("Transformation Complete!")
    print("=" * 60)
    print()
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print()
    print("To import into PostgreSQL:")
    print(f"  cd {OUTPUT_DIR.absolute()}")
    print("  psql $DATABASE_URL -f 00_import_all.sql")
    print("=" * 60)


if __name__ == '__main__':
    main()

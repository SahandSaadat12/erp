from .connection import get_connection


def check_foreign_keys():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        tables = [
            row[0]
            for row in cursor.fetchall()
        ]

        print()
        print("=" * 70)
        print("DATABASE FOREIGN KEY RELATIONSHIPS")
        print("=" * 70)

        found = False

        for table in tables:

            if table == "archive":
                continue

            cursor.execute(
                f'PRAGMA foreign_key_list("{table}")'
            )

            foreign_keys = cursor.fetchall()

            if not foreign_keys:
                continue

            found = True

            print()
            print(f"[ {table} ]")

            for foreign_key in foreign_keys:

                referenced_table = foreign_key[2]
                from_column = foreign_key[3]
                to_column = foreign_key[4]

                print(
                    f"  {table}.{from_column}"
                    f"  ->  "
                    f"{referenced_table}.{to_column}"
                )

        print()
        print("=" * 70)

        if not found:
            print("No foreign keys found.")

        print("=" * 70)
        print()

    finally:

        connection.close()


if __name__ == "__main__":
    check_foreign_keys()
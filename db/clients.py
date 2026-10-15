from .connection import get_connection


def get_clients():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            company_name
        FROM clients
        ORDER BY company_name
    """)

    clients = cursor.fetchall()

    connection.close()

    return clients
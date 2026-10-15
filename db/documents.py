from .connection import get_connection
from .permissions import require_session_permission


# ==========================================================
# Create Documents Table
# ==========================================================

def create_documents_table():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            project_id INTEGER,

            title TEXT NOT NULL,

            file_path TEXT,

            document_type TEXT,

            upload_date TEXT,

            description TEXT,

            FOREIGN KEY(project_id)
            REFERENCES projects(id)
            ON DELETE SET NULL

        )
    """)

    connection.commit()

    connection.close()



# ==========================================================
# Get All Documents
# ==========================================================

# ==========================================================
# Get Documents
# ==========================================================

def get_documents(
    keyword="",
    project="All Projects",
    document_type="All Types",
    date_start=None,
    date_end=None
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """

        SELECT

            documents.id,
            documents.title,
            projects.project_name,
            documents.document_type,
            documents.upload_date,
            documents.description

        FROM documents

        LEFT JOIN projects
            ON documents.project_id = projects.id

        WHERE 1 = 1

    """

    params = []

    # ======================================================
    # Search
    # ======================================================

    if keyword:

        query += """

            AND (

                documents.title LIKE ?

                OR documents.document_type LIKE ?

                OR projects.project_name LIKE ?

                OR documents.description LIKE ?

            )

        """

        pattern = f"%{keyword}%"

        params.extend([
            pattern,
            pattern,
            pattern,
            pattern
        ])

    # ======================================================
    # Project Filter
    # ======================================================

    if project not in (
        "All Projects",
        "Project"
    ):

        query += """

            AND projects.project_name = ?

        """

        params.append(project)

    # ======================================================
    # Type Filter
    # ======================================================

    if document_type not in (
        "All Types",
        "Type"
    ):

        query += """

            AND documents.document_type = ?

        """

        params.append(document_type)

    # ======================================================
    # Date Filter
    # ======================================================

    if date_start and date_end:

        query += """

            AND documents.upload_date >= ?
            AND documents.upload_date <= ?

        """

        params.extend([
            date_start,
            date_end
        ])

    # ======================================================
    # Order
    # ======================================================

    query += """

        ORDER BY documents.id DESC

    """

    cursor.execute(
        query,
        params
    )

    result = cursor.fetchall()

    connection.close()

    return result




# ==========================================================
# Insert Document
# ==========================================================

def insert_document(

    project_id,

    title,

    file_path,

    document_type,

    upload_date,

    description

):

    connection = get_connection()

    try:
        require_session_permission(connection, "documents.create")

        cursor = connection.cursor()


        cursor.execute("""

            INSERT INTO documents (

                project_id,

                title,

                file_path,

                document_type,

                upload_date,

                description

            )

            VALUES (?,?,?,?,?,?)

        """,

        (

            project_id,

            title,

            file_path,

            document_type,

            upload_date,

            description

        ))


        connection.commit()


        document_id = cursor.lastrowid

    finally:
        connection.close()


    return document_id




# ==========================================================
# Get Document By ID
# ==========================================================

def get_document(document_id):

    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute("""

        SELECT

            id,

            project_id,

            title,

            file_path,

            document_type,

            upload_date,

            description


        FROM documents


        WHERE id = ?

    """,

    (document_id,))


    result = cursor.fetchone()


    connection.close()


    return result




# ==========================================================
# Update Document
# ==========================================================

def update_document(

    document_id,

    project_id,

    title,

    file_path,

    document_type,

    upload_date,

    description

):

    connection = get_connection()

    try:
        require_session_permission(connection, "documents.edit")

        cursor = connection.cursor()


        cursor.execute("""

            UPDATE documents


            SET

                project_id = ?,

                title = ?,

                file_path = ?,

                document_type = ?,

                upload_date = ?,

                description = ?



            WHERE id = ?

        """,

        (

            project_id,

            title,

            file_path,

            document_type,

            upload_date,

            description,

            document_id

        ))


        connection.commit()

    finally:
        connection.close()




# ==========================================================
# Delete Document
# ==========================================================

def delete_document(document_id):

    connection = get_connection()

    try:
        require_session_permission(connection, "documents.delete")
    except Exception:
        connection.close()
        raise

    cursor = connection.cursor()


    cursor.execute("""

        DELETE FROM documents

        WHERE id = ?

    """,

    (document_id,))


    connection.commit()


    connection.close()


    return True




# ==========================================================
# Get Projects For Documents
# ==========================================================

def get_document_projects():

    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute("""

        SELECT

            id,

            project_name


        FROM projects


        ORDER BY project_name

    """)


    result = cursor.fetchall()


    connection.close()


    return result




# ==========================================================
# Get Document Types
# ==========================================================

def get_document_types():

    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute("""

        SELECT DISTINCT

            document_type


        FROM documents


        WHERE document_type IS NOT NULL

        AND document_type != ''


        ORDER BY document_type

    """)


    result = cursor.fetchall()


    connection.close()


    return result
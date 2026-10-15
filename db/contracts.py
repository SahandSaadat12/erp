from decimal import Decimal, InvalidOperation

from .connection import get_connection
from .permissions import require_session_permission


def _validated_amount(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Amount must be a valid non-negative number.")
    try:
        amount = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be a valid non-negative number.")
    if not amount.is_finite() or amount < 0:
        raise ValueError("Amount must be a finite, non-negative number.")
    return float(amount)


# ==========================================================
# Get All Contracts
# ==========================================================

def get_contracts(
    keyword="",
    project="All Projects",
    status="All"
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            contracts.id,
            contracts.contract_name,
            contracts.contract_number,
            projects.project_name,
            COALESCE(clients.company_name, '-'),
            contracts.contract_value,
            contracts.contract_date,
            contracts.status
        FROM contracts

        INNER JOIN projects
            ON contracts.project_id = projects.id

        LEFT JOIN clients
            ON projects.client_id = clients.id

        WHERE 1 = 1
    """

    params = []

    # ------------------------------------------------------
    # Search
    # ------------------------------------------------------

    if keyword:

        query += """
            AND (
                contracts.contract_name LIKE ?
                OR contracts.contract_number LIKE ?
                OR projects.project_name LIKE ?
                OR clients.company_name LIKE ?
            )
        """

        search_pattern = f"%{keyword}%"

        params.extend([
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern
        ])

    # ------------------------------------------------------
    # Project Filter
    # ------------------------------------------------------

    if project != "Project" and project != "All Projects":

        query += """
            AND projects.project_name = ?
        """

        params.append(project)

    # ------------------------------------------------------
    # Status Filter
    # ------------------------------------------------------

    if status != "Status" and status != "All":

        query += """
            AND contracts.status = ?
        """

        params.append(status)

    # ------------------------------------------------------
    # Order
    # ------------------------------------------------------

    query += """
        ORDER BY contracts.id DESC
    """

    cursor.execute(query, params)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Search Contracts
# ==========================================================

def search_contracts(
    keyword="",
    project="All Projects",
    status="All Status",
    date_start=None,
    date_end=None
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            contracts.id,
            contracts.contract_name,
            contracts.contract_number,
            projects.project_name,
            COALESCE(clients.company_name, '-'),
            contracts.contract_value,
            contracts.contract_date,
            contracts.status

        FROM contracts

        INNER JOIN projects
            ON contracts.project_id = projects.id

        LEFT JOIN clients
            ON projects.client_id = clients.id

        WHERE 1 = 1
    """

    params = []

    # ------------------------------------------------------
    # Search
    # ------------------------------------------------------

    if keyword:

        query += """
            AND (
                contracts.contract_name LIKE ?
                OR contracts.contract_number LIKE ?
                OR projects.project_name LIKE ?
                OR clients.company_name LIKE ?
                OR contracts.status LIKE ?
            )
        """

        search_pattern = f"%{keyword}%"

        params.extend([
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern
        ])

    # ------------------------------------------------------
    # Project Filter
    # ------------------------------------------------------

    if project not in ("Project", "All Projects"):

        query += """
            AND projects.project_name = ?
        """

        params.append(project)

    # ------------------------------------------------------
    # Status Filter
    # ------------------------------------------------------

    if status not in ("Status", "All", "All Status"):

        query += """
            AND contracts.status = ?
        """

        params.append(status)

    # ------------------------------------------------------
    # Date Filter
    # ------------------------------------------------------

    if date_start and date_end:

        query += """
            AND contracts.contract_date >= ?
            AND contracts.contract_date <= ?
        """

        params.extend([
            date_start,
            date_end
        ])

    # ------------------------------------------------------
    # Order
    # ------------------------------------------------------

    query += """
        ORDER BY contracts.id DESC
    """

    cursor.execute(query, params)

    result = cursor.fetchall()

    connection.close()

    return result


# ==========================================================
# Get Contract By ID
# ==========================================================

def get_contract_by_id(contract_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            project_id,
            client_id,
            contract_name,
            contract_number,
            contract_value,
            paid_amount,
            contract_date,
            payment_terms,
            status,
            description
        FROM contracts
        WHERE id = ?
    """, (contract_id,))

    contract = cursor.fetchone()

    connection.close()

    return contract


# ==========================================================
# Insert Contract
# ==========================================================

def insert_contract(
    project_id,
    client_id,
    contract_name,
    contract_number,
    contract_value,
    paid_amount,
    contract_date,
    payment_terms,
    status,
    description
):

    contract_value = _validated_amount(contract_value)
    paid_amount = _validated_amount(paid_amount)

    connection = get_connection()

    try:
        require_session_permission(connection, "contracts.create")

        cursor = connection.cursor()

        cursor.execute("""
        INSERT INTO contracts(
            project_id,
            client_id,
            contract_name,
            contract_number,
            contract_value,
            paid_amount,
            contract_date,
            payment_terms,
            status,
            description
        )
        VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            project_id,
            client_id,
            contract_name,
            contract_number,
            contract_value,
            paid_amount,
            contract_date,
            payment_terms,
            status,
            description
        ))

        connection.commit()

        contract_id = cursor.lastrowid

        return contract_id

    finally:
        connection.close()


# ==========================================================
# Update Contract
# ==========================================================

def update_contract(
    contract_id,
    project_id,
    client_id,
    contract_name,
    contract_number=None,
    contract_value=None,
    paid_amount=None,
    contract_date=None,
    payment_terms=None,
    status=None,
    description=None
):
    if contract_value is not None:
        contract_value = _validated_amount(contract_value)
    if paid_amount is not None:
        paid_amount = _validated_amount(paid_amount)

    connection = get_connection()

    try:
        require_session_permission(connection, "contracts.edit")

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE contracts

            SET
                project_id = ?,
                client_id = ?,
                contract_name = ?,
                contract_number = ?,
                contract_value = ?,
                paid_amount = ?,
                contract_date = ?,
                payment_terms = ?,
                status = ?,
                description = ?

            WHERE id = ?

        """, (
            project_id,
            client_id,
            contract_name,
            contract_number,
            contract_value,
            paid_amount,
            contract_date,
            payment_terms,
            status,
            description,
            contract_id
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================================
# Delete Contract
# ==========================================================

def delete_contract(contract_id):

    connection = get_connection()

    try:
        require_session_permission(connection, "contracts.delete")
    except Exception:
        connection.close()
        raise

    cursor = connection.cursor()

    cursor.execute("""
        DELETE
        FROM contracts

        WHERE id = ?
    """, (contract_id,))

    connection.commit()

    connection.close()

    return True


# ==========================================================
# Get Contract Projects
# ==========================================================

def get_contract_projects():

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                projects.id,
                projects.project_code,
                projects.project_name,
                COALESCE(clients.company_name, '-')

            FROM projects

            LEFT JOIN clients
                ON projects.client_id = clients.id

            ORDER BY projects.project_name
        """)

        return cursor.fetchall()

    finally:
        connection.close()


# ==========================================================
# Get Contract Statuses
# ==========================================================

def get_contract_statuses():

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT DISTINCT
                status

            FROM contracts

            WHERE status IS NOT NULL
              AND status != ''

            ORDER BY status
        """)

        return cursor.fetchall()

    finally:

        connection.close()



def get_contract(contract_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.project_id,
            c.client_id,
            c.contract_name,
            c.contract_number,
            c.contract_value,
            c.paid_amount,
            c.contract_date,
            c.payment_terms,
            c.status,
            c.description
        FROM contracts c
        WHERE c.id = ?
    """, (contract_id,))

    contract = cursor.fetchone()

    connection.close()

    return contract



"""Final database structure (generated from the real erp.db)."""
TABLES = [
    """
CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        description TEXT
    )
    """,
    """
CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        username TEXT UNIQUE COLLATE NOCASE,
        password TEXT,
        role TEXT,
        status TEXT DEFAULT 'Active'
    )
    """,
    """
CREATE TABLE IF NOT EXISTS departments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_name TEXT UNIQUE
    )
    """,
    """
CREATE TABLE IF NOT EXISTS phases(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase_name TEXT UNIQUE NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """,
    """
CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            client_id INTEGER,
            project_type TEXT,
            department_id INTEGER,
            manager_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            progress REAL DEFAULT 0,
            priority TEXT,
            current_phase_id INTEGER,
            project_status TEXT NOT NULL
                DEFAULT 'Open',
            description TEXT,
            created_at TEXT,
            updated_at TEXT,
            completion_date TEXT, expected_price REAL DEFAULT 0,
            FOREIGN KEY(client_id)
                REFERENCES clients(id)
                ON DELETE SET NULL,
            FOREIGN KEY(current_phase_id)
                REFERENCES phases(id)
                ON DELETE SET NULL,
            FOREIGN KEY(department_id)
                REFERENCES departments(id)
                ON DELETE SET NULL,
            FOREIGN KEY(manager_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        )
    """,
    """
CREATE TABLE IF NOT EXISTS contracts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        contract_name TEXT NOT NULL,
        contract_number TEXT,
        contract_value REAL,
        paid_amount REAL DEFAULT 0,
        contract_date TEXT,
        payment_terms TEXT,
        status TEXT,
        description TEXT, client_id INTEGER,
        FOREIGN KEY(project_id)
            REFERENCES projects(id)
            ON DELETE CASCADE
    )
    """,
    """
CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        title TEXT,
        file_path TEXT,
        document_type TEXT,
        upload_date TEXT,
        description TEXT,
        FOREIGN KEY(project_id)
            REFERENCES projects(id)
            ON DELETE SET NULL
    )
    """,
    """
CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT,
        category TEXT,
        amount REAL,
        expense_date TEXT,
        description TEXT, paid_by TEXT, status TEXT NOT NULL DEFAULT 'Pending', project_phase_id INTEGER,
        FOREIGN KEY(project_id)
            REFERENCES projects(id)
            ON DELETE CASCADE
    )
    """,
    """
CREATE TABLE IF NOT EXISTS project_phases(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            phase_id INTEGER NOT NULL,
            percentage REAL NOT NULL DEFAULT 0,
            progress REAL DEFAULT 0,
            status TEXT NOT NULL
                DEFAULT 'Pending',
            sort_order INTEGER, start_date TEXT, end_date TEXT, expected_price REAL DEFAULT 0,
            FOREIGN KEY(project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE,
            FOREIGN KEY(phase_id)
                REFERENCES phases(id)
                ON DELETE CASCADE,
            UNIQUE(project_id, phase_id)
        )
    """,
    """
CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT
    )
    """,
    """
CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        assigned_to TEXT,
        start_date TEXT,
        due_date TEXT,
        progress REAL DEFAULT 0,
        priority TEXT,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY(project_id)
            REFERENCES projects(id)
            ON DELETE CASCADE
    )
    """,
    """
CREATE TABLE IF NOT EXISTS roles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        is_system INTEGER DEFAULT 0
    )
    """,
    """
CREATE TABLE IF NOT EXISTS role_permissions(
        role_id INTEGER NOT NULL,
        permission TEXT NOT NULL,
        PRIMARY KEY (role_id, permission),
        FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE
    )
    """,
    """
CREATE TABLE IF NOT EXISTS session_context(
        id INTEGER PRIMARY KEY CHECK (id = 1),
        user_id INTEGER,
        username TEXT,
        failed_attempts INTEGER DEFAULT 0,
        locked_until TEXT
    )
    """,
    """
CREATE TABLE IF NOT EXISTS lookups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        value TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_system INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        UNIQUE(category, value)
    )
    """,
    """
CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now', 'localtime')),
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id INTEGER,
        label TEXT,
        old_data TEXT,
        new_data TEXT,
        performed_by_user_id INTEGER,
        performed_by_username TEXT
    )
    """,
    """
CREATE TABLE IF NOT EXISTS history_ctx(
        id INTEGER PRIMARY KEY,
        action TEXT,
        suppress INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
CREATE TABLE IF NOT EXISTS login_attempts(
        username TEXT PRIMARY KEY COLLATE NOCASE,
        failed_count INTEGER NOT NULL DEFAULT 0,
        locked_until REAL NOT NULL DEFAULT 0,
        updated_at REAL NOT NULL DEFAULT 0
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_contracts_project ON contracts(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_project ON expenses(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_phase ON expenses(project_phase_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_project_phases_project ON project_phases(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id)",
    "CREATE INDEX IF NOT EXISTS idx_history_ts ON history(ts)",
    "CREATE INDEX IF NOT EXISTS idx_lookups_category ON lookups(category)",
]

DEFAULT_PHASES = [
    "Contract & Kickoff",
    "Engineering & Drawing Approval",
    "Material Procurement",
    "Cutting",
    "Fit-up",
    "Welding",
    "NDT",
    "Surface Treatment",
    "Painting",
    "Packing",
    "Shipped",
    "Fabrication / Production",
    "Documentation & As-built",
    "Project Closeout",
]

DEFAULT_DEPARTMENTS = [
    "Engineering",
    "Production",
    "Quality Control",
    "Finance",
    "Sales",
]

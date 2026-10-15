from tkinter import ttk
from config import *



def setup_treeview():

    style = ttk.Style()

    # ===============================
    # Theme
    # ===============================

    style.theme_use("clam")

    # ===============================
    # Treeview
    # ===============================

    style.configure(

        "Treeview",

        background=TREE_BACKGROUND,
        foreground=TREE_FOREGROUND,
        fieldbackground=TREE_BACKGROUND,

        borderwidth=0,

        rowheight=TREE_ROW_HEIGHT,

        font=TREE_FONT

    )

    # ===============================
    # Selected Row
    # ===============================

    style.map(

        "Treeview",

        background=[
            ("selected", TREE_SELECTED)
        ],

        foreground=[
            ("selected", TREE_FOREGROUND)
        ]

    )

    # ===============================
    # Heading
    # ===============================

    style.configure(

        "Treeview.Heading",

        background=TREE_HEADER_BACKGROUND,

        foreground=TREE_HEADER_FOREGROUND,

        relief="flat",

        borderwidth=0,

        padding=(8,8),

        font=TREE_HEADER_FONT

    )

    style.map(

        "Treeview.Heading",

        background=[
            ("active", HEADER_ACTIVE)
        ]

    )

    # ===============================
    # Scrollbar
    # ===============================

    style.configure(

        "Vertical.TScrollbar",

        gripcount=0,

        background=CARD,

        darkcolor=CARD,

        lightcolor=CARD,

        troughcolor=BACKGROUND,

        bordercolor=BACKGROUND,

        arrowcolor=TEXT

    )

    style.configure(

        "Horizontal.TScrollbar",

        gripcount=0,

        background=CARD,

        darkcolor=CARD,

        lightcolor=CARD,

        troughcolor=BACKGROUND,

        bordercolor=BACKGROUND,

        arrowcolor=TEXT

    )
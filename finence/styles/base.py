from __future__ import annotations


def load_base_light_styles() -> str:
    return """
    QWidget {
        background: #dbeafe; /* light blue app background */
        color: #111827; /* near-black */
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", ".SF Hebrew", Arial;
    }
    QMainWindow {
        background: #dbeafe; /* match app background */
    }
    """


def load_base_dark_styles() -> str:
    return """
    QWidget {
        background: #020617;
        color: #e5e7eb;
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", ".SF Hebrew", Arial;
    }
    QMainWindow {
        background: #020617;
    }
    """

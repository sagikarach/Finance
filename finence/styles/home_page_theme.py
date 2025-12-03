from __future__ import annotations


def load_home_page_light_styles() -> str:
    """Styles specific to the home page in light mode."""
    return """
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
        letter-spacing: .2px;
        background: transparent;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #0b1220;
        padding: 6px 8px;
        background: transparent;
    }
    /* Colored stat cards */
    QWidget#StatCardGreen {
        background: #22c55e; /* green-500 */
        border: none;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #6366f1; /* indigo-500 */
        border: none;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardPurple * {
        background: transparent; /* avoid white fill from descendants */
    }
    QWidget#StatCardGreen QLabel, QWidget#StatCardPurple QLabel {
        color: #0b1220;
    }
    """


def load_home_page_dark_styles() -> str:
    """Styles specific to the home page in dark mode."""
    return """
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #e5e7eb;
        letter-spacing: .2px;
        background: transparent;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #e5e7eb;
        padding: 6px 8px;
        background: transparent;
    }
    QWidget#StatCardGreen {
        background: #16a34a;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #4f46e5;
        border-radius: 20px;
    }
    QWidget#StatCardGreen QLabel, QWidget#StatCardPurple QLabel {
        color: #e5e7eb;
    }
    """

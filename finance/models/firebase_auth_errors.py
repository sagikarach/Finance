"""Turn Firebase Auth REST error codes into Hebrew messages for the UI."""

from __future__ import annotations

_MESSAGES = {
    "EMAIL_EXISTS": "כבר קיים חשבון עם האימייל הזה. נסה להתחבר.",
    "EMAIL_NOT_FOUND": "לא נמצא חשבון עם האימייל הזה.",
    "INVALID_PASSWORD": "הסיסמה שגויה.",
    "INVALID_LOGIN_CREDENTIALS": "האימייל או הסיסמה שגויים.",
    "INVALID_EMAIL": "כתובת האימייל לא תקינה.",
    "MISSING_PASSWORD": "חובה להזין סיסמה.",
    "WEAK_PASSWORD": "הסיסמה חלשה מדי (לפחות 6 תווים).",
    "USER_DISABLED": "החשבון הזה הושבת.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "יותר מדי ניסיונות. נסה שוב בעוד כמה דקות.",
    "OPERATION_NOT_ALLOWED": "הרשמה עם אימייל וסיסמה לא מופעלת בפרויקט Firebase.",
    "PERMISSION_DENIED": "אין לחשבון הזה גישה לתקציב הזה.",
}


def auth_error_message(exc: BaseException) -> str:
    raw = str(exc or "")
    for code, msg in _MESSAGES.items():
        if code in raw:
            return msg
    if "urlopen error" in raw or "timed out" in raw or "Name or service" in raw:
        return "אין חיבור לאינטרנט. בדוק את החיבור ונסה שוב."
    return f"שגיאה: {raw}" if raw else "שגיאה לא ידועה"

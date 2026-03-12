from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

from logger import logger

CATEGORY_SCHEDULE: Final[str] = "schedule"
CATEGORY_GENERAL_INFO: Final[str] = "general_info"
CATEGORY_TECHNICAL_ISSUE: Final[str] = "technical_issue"
CATEGORY_EXAMS_AND_GRADES: Final[str] = "exams_and_grades"
CATEGORY_LIBRARY_SERVICES: Final[str] = "library_services"
CATEGORY_STUDENT_UNION_AND_DORMS: Final[str] = "student_union_and_dorms"
CATEGORY_UNKNOWN: Final[str] = "unknown"

ALL_CATEGORIES: Final[tuple[str, ...]] = (
    CATEGORY_SCHEDULE,
    CATEGORY_GENERAL_INFO,
    CATEGORY_TECHNICAL_ISSUE,
    CATEGORY_EXAMS_AND_GRADES,
    CATEGORY_LIBRARY_SERVICES,
    CATEGORY_STUDENT_UNION_AND_DORMS,
    CATEGORY_UNKNOWN,
)


_SCHEDULE_KEYWORDS: Final[list[str]] = [
    # Hebrew - exams
    "מבחן", "בחינה", "בחינות", "מבחנים",
    "מועד", "מועדים", "מועד א", "מועד ב",
    "לוח בחינות", "תאריך בחינה", "שבוע בחינות",
    # Hebrew - reception / office hours (EXCLUDING library hours)
    "שעות קבלה", "קבלת קהל", "שעות פעילות",
    "קבלה",           # root - matches הקבלה, שעות קבלה, ימי קבלה
    "מזכירות",        # root - matches המזכירות, מזכירות האוניברסיטה
    "מזכיר", "מזכירה",
    "דיקנט",
    "פגישה",
    "תור",            # appointment slot
    "לקבוע תור",
    "זמין", "זמינות",
    "מתי פתוח", "מתי סגור", "ימי קבלה",
    "קבלת קהל",
    # Hebrew - timetable / semester
    "מערכת שעות", "לוח זמנים", "סמסטר",
    # English - exams
    "exam", "exams", "examination", "test", "quiz", "final",
    "midterm", "moed", "exam schedule", "exam date",
    # English - reception / office hours (EXCLUDING library hours)
    "reception", "office hours", "opening hours",
    "appointment", "available",
    "secretary", "registrar", "dean",
    # English - timetable / schedule
    "schedule", "timetable", "semester",
    "when is", "what time", "what date",
]

_TECHNICAL_KEYWORDS: Final[list[str]] = [
    # Hebrew - login / credentials
    "סיסמה",          # root - matches הסיסמה, שכחתי סיסמה
    "סיסמא",          # alternate spelling
    "שכחתי סיסמה", "איפוס סיסמה",
    "כניסה למערכת", "לא מצליח להיכנס", "בעיית כניסה",
    "חשבון",          # root - matches החשבון, חשבוני
    "חשבון סגור", "חשבון חסום",
    "גישה",
    "אימות", "התחברות", "התנתקות",
    # Hebrew - network / hardware
    "אינטרנט",        # root - matches האינטרנט, לאינטרנט
    "רשת",
    "ווייפיי",
    "חיבור לאינטרנט", "אין אינטרנט", "נפל האינטרנט",
    "מחשב",           # root - matches המחשב, מחשבים
    "מחשבים",
    "מדפסת",          # root - matches המדפסת, מדפסות
    "הדפסה", "סורק",
    "תקלה",           # root - matches תקלה, תקלות
    "תקלה טכנית",
    # Hebrew - systems / portals
    "מערכת",          # root - matches המערכת, מערכות
    "אתר",
    "פורטל",
    "מודל", "moodle",
    "אפליקציה", "תוכנה",
    "תמיכה טכנית", "מחלקת מחשוב",
    "שגיאה",          # root - matches השגיאה, שגיאות
    "לא עובד", "לא עובדת",
    "קרסה", "קפאה", "תקוע",
    # English - login / credentials
    "password", "forgot password", "reset password",
    "login", "log in", "sign in", "can't login", "cannot login",
    "account", "account locked", "access denied", "authentication",
    "credentials", "username",
    # English - network / hardware
    "internet", "network", "wifi", "wi-fi", "connection",
    "no internet", "disconnected",
    "computer", "computers", "printer", "printing", "scanner",
    # English - systems / portals
    "system", "portal", "moodle", "website", "app", "application",
    "software", "error", "bug", "crash", "not working", "broken",
    "technical", "it support", "helpdesk", "tech support",
    "it department", "it office",
]

_GENERAL_KEYWORDS: Final[list[str]] = [
    # Hebrew - rooms
    "חדר",            # root - matches חדרים, החדר, חדר 204
    "חדרים",
    "כיתה",           # root - matches הכיתה, כיתות
    "כיתות",
    "אולם",           # root - matches האולם, אולמות
    "אולמות",
    "מעבדה",          # root - matches המעבדה, מעבדות
    "מעבדות",
    "משרד",           # root - matches המשרד, משרדים
    "משרדים",
    # Hebrew - navigation
    "קומה",           # root - matches הקומה, קומות
    "קומות",
    "בניין",          # root - matches הבניין, בניינים
    "בניינים",
    "איפה", "היכן", "מיקום", "לאן",
    "כיצד מגיעים",
    "איך מגיעים",
    "מגיעים",         # root - catches any phrasing with arriving
    "איך להגיע", "כיצד להגיע",
    "מסדרון",
    "כניסה",          # root - matches הכניסה, כניסה לקמפוס
    "יציאה",
    "מעלית",          # root - matches המעלית
    "מדרגות",
    # Hebrew - accessibility
    "נגישות", "נגיש",
    "כיסא גלגלים",
    "מוגבלות",
    # Hebrew - campus facilities
    "קפיטריה",        # root - matches הקפיטריה
    "אוכל", "מזנון",
    "ספרייה",         # root - matches הספרייה, לספרייה
    "ספריה",           # alternate spelling
    "ספרייה מרכזית",
    "חניה", "חנייה",
    "כניסה לקמפוס", "מפה",
    "שירותים", "שירותי נכים",
    # Hebrew - regex fragments (raw strings)
    r"חדר\s*\d+",
    r"כיתה\s*\w+",
    # English - rooms
    "room", "rooms", "classroom", "hall", "auditorium",
    "lab", "laboratory", "office",
    # English - navigation
    "floor", "building", "buildings",
    "where is", "where are", "how to get", "directions", "location",
    "corridor", "entrance", "exit", "elevator", "lift", "stairs",
    "how do i get", "how do i reach", "how do i find",
    # English - accessibility
    "accessible", "accessibility", "wheelchair", "disabled",
    # English - campus facilities
    "cafeteria", "canteen", "food", "library", "parking",
    "campus map", "map", "facilities",
    # English - regex fragment
    r"room\s+\w+",
]

_EXAMS_GRADES_KEYWORDS: Final[list[str]] = [
    # Hebrew - grades / appeals
    "ציון",            # root - matches הציון, ציונים, ציוני
    "ציונים",
    "ציוני",
    "ערעור",           # root - matches ערעור, ערעורים
    "ערעורים",
    "ערעור ציון",
    "טענה לציון",
    "רצוא",
    "הנמקה",
    "ציון נמוך",
    "תוצאות",          # root - matches התוצאות, תוצאות הבחינה
    "קיזוז",
    "אוטומטי",
    # Hebrew - exam policy / registration
    "מדיניות בחינה",
    "שיטת הערכה",
    "משקלים",
    "משקל",
    "תנאי עברה",
    "הצלחה",
    "כשלון",
    "שקלול",
    "ממוצע",
    "ממוצע מצטבר", "gpa",
    "ניסיון",
    "רישום לבחינה",
    "ביטול רישום",
    "הצהרת השתתפות",
    # Hebrew - publication times
    "פרסום ציונים",
    "פרסום תוצאות",
    "מתי מפרסמים",
    "תאריך פרסום",
    # English - grades / appeals
    "grade", "grades", "score", "scores", "mark", "marks",
    "appeal", "appeals", "grade appeal", "contest grade",
    "grade dispute", "grade complaint",
    "grade review", "grade change",
    "failed", "failed exam", "failure",
    "gpa", "average", "cumulative", "cumulative gpa",
    # English - exam policy / registration
    "exam policy", "grading policy", "grading scale",
    "exam registration", "register for exam",
    "exam attempt", "retake", "passing grade", "passing score",
    "weighted", "weight", "percentage",
    "course completion", "course outcome",
    # English - publication times
    "grades published", "grades posted", "when are grades published",
    "grade publication", "results publication",
]

_LIBRARY_KEYWORDS: Final[list[str]] = [
    # Hebrew - hours / access
    "ספרייה",          # root - catch all library references
    "ספרייה מרכזית",
    "שעות פתיחה ספרייה",
    "שעות ספרייה",
    "אחרי שעות",
    "גישה רחוקה",
    "גישה מרחוק",
    "וי פי אן", "vpn",
    "זיהוי",
    "סיסמה לספרייה",
    # Hebrew - collections / databases
    "ספרים",           # root - matches הספרים, ספרים
    "ספר",             # root - matches הספר
    "מאמר",            # root - matches המאמר, מאמרים
    "מאמרים",
    "כתב עת",         # journal
    "בסיס נתונים",    # database
    "מסד נתונים",
    "ieee",
    "שאילוח",         # borrowing
    "הארכה",           # extension
    "החזרה",           # return
    "עיכוב",           # overdue
    "קנס",             # fine
    # Hebrew - research / services
    "מחקר",            # root - matches מחקר, מחקרים
    "מחקרים",
    "ביבליוגרפיה",
    "הדרכה",           # instruction/tutorial
    "עזרה חיפוש",
    "הסכם גישה",
    "רישיון",          # license
    "קובץ זמין",
    # English - hours / access
    "library", "libraries", "library hours", "opening hours",
    "library access", "remote access", "off-campus access",
    "vpn", "proxy", "authentication",
    "library password", "library login",
    # English - collections / databases
    "book", "books", "article", "articles", "journal", "journals",
    "database", "databases", "ieee", "scholarly articles",
    "borrowing", "loan", "extend", "extension", "return",
    "overdue", "fine", "late fee",
    # English - research / services
    "research", "bibliography", "citation", "instruction",
    "library support", "reference librarian",
    "access agreement", "license", "licensed resources",
]

_STUDENT_SERVICES_KEYWORDS: Final[list[str]] = [
    # Hebrew - dorm / housing
    "כנס",             # dorm/dormitory (colloquial)
    "כנסיה",
    "דירה",            # apartment
    "יישוב",           # housing/accommodation
    "בקשה לדיור",     # housing application
    "דיור סטודנטים",   # student housing
    "מעון",            # dorm/residence
    "מעונות",          # dorms (plural)
    "שכן רע",          # bad roommate
    "סיוע דיור",       # housing support
    # Hebrew - union / clubs
    "איגוד סטודנטים",  # student union
    "קל״א",            # student union (abbreviation)
    "מועצה",           # council
    "קבוצה",           # group
    "קבוצות סטודנטים", # student groups
    "פעילות",          # activities
    "ארוע",            # event
    "בחירות",          # elections
    # Hebrew - financial/services
    "מלגה",            # scholarship
    "מלגות",
    "סיוע כלכלי",       # financial aid
    "עזרה כלכלית",
    "תשלום שכ״ל",      # tuition
    "עדכון זהות",
    "דרכון",
    "תעודה",           # certificate / ID
    # Hebrew - health / wellness
    "בריאות נפשית",    # mental health
    "פסיכולוג",        # psychologist
    "יעוץ",            # counseling
    "עזרה נפשית",
    "קלינאי",          # clinician
    "רופא",            # doctor
    "בריאות",          # health
    "חרדה",            # anxiety
    "דיכאון",          # depression
    "משברים",         # crisis
    # Hebrew - student day / tickets
    "כרטיס סטודנט",    # student ticket / card
    "כרטיסים",
    "הנחה סטודנט",     # student discount
    "הנחה",            # discount
    "תחבורה",          # transportation
    # English - dorm / housing
    "dorm", "dormitory", "dorms", "residence", "residence hall",
    "housing", "student housing", "on-campus housing", "accommodation",
    "roommate", "housing application", "housing request",
    # English - union / clubs
    "student union", "student council", "student organization",
    "student club", "clubs", "group", "organizations",
    "activities", "events", "student activities", "elections",
    # English - financial / services
    "scholarship", "scholarships", "financial aid", "financial support",
    "tuition", "fees", "payment", "billing",
    "identity", "student id", "documentation",
    # English - health / wellness
    "mental health", "psychological", "counseling", "counselor",
    "wellness", "health services", "health center",
    "stress", "anxiety", "depression", "crisis", "support",
    # English - student day / tickets
    "student ticket", "student discount", "transportation",
    "student day", "discounts",
]


# Detects whether a string already contains regex metacharacters
_META_RE: re.Pattern[str] = re.compile(r'[\\[\]()*+?{}^$|]')


def _build_pattern(keywords: list[str]) -> re.Pattern[str]:
    """
    Build a single compiled OR-pattern from a list of keyword strings.

    Strategy per keyword type:
      1. Raw regex fragment (contains metacharacters)
         -> used as-is without modification.
      2. Pure ASCII word / phrase
         -> wrapped with word-boundary anchors for precision.
      3. Hebrew / mixed-script string
         -> plain re.escape() substring match (no boundaries).
         Hebrew prefixes attach directly to roots without spaces,
         so boundary anchors produce false negatives.
         Example: '\u05e1\u05d9\u05e1\u05de\u05d4' must match inside '\u05d4\u05e1\u05d9\u05e1\u05de\u05d4'.
    """
    parts: list[str] = []
    for kw in keywords:
        if _META_RE.search(kw):
            parts.append(kw)
        elif kw.isascii():
            parts.append(r'\b' + re.escape(kw) + r'\b')
        else:
            parts.append(re.escape(kw))
    return re.compile('|'.join(parts), re.IGNORECASE | re.UNICODE)


_PATTERN_SCHEDULES: re.Pattern[str] = _build_pattern(_SCHEDULE_KEYWORDS)
_PATTERN_TECHNICAL: re.Pattern[str] = _build_pattern(_TECHNICAL_KEYWORDS)
_PATTERN_GENERAL:   re.Pattern[str] = _build_pattern(_GENERAL_KEYWORDS)
_PATTERN_EXAMS_GRADES: re.Pattern[str] = _build_pattern(_EXAMS_GRADES_KEYWORDS)
_PATTERN_LIBRARY: re.Pattern[str] = _build_pattern(_LIBRARY_KEYWORDS)
_PATTERN_STUDENT_SERVICES: re.Pattern[str] = _build_pattern(_STUDENT_SERVICES_KEYWORDS)

_HEBREW_CHAR_RE: re.Pattern[str] = re.compile(r'[\u0590-\u05FF]')


def detect_language(text: str) -> str:
    """Return 'he' if text contains Hebrew characters, else 'en'."""
    return "he" if _HEBREW_CHAR_RE.search(text) else "en"


@dataclass(frozen=True)
class FallbackMessages:
    """Bilingual polite refusal templates for out-of-scope questions."""

    hebrew: str = field(default=(
        "מצטער/ת, השאלה שלך חורגת מהנושאים שאני יכול/ה לסייע בהם.\n"
        "אני מטפל/ת בנושאים הבאים בלבד:\n"
        "  • לוח בחינות ושעות קבלה\n"
        "  • מיקום חדרים ונווט בקמפוס\n"
        "  • ציונים וערעורים\n"
        "  • שירותי ספרייה\n"
        "  • דיור סטודנטים ופעילויות איגוד\n"
        "  • תמיכה טכנית ובעיות מערכת\n\n"
        "לשאלות אחרות, אנא פנה/י ישירות למזכירות האוניברסיטה:\n"
        "  📞 03-6789001\n"
        "  ✉️  registrar@campus.ac.il"
    ))

    english: str = field(default=(
        "I'm sorry, your question is outside the topics I can help with.\n"
        "I only handle the following:\n"
        "  • Exam schedules and reception hours\n"
        "  • Room locations and campus navigation\n"
        "  • Exam grades and appeals\n"
        "  • Library services and research support\n"
        "  • Student housing and union activities\n"
        "  • Technical support and system issues\n\n"
        "For other inquiries, please contact the University Registrar directly:\n"
        "  📞 03-6789001\n"
        "  ✉️  registrar@campus.ac.il"
    ))


_FALLBACK = FallbackMessages()


def get_fallback_message(question: str) -> str:
    """Return polite refusal in the user's detected language."""
    return _FALLBACK.hebrew if detect_language(question) == "he" else _FALLBACK.english


def classify_question(question: str) -> str:
    """
    Classify a user question into one of seven category strings.

    Detection order (first match wins):
        1. schedule            - exam dates & reception hours
        2. exams_and_grades    - grades, appeals, exam policy
        3. library_services    - library hours, databases, borrowing
        4. student_union_and_dorms - housing, student clubs, union services
        5. technical_issue     - IT / login / system keywords
        6. general_info        - room / navigation / facilities keywords
        7. unknown             - no keywords matched

    Args:
        question: Raw user input string (Hebrew, English, or mixed).

    Returns:
        One of: 'schedule', 'exams_and_grades', 'library_services',
                'student_union_and_dorms', 'technical_issue', 'general_info', 'unknown'
    """
    if not question or not question.strip():
        logger.debug("classify_question: empty input -> unknown")
        return CATEGORY_UNKNOWN

    q = question.strip()
    logger.debug("classify_question: input=%r", q[:120])

    if _PATTERN_SCHEDULES.search(q):
        logger.debug("classify_question: matched SCHEDULE")
        return CATEGORY_SCHEDULE

    if _PATTERN_EXAMS_GRADES.search(q):
        logger.debug("classify_question: matched EXAMS_AND_GRADES")
        return CATEGORY_EXAMS_AND_GRADES

    if _PATTERN_LIBRARY.search(q):
        logger.debug("classify_question: matched LIBRARY_SERVICES")
        return CATEGORY_LIBRARY_SERVICES

    if _PATTERN_STUDENT_SERVICES.search(q):
        logger.debug("classify_question: matched STUDENT_UNION_AND_DORMS")
        return CATEGORY_STUDENT_UNION_AND_DORMS

    if _PATTERN_TECHNICAL.search(q):
        logger.debug("classify_question: matched TECHNICAL_ISSUE")
        return CATEGORY_TECHNICAL_ISSUE

    if _PATTERN_GENERAL.search(q):
        logger.debug("classify_question: matched GENERAL_INFO")
        return CATEGORY_GENERAL_INFO

    logger.debug("classify_question: no match -> unknown")
    return CATEGORY_UNKNOWN


@dataclass
class ClassificationResult:
    """
    Bundles category + optional fallback text for routers.py.

    Usage:
        result = classify(question)
        if result.is_unknown:
            return {"answer": result.fallback_message, "category": result.category}
    """
    category: str
    fallback_message: str | None = None

    @property
    def is_unknown(self) -> bool:
        return self.category == CATEGORY_UNKNOWN


def classify(question: str) -> ClassificationResult:
    """
    High-level entry point for routers.py.

    Returns ClassificationResult with:
      - .category         always set
      - .fallback_message set only when category == unknown
      - .is_unknown       True when the router should skip the LLM
    """
    category = classify_question(question)
    fallback = get_fallback_message(question) if category == CATEGORY_UNKNOWN else None
    return ClassificationResult(category=category, fallback_message=fallback)



if __name__ == "__main__":
    _TEST_CASES: list[tuple[str, str]] = [
        # Schedule - Hebrew
        ("מתי מועד א של מבחן CS101?",                   CATEGORY_SCHEDULE),
        ("מה שעות הקבלה של המזכירות?",  CATEGORY_SCHEDULE),
        ("מתי יש בחינות בסמסטר הקרוב?",  CATEGORY_SCHEDULE),
        ("האם יש לי תור לדיקנט?",       CATEGORY_SCHEDULE),
        # Schedule - English
        ("When is the CS201 exam?",                        CATEGORY_SCHEDULE),
        ("What are the reception hours for the registrar?", CATEGORY_SCHEDULE),
        ("What time does the office open?",                CATEGORY_SCHEDULE),
        # Technical_Issue - Hebrew
        ("שכחתי את הסיסמה שלי למערכת",   CATEGORY_TECHNICAL_ISSUE),
        ("אני לא מצליח להתחבר ל-Moodle",  CATEGORY_TECHNICAL_ISSUE),
        ("אין לי אינטרנט בקמפוס",    CATEGORY_TECHNICAL_ISSUE),
        ("המדפסת לא עובדת",                CATEGORY_TECHNICAL_ISSUE),
        # Technical_Issue - English
        ("I forgot my password",                           CATEGORY_TECHNICAL_ISSUE),
        ("Can't login to the student portal",              CATEGORY_TECHNICAL_ISSUE),
        ("The Wi-Fi is not working in building A",         CATEGORY_TECHNICAL_ISSUE),
        ("My account is locked",                           CATEGORY_TECHNICAL_ISSUE),
        # General_Info - Hebrew
        ("איפה חדר 204 בבניין הנדסה?",   CATEGORY_GENERAL_INFO),
        ("איך מגיעים לספרייה המרכזית?", CATEGORY_GENERAL_INFO),
        ("האם הבניין נגיש לכיסאות גלגלים?", CATEGORY_GENERAL_INFO),
        ("היכן הקפיטריה?",               CATEGORY_GENERAL_INFO),
        # General_Info - English
        ("Where is room 101?",                             CATEGORY_GENERAL_INFO),
        ("How do I get to the library?",                   CATEGORY_GENERAL_INFO),
        ("Is the auditorium on floor 1?",                  CATEGORY_GENERAL_INFO),
        ("Where can I find parking?",                      CATEGORY_GENERAL_INFO),
        # Unknown
        ("What is the meaning of life?",                   CATEGORY_UNKNOWN),
        ("מי יזכה בגביע העולם?",   CATEGORY_UNKNOWN),
        ("Tell me a joke",                                 CATEGORY_UNKNOWN),
        ("",                                               CATEGORY_UNKNOWN),
    ]

    print("\n" + "=" * 72)
    print("  classifier.py - self-test")
    print("=" * 72)

    passed = failed = 0
    for question, expected in _TEST_CASES:
        result  = classify(question)
        ok      = result.category == expected
        status  = "V" if ok else "X"
        passed += int(ok)
        failed += int(not ok)
        label   = repr(question[:54]) if question else repr("")
        print(f"  {status}  {label:<56} -> {result.category:<12} (expected {expected})")

    print("=" * 72)
    print(f"  Results: {passed} passed, {failed} failed out of {len(_TEST_CASES)} cases")
    print("=" * 72)

    print("\n--- Hebrew fallback ---")
    print(get_fallback_message("שאלה לא רלוונטית"))
    print("\n--- English fallback ---")
    print(get_fallback_message("What is the weather?"))
    print()

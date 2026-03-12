"""
seed.py
-------
Data seeding script for the Smart Campus Assistant.

Responsibilities:
  - Populates ExamSchedule, ReceptionHours, and RoomLocation tables
    with realistic mock campus data (bilingual: Hebrew names, English structure)
  - Uses INSERT OR IGNORE semantics via UniqueConstraints so the script is
    fully idempotent — safe to run multiple times without duplicating rows
  - Exposes fetch functions that the AI pipeline (Task 3.7) will call to
    inject live DB context into the prompt

Run directly:
    python seed.py

Fetch functions are importable:
    from seed import fetch_all_exams, fetch_reception_hours, fetch_room_locations
"""

from __future__ import annotations

import sys
from typing import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import (
    ExamSchedule,
    ReceptionHours,
    RoomLocation,
    ExamsGradesInfo,
    LibraryServicesInfo,
    StudentServicesInfo,
    SessionLocal,
    init_db,
)
from logger import logger


# ===========================================================================
# SECTION 1 — MOCK DATA
# ===========================================================================

# ---------------------------------------------------------------------------
# 1a. Exam Schedules
# ---------------------------------------------------------------------------
EXAM_SCHEDULES: list[dict] = [
    {
        "course_code": "CS101",
        "course_name": "מבוא למדעי המחשב",          # Introduction to Computer Science
        "exam_date": "2025-02-03",
        "start_time": "09:00",
        "end_time": "12:00",
        "building": "בניין הנדסה א׳",                # Engineering Building A
        "room_number": "101",
        "lecturer": "ד״ר יוסי כהן",                  # Dr. Yossi Cohen
        "notes": "מותר להכניס מחשבון מדעי",           # Scientific calculator permitted
    },
    {
        "course_code": "CS201",
        "course_name": "מבני נתונים ואלגוריתמים",    # Data Structures & Algorithms
        "exam_date": "2025-02-05",
        "start_time": "10:00",
        "end_time": "13:00",
        "building": "בניין הנדסה א׳",
        "room_number": "204",
        "lecturer": "פרופ׳ רחל לוי",                 # Prof. Rachel Levy
        "notes": None,
    },
    {
        "course_code": "MATH101",
        "course_name": "חשבון דיפרנציאלי ואינטגרלי",  # Calculus I
        "exam_date": "2025-02-06",
        "start_time": "08:30",
        "end_time": "11:30",
        "building": "בניין מדעים",                   # Science Building
        "room_number": "A10",
        "lecturer": "ד״ר אמיר שפירו",
        "notes": "טבלאות אינטגרלים מותרות",           # Integral tables permitted
    },
    {
        "course_code": "MATH201",
        "course_name": "אלגברה לינארית",              # Linear Algebra
        "exam_date": "2025-02-10",
        "start_time": "09:00",
        "end_time": "12:00",
        "building": "בניין מדעים",
        "room_number": "B20",
        "lecturer": "פרופ׳ נועה ברק",
        "notes": None,
    },
    {
        "course_code": "ENG110",
        "course_name": "אנגלית אקדמית",               # Academic English
        "exam_date": "2025-02-12",
        "start_time": "11:00",
        "end_time": "13:00",
        "building": "בניין מדעי הרוח",               # Humanities Building
        "room_number": "305",
        "lecturer": "גב׳ סרה גרין",
        "notes": "מילון אנגלי-עברי מותר",             # English-Hebrew dictionary permitted
    },
    {
        "course_code": "PHY101",
        "course_name": "פיזיקה א׳",                   # Physics I
        "exam_date": "2025-02-14",
        "start_time": "08:00",
        "end_time": "11:00",
        "building": "בניין הנדסה ב׳",                # Engineering Building B
        "room_number": "102",
        "lecturer": "ד״ר דן אביב",
        "notes": "דף נוסחאות מותר",                   # Formula sheet permitted
    },
    {
        "course_code": "CS301",
        "course_name": "מערכות הפעלה",                # Operating Systems
        "exam_date": "2025-02-17",
        "start_time": "14:00",
        "end_time": "17:00",
        "building": "בניין הנדסה א׳",
        "room_number": "301",
        "lecturer": "פרופ׳ עמי זהבי",
        "notes": None,
    },
    {
        "course_code": "STAT201",
        "course_name": "סטטיסטיקה והסתברות",          # Statistics & Probability
        "exam_date": "2025-02-19",
        "start_time": "10:00",
        "end_time": "13:00",
        "building": "בניין מדעים",
        "room_number": "C15",
        "lecturer": "ד״ר מיכל דוד",
        "notes": "מחשבון מדעי מותר",
    },
]


# ---------------------------------------------------------------------------
# 1b. Reception Hours
# ---------------------------------------------------------------------------
RECEPTION_HOURS: list[dict] = [
    # --- Registrar (מזכירות) ---
    {
        "department": "מזכירות האוניברסיטה",           # University Registrar
        "contact_person": "גב׳ חנה מור",
        "room_number": "101",
        "phone": "03-6789001",
        "email": "registrar@campus.ac.il",
        "day_of_week": "Sunday",
        "open_time": "08:30",
        "close_time": "13:00",
        "is_by_appointment": False,
        "notes": "קבלת קהל בימים א׳–ה׳",              # Walk-in Sun–Thu
    },
    {
        "department": "מזכירות האוניברסיטה",
        "contact_person": "גב׳ חנה מור",
        "room_number": "101",
        "phone": "03-6789001",
        "email": "registrar@campus.ac.il",
        "day_of_week": "Monday",
        "open_time": "08:30",
        "close_time": "13:00",
        "is_by_appointment": False,
        "notes": None,
    },
    {
        "department": "מזכירות האוניברסיטה",
        "contact_person": "גב׳ חנה מור",
        "room_number": "101",
        "phone": "03-6789001",
        "email": "registrar@campus.ac.il",
        "day_of_week": "Wednesday",
        "open_time": "12:00",
        "close_time": "16:00",
        "is_by_appointment": False,
        "notes": "שעות צהריים",                        # Afternoon hours
    },
    # --- Financial Aid (מלגות) ---
    {
        "department": "מדור מלגות",                    # Scholarships Office
        "contact_person": "מר אבי לב",
        "room_number": "210",
        "phone": "03-6789050",
        "email": "scholarships@campus.ac.il",
        "day_of_week": "Tuesday",
        "open_time": "09:00",
        "close_time": "14:00",
        "is_by_appointment": True,
        "notes": "יש לקבוע תור מראש באתר",             # Appointment required via website
    },
    {
        "department": "מדור מלגות",
        "contact_person": "מר אבי לב",
        "room_number": "210",
        "phone": "03-6789050",
        "email": "scholarships@campus.ac.il",
        "day_of_week": "Thursday",
        "open_time": "09:00",
        "close_time": "14:00",
        "is_by_appointment": True,
        "notes": None,
    },
    # --- IT Help Desk (תמיכה טכנית) ---
    {
        "department": "מדור תקשוב ומחשוב",             # IT Department
        "contact_person": "טל שרון",
        "room_number": "B05",
        "phone": "03-6789100",
        "email": "it-support@campus.ac.il",
        "day_of_week": "Sunday",
        "open_time": "08:00",
        "close_time": "17:00",
        "is_by_appointment": False,
        "notes": "תמיכה בסיסמאות, מערכת הרשמה ורשת",  # Passwords, registration & network
    },
    {
        "department": "מדור תקשוב ומחשוב",
        "contact_person": "טל שרון",
        "room_number": "B05",
        "phone": "03-6789100",
        "email": "it-support@campus.ac.il",
        "day_of_week": "Tuesday",
        "open_time": "08:00",
        "close_time": "17:00",
        "is_by_appointment": False,
        "notes": None,
    },
    {
        "department": "מדור תקשוב ומחשוב",
        "contact_person": "טל שרון",
        "room_number": "B05",
        "phone": "03-6789100",
        "email": "it-support@campus.ac.il",
        "day_of_week": "Thursday",
        "open_time": "08:00",
        "close_time": "17:00",
        "is_by_appointment": False,
        "notes": None,
    },
    # --- Student Affairs (סטודנטים) ---
    {
        "department": "דיקנט הסטודנטים",              # Dean of Students
        "contact_person": "ד״ר יעל פרץ",
        "room_number": "120",
        "phone": "03-6789200",
        "email": "dean-students@campus.ac.il",
        "day_of_week": "Monday",
        "open_time": "10:00",
        "close_time": "14:00",
        "is_by_appointment": True,
        "notes": "ייעוץ אישי בתיאום מראש",            # Personal counselling by appointment
    },
    {
        "department": "דיקנט הסטודנטים",
        "contact_person": "ד״ר יעל פרץ",
        "room_number": "120",
        "phone": "03-6789200",
        "email": "dean-students@campus.ac.il",
        "day_of_week": "Wednesday",
        "open_time": "10:00",
        "close_time": "14:00",
        "is_by_appointment": True,
        "notes": None,
    },
    # --- Library (ספרייה) ---
    {
        "department": "הספרייה המרכזית",               # Central Library
        "contact_person": "גב׳ רות בן-דוד",
        "room_number": "ספרייה מרכזית",
        "phone": "03-6789300",
        "email": "library@campus.ac.il",
        "day_of_week": "Sunday",
        "open_time": "08:00",
        "close_time": "21:00",
        "is_by_appointment": False,
        "notes": "פתוח גם בימי שישי 08:00–14:00",
    },
    {
        "department": "הספרייה המרכזית",
        "contact_person": "גב׳ רות בן-דוד",
        "room_number": "ספרייה מרכזית",
        "phone": "03-6789300",
        "email": "library@campus.ac.il",
        "day_of_week": "Monday",
        "open_time": "08:00",
        "close_time": "21:00",
        "is_by_appointment": False,
        "notes": None,
    },
]


# ---------------------------------------------------------------------------
# 1c. Room Locations
# ---------------------------------------------------------------------------
ROOM_LOCATIONS: list[dict] = [
    # --- Engineering Building A (בניין הנדסה א׳) ---
    {
        "building": "בניין הנדסה א׳",
        "room_number": "101",
        "room_name": "אולם בחינות גדול",              # Large Exam Hall
        "room_type": "auditorium",
        "floor": 1,
        "capacity": 200,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "כניסה ראשית, פנה שמאלה, חדר ראשון מימין",
        "notes": "מצויד במקרן ומיקרופון",
    },
    {
        "building": "בניין הנדסה א׳",
        "room_number": "204",
        "room_name": "חדר בחינות 204",
        "room_type": "classroom",
        "floor": 2,
        "capacity": 80,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "עלה לקומה 2 במעלית, פנה ימינה",
        "notes": None,
    },
    {
        "building": "בניין הנדסה א׳",
        "room_number": "301",
        "room_name": "מעבדת מחשבים 301",              # Computer Lab 301
        "room_type": "lab",
        "floor": 3,
        "capacity": 40,
        "is_accessible": False,
        "has_elevator_access": True,
        "directions": "קומה 3, מסדרון ראשי, דלת בסוף המסדרון",
        "notes": "30 תחנות עבודה, מדפסת לייזר זמינה",
    },
    # --- Engineering Building B (בניין הנדסה ב׳) ---
    {
        "building": "בניין הנדסה ב׳",
        "room_number": "102",
        "room_name": "אולם הרצאות 102",
        "room_type": "auditorium",
        "floor": 1,
        "capacity": 150,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "כניסה מרחוב הגפן, קומת קרקע",
        "notes": None,
    },
    # --- Science Building (בניין מדעים) ---
    {
        "building": "בניין מדעים",
        "room_number": "A10",
        "room_name": "אולם מדעים A",
        "room_type": "auditorium",
        "floor": 0,
        "capacity": 120,
        "is_accessible": True,
        "has_elevator_access": False,
        "directions": "קומת קרקע, כניסה מזרחית",
        "notes": "נגיש לכיסאות גלגלים מהכניסה הצדדית",
    },
    {
        "building": "בניין מדעים",
        "room_number": "B20",
        "room_name": "חדר סמינרים B20",
        "room_type": "classroom",
        "floor": 2,
        "capacity": 50,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "קומה 2, צד ימין של המסדרון",
        "notes": None,
    },
    {
        "building": "בניין מדעים",
        "room_number": "C15",
        "room_name": "כיתה C15",
        "room_type": "classroom",
        "floor": 1,
        "capacity": 60,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "קומה 1, ממול למדרגות",
        "notes": None,
    },
    # --- Humanities Building (בניין מדעי הרוח) ---
    {
        "building": "בניין מדעי הרוח",
        "room_number": "305",
        "room_name": "כיתת שפות 305",                # Language Classroom 305
        "room_type": "classroom",
        "floor": 3,
        "capacity": 35,
        "is_accessible": False,
        "has_elevator_access": False,
        "directions": "קומה 3, המדרגות המרכזיות בלבד",
        "notes": "אין מעלית בבניין זה",               # No elevator in this building
    },
    # --- Administration Building (בניין המינהל) ---
    {
        "building": "בניין המינהל",
        "room_number": "101",
        "room_name": "מזכירות האוניברסיטה",
        "room_type": "office",
        "floor": 1,
        "capacity": None,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "כניסה ראשית, ישר קדימה",
        "notes": None,
    },
    {
        "building": "בניין המינהל",
        "room_number": "120",
        "room_name": "דיקנט הסטודנטים",
        "room_type": "office",
        "floor": 1,
        "capacity": None,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "כניסה ראשית, פנה שמאלה, חדר 120",
        "notes": None,
    },
    {
        "building": "בניין המינהל",
        "room_number": "210",
        "room_name": "מדור מלגות",
        "room_type": "office",
        "floor": 2,
        "capacity": None,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "קומה 2 במעלית, פנה ימינה",
        "notes": None,
    },
    {
        "building": "בניין המינהל",
        "room_number": "B05",
        "room_name": "מדור תקשוב",                    # IT Department
        "room_type": "office",
        "floor": 0,
        "capacity": None,
        "is_accessible": True,
        "has_elevator_access": False,
        "directions": "מרתף, פנה ימינה מהמדרגות",
        "notes": "Help Desk — תמיכה טכנית לסטודנטים",
    },
    # --- Central Library (ספרייה מרכזית) ---
    {
        "building": "ספרייה מרכזית",
        "room_number": "ספרייה מרכזית",
        "room_name": "ספרייה מרכזית",
        "room_type": "library",
        "floor": 0,
        "capacity": 300,
        "is_accessible": True,
        "has_elevator_access": True,
        "directions": "בניין עצמאי במרכז הקמפוס, ממול לקפיטריה",
        "notes": "Wi-Fi, עמדות הדפסה, חדרי לימוד קבוצתיים",
    },
    # --- Cafeteria (קפיטריה) ---
    {
        "building": "בניין סטודנטים",
        "room_number": "קפיטריה",
        "room_name": "קפיטריה מרכזית",
        "room_type": "cafeteria",
        "floor": 0,
        "capacity": 250,
        "is_accessible": True,
        "has_elevator_access": False,
        "directions": "קומת קרקע, ממול לספרייה המרכזית",
        "notes": "פתוח א׳–ה׳ 07:30–19:00, שישי 07:30–14:00",
    },
]


# ---------------------------------------------------------------------------
# 1d. Exams & Grades Information (5 entries)
# ---------------------------------------------------------------------------

EXAMS_GRADES_DATA: list[dict] = [
    {
        "question": "איך מערערים על ציון בבחינה?",
        "answer": "ערעור על ציון יש להגיש תוך 14 ימים מפרסום התוצאות. יש למלא טופס ערעור בדיקנט ולצרף הסבר מפורט. בדרך כלל התשובה תשמע תוך שבועות.",
        "topic": "appeals",
    },
    {
        "question": "מתי מפרסמים את ציוני הבחינות?",
        "answer": "ציונים מפורסמים בדרך כלל תוך שבועות אחדים מסיום תקופת בחינות. ניתן לבדוק בפורטל סטודנטים. מרצים אתם מודיעים בדוא״ל כשהציונים זמינים.",
        "topic": "publication",
    },
    {
        "question": "מה ציון עברה בקורס?",
        "answer": "הציון המינימום לעברה קורס הוא 55 נקודות. בחלק מהקורסים בודקים גם ציון מינימום בבחינה. בדוק בסילבוס של הקורס.",
        "topic": "policy",
    },
    {
        "question": "איך מחושב הממוצע המצטבר שלי?",
        "answer": "הממוצע המצטבר מחושב כממוצע משוקלל של כל הציונים שקיבלת, מושקלל לפי יחידות הקורס (נקודות זכות). קורסים שלא עברת לא נכללים בחישוב.",
        "topic": "cumulative",
    },
    {
        "question": "האם אוכל לגשת לבחינה פעם שנייה?",
        "answer": "כן, ניתן להבחן בניסיון נוסף. הציון החדש מחליף את הישן (אפילו אם נמוך יותר). בבקשה בדוק עם הדיקנט לגבי מועדים זמינים.",
        "topic": "registration",
    },
]

# ---------------------------------------------------------------------------
# 1e. Library Services Information (5 entries)
# ---------------------------------------------------------------------------

LIBRARY_SERVICES_DATA: list[dict] = [
    {
        "question": "מה שעות הפתיחה של הספרייה המרכזית?",
        "answer": "הספרייה פתוחה ימים א׳–ה׳ 08:00–20:00, יום שישי 08:00–14:00, סגורה בשבת. בזמן בחינות השעות ייתכן שיוארכו.",
        "topic": "hours",
    },
    {
        "question": "איך אני קולח ספר מהספרייה?",
        "answer": "ניתן לקלוח ספר עד 3 שבועות. הקלוח מתבצע בדלפק הספרייה עם תעודת הזיהוי של הסטודנט. ניתן לארך קלוח פעם אחת עד 2 שבועות נוספות.",
        "topic": "borrowing",
    },
    {
        "question": "איך אני ניגש לבסיסי נתונים מרחוק (מהבית)?",
        "answer": "יש להתחבר דרך VPN של האוניברסיטה. הוראות התחברות ב-vpn מופצות בדף הספרייה. צור קשר עם מדור תקשוב אם יש בעיות בחיבור.",
        "topic": "access",
    },
    {
        "question": "האם גישה לבסיסי נתונים כמו IEEE זמינה?",
        "answer": "כן! הספרייה מנויה לבסיסי נתונים חשובים כ-IEEE Xplore, JSTOR, ועוד. ניתן לאתר דרך אתר הספרייה. גישה זמינה למחוברים לרשת האוניברסיטה.",
        "topic": "databases",
    },
    {
        "question": "מה הקנס על ספר שלא חזר בזמן?",
        "answer": "הקנס הוא 5 שקלים ליום לכל ספר. אם הספר לא יוחזר תוך 30 ימים, עלות הספר תחויב לחשבון הסטודנט.",
        "topic": "borrowing",
    },
]

# ---------------------------------------------------------------------------
# 1f. Student Services Information (5 entries)
# ---------------------------------------------------------------------------

STUDENT_SERVICES_DATA: list[dict] = [
    {
        "question": "איך אני מגיש בקשה למעון סטודנטים?",
        "answer": "בקשות לדיור פתוחות כל שנה בחודשי מאי-יוני. נתונים מגישים דרך הפורטל של משרד הסטודנטים. עדיפות ניתנת לסטודנטים שנתם הראשונה וצרכים חברתיים-כלכליים.",
        "topic": "housing",
    },
    {
        "question": "מה שירותי הבריאות הנפשית בקמפוס?",
        "answer": "הקמפוס מפעיל קלינאי בריאות נפשית והפניות לפסיכולוגים. הייעוץ חינם לסטודנטים. התור למשהו חדש לוקח בדרך כלל שבוע. בשעות משברים, ניתן לתקוע למדור מקום בחירום.",
        "topic": "wellness",
    },
    {
        "question": "איך אני משיג מלגה או סיוע כלכלי?",
        "answer": "בקשה למלגה מוגשת דרך משרד הסטודנטים. המלגות מתבססות על הישגים אקדמיים וצרכים כלכליים. התרקום מתבצע פעמיים בשנה.",
        "topic": "financial",
    },
    {
        "question": "מה האלות לתלמיד בחברת סטודנטים?",
        "answer": "קל״א (איגוד הסטודנטים) מארגן פעילויות שבוע סטודנטים, טורנירים, וערכות חברתיות. ניתן להצטרף לקבוצות ענין שונות. ועד הנבחרים נבחר בהצבעה שנתית.",
        "topic": "union",
    },
    {
        "question": "איך אני מקבל כרטיס סטודנט להנחות?",
        "answer": "כרטיס הסטודנט מונפק בתחילת השנה במשרד הסטודנטים עם תעודת הזיהוי. הכרטיס זכאי להנחות בתחבורה ציבורית, בתרבות, ובמוסדות שונים.",
        "topic": "student_day",
    },
]

# ===========================================================================
# SECTION 2 — SEEDING FUNCTIONS
# ===========================================================================

def _seed_table(db: Session, model, records: list[dict], table_label: str) -> int:
    """
    Generic helper that inserts records and silently skips duplicates.

    Returns the number of rows actually inserted (not skipped).
    """
    inserted = 0
    for record in records:
        obj = model(**record)
        db.add(obj)
        try:
            db.flush()          # hit the DB immediately to catch UniqueConstraint
            inserted += 1
        except IntegrityError:
            db.rollback()       # roll back only this row; keep session alive
            logger.debug("Skipped duplicate %s: %r", table_label, record)
        else:
            db.commit()

    return inserted


def seed_all(db: Session | None = None) -> dict[str, int]:
    """
    Populate all three tables with mock campus data.

    Accepts an optional Session; creates its own if none is provided,
    so the function works both as a standalone script and as a test helper.

    Returns a summary dict: { "exams": N, "reception": N, "rooms": N }
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()

    try:
        logger.info("Starting database seed…")

        exams_n       = _seed_table(db, ExamSchedule,        EXAM_SCHEDULES,        "ExamSchedule")
        recept_n      = _seed_table(db, ReceptionHours,      RECEPTION_HOURS,       "ReceptionHours")
        rooms_n       = _seed_table(db, RoomLocation,        ROOM_LOCATIONS,        "RoomLocation")
        grades_n      = _seed_table(db, ExamsGradesInfo,     EXAMS_GRADES_DATA,     "ExamsGradesInfo")
        library_n     = _seed_table(db, LibraryServicesInfo, LIBRARY_SERVICES_DATA, "LibraryServicesInfo")
        services_n    = _seed_table(db, StudentServicesInfo, STUDENT_SERVICES_DATA, "StudentServicesInfo")

        summary = {
            "exams": exams_n,
            "reception": recept_n,
            "rooms": rooms_n,
            "exams_grades": grades_n,
            "library_services": library_n,
            "student_services": services_n,
        }
        logger.info("Seed complete — %s", summary)
        return summary

    finally:
        if close_after:
            db.close()


# ===========================================================================
# SECTION 3 — FETCH FUNCTIONS
# ===========================================================================

def fetch_all_exams(db: Session | None = None) -> list[ExamSchedule]:
    """
    Return every exam row ordered by date then start time.
    Used by the AI prompt builder (Task 3.5) to inject current exam data.
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        return (
            db.query(ExamSchedule)
            .order_by(ExamSchedule.exam_date, ExamSchedule.start_time)
            .all()
        )
    finally:
        if close_after:
            db.close()


def fetch_exams_by_course(course_code: str, db: Session | None = None) -> list[ExamSchedule]:
    """Return exams filtered by course code (case-insensitive)."""
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        return (
            db.query(ExamSchedule)
            .filter(ExamSchedule.course_code.ilike(f"%{course_code}%"))
            .order_by(ExamSchedule.exam_date)
            .all()
        )
    finally:
        if close_after:
            db.close()


def fetch_reception_hours(department: str | None = None, db: Session | None = None) -> list[ReceptionHours]:
    """
    Return reception hour rows.
    If `department` is provided, filter by partial name match (Hebrew-safe ilike).
    Ordered by department name then day of week.
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        q = db.query(ReceptionHours)
        if department:
            q = q.filter(ReceptionHours.department.ilike(f"%{department}%"))
        return q.order_by(ReceptionHours.department, ReceptionHours.day_of_week).all()
    finally:
        if close_after:
            db.close()


def fetch_room_locations(
    building: str | None = None,
    room_type: str | None = None,
    accessible_only: bool = False,
    db: Session | None = None,
) -> list[RoomLocation]:
    """
    Return room location rows with optional filters.

    Args:
        building:        Partial building name match.
        room_type:       Exact type string, e.g. "classroom" | "lab" | "office".
        accessible_only: If True, returns only wheelchair-accessible rooms.
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        q = db.query(RoomLocation)
        if building:
            q = q.filter(RoomLocation.building.ilike(f"%{building}%"))
        if room_type:
            q = q.filter(RoomLocation.room_type == room_type)
        if accessible_only:
            q = q.filter(RoomLocation.is_accessible.is_(True))
        return q.order_by(RoomLocation.building, RoomLocation.room_number).all()
    finally:
        if close_after:
            db.close()


def fetch_room_by_number(building: str, room_number: str, db: Session | None = None) -> RoomLocation | None:
    """
    Return a single room by exact building + room_number, or None if not found.
    Used for direct questions like "Where is room 204 in Engineering Building A?"
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        return (
            db.query(RoomLocation)
            .filter(
                RoomLocation.building == building,
                RoomLocation.room_number == room_number,
            )
            .first()
        )
    finally:
        if close_after:
            db.close()


def fetch_exams_grades(topic: str | None = None, db: Session | None = None) -> list[ExamsGradesInfo]:
    """
    Return exams & grades FAQ entries.
    If `topic` is provided, filter by topic (e.g., "appeals", "publication", "policy").
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        q = db.query(ExamsGradesInfo)
        if topic:
            q = q.filter(ExamsGradesInfo.topic == topic)
        return q.order_by(ExamsGradesInfo.created_at).all()
    finally:
        if close_after:
            db.close()


def fetch_library_services(topic: str | None = None, db: Session | None = None) -> list[LibraryServicesInfo]:
    """
    Return library services FAQ entries.
    If `topic` is provided, filter by topic (e.g., "hours", "access", "databases", "borrowing").
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        q = db.query(LibraryServicesInfo)
        if topic:
            q = q.filter(LibraryServicesInfo.topic == topic)
        return q.order_by(LibraryServicesInfo.created_at).all()
    finally:
        if close_after:
            db.close()


def fetch_student_services(topic: str | None = None, db: Session | None = None) -> list[StudentServicesInfo]:
    """
    Return student services FAQ entries.
    If `topic` is provided, filter by topic (e.g., "housing", "union", "clubs", "financial", "wellness").
    """
    close_after = db is None
    if db is None:
        db = SessionLocal()
    try:
        q = db.query(StudentServicesInfo)
        if topic:
            q = q.filter(StudentServicesInfo.topic == topic)
        return q.order_by(StudentServicesInfo.created_at).all()
    finally:
        if close_after:
            db.close()


# ===========================================================================
# SECTION 4 — PRETTY-PRINT HELPERS (for CLI verification)
# ===========================================================================

def _print_section(title: str, rows: Sequence) -> None:
    width = 72
    print(f"\n{'=' * width}")
    print(f"  {title}  ({len(rows)} rows)")
    print("=" * width)
    for row in rows:
        print(" ", row)


def _run_verification() -> None:
    """Fetch and display all seeded data to confirm the DB is populated."""
    print("\n📋  Smart Campus Assistant — Database Verification")

    exams    = fetch_all_exams()
    recept   = fetch_reception_hours()
    rooms    = fetch_room_locations()
    grades   = fetch_exams_grades()
    library  = fetch_library_services()
    services = fetch_student_services()

    _print_section("EXAM SCHEDULES", exams)
    _print_section("RECEPTION HOURS", recept)
    _print_section("ROOM LOCATIONS", rooms)
    _print_section("EXAMS & GRADES FAQ", grades)
    _print_section("LIBRARY SERVICES FAQ", library)
    _print_section("STUDENT SERVICES FAQ", services)

    # Demonstrate filtered queries
    cs_exams = fetch_exams_by_course("CS")
    _print_section("FILTERED — CS courses only", cs_exams)

    accessible = fetch_room_locations(accessible_only=True)
    _print_section("FILTERED — Accessible rooms only", accessible)

    labs = fetch_room_locations(room_type="lab")
    _print_section("FILTERED — Labs only", labs)

    appeals = fetch_exams_grades(topic="appeals")
    _print_section("FILTERED — Grade appeals FAQ only", appeals)

    lib_hours = fetch_library_services(topic="hours")
    _print_section("FILTERED — Library hours FAQ only", lib_hours)

    housing = fetch_student_services(topic="housing")
    _print_section("FILTERED — Housing FAQ only", housing)

    single = fetch_room_by_number("בניין הנדסה א׳", "204")
    print(f"\n🔍  fetch_room_by_number('בניין הנדסה א׳', '204') → {single}")

    print("\n✅  Verification complete.\n")


# ===========================================================================
# SECTION 5 — SCRIPT ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    # Ensure tables exist (idempotent — safe if already created by main.py)
    init_db()

    # Seed mock data
    summary = seed_all()
    print(f"\n🌱  Seeded: {summary}")

    # Verify by reading back from DB
    _run_verification()

    sys.exit(0)

from __future__ import annotations

from datetime import datetime

from database import ExamSchedule, ReceptionHours, RoomLocation, ExamsGradesInfo, LibraryServicesInfo, StudentServicesInfo
from seed import fetch_all_exams, fetch_reception_hours, fetch_room_locations, fetch_exams_grades, fetch_library_services, fetch_student_services


def detect_user_language(text: str) -> str:
    """
    Detect whether the user's question is in Hebrew or English.
    
    Returns: "hebrew" or "english"
    """
    # Count Hebrew characters (Unicode range 0x0590-0x05FF)
    hebrew_count = sum(1 for c in text if 0x0590 <= ord(c) <= 0x05FF)
    # Count English letters
    english_count = sum(1 for c in text if c.isascii() and c.isalpha())
    
    # If text has Hebrew characters, classify as Hebrew
    # Otherwise classify as English
    return "hebrew" if hebrew_count > 0 else "english"


def _format_exams(exams: list[ExamSchedule]) -> str:
    """Render exam rows as a numbered plain-text list."""
    if not exams:
        return "  (אין מבחנים זמינים / No exams currently available)"

    lines: list[str] = []
    for e in exams:
        line = (
            f"  • [{e.course_code}] {e.course_name} | "
            f"תאריך/Date: {e.exam_date} | "
            f"שעה/Time: {e.start_time}–{e.end_time} | "
            f"מיקום/Location: {e.building}, Room {e.room_number}"
        )
        if e.lecturer:
            line += f" | מרצה/Lecturer: {e.lecturer}"
        if e.notes:
            line += f" | הערות/Notes: {e.notes}"
        lines.append(line)
    return "\n".join(lines)


def _format_reception(hours: list[ReceptionHours]) -> str:
    """Render reception-hour rows grouped by department."""
    if not hours:
        return "  (אין שעות קבלה זמינות / No reception hours available)"

    lines: list[str] = []
    current_dept = ""
    for h in hours:
        if h.department != current_dept:
            current_dept = h.department
            lines.append(f"\n  ▸ {h.department}")
            if h.contact_person:
                lines.append(f"    איש קשר/Contact: {h.contact_person}")
            if h.room_number:
                lines.append(f"    חדר/Room: {h.room_number}")
            if h.phone:
                lines.append(f"    טלפון/Phone: {h.phone}")
            if h.email:
                lines.append(f"    אימייל/Email: {h.email}")

        appt = " (בתיאום מראש / By appointment only)" if h.is_by_appointment else ""
        lines.append(
            f"    – {h.day_of_week}: {h.open_time}–{h.close_time}{appt}"
        )
        if h.notes:
            lines.append(f"      * {h.notes}")

    return "\n".join(lines)


def _format_rooms(rooms: list[RoomLocation]) -> str:
    """Render room rows as a plain-text list."""
    if not rooms:
        return "  (אין חדרים במאגר / No rooms in database)"

    lines: list[str] = []
    for r in rooms:
        accessible = "✓ נגיש/Accessible" if r.is_accessible else "✗ לא נגיש/Not accessible"
        elevator   = " | מעלית/Elevator: ✓" if r.has_elevator_access else ""
        capacity   = f" | קיבולת/Capacity: {r.capacity}" if r.capacity else ""
        name_part  = f" ({r.room_name})" if r.room_name else ""

        line = (
            f"  • {r.building} — Room {r.room_number}{name_part} | "
            f"סוג/Type: {r.room_type} | קומה/Floor: {r.floor if r.floor is not None else '?'}"
            f"{capacity} | {accessible}{elevator}"
        )
        if r.directions:
            line += f"\n    ➜ {r.directions}"
        if r.notes:
            line += f"\n    * {r.notes}"
        lines.append(line)
    return "\n".join(lines)


def _format_exams_grades(grades: list[ExamsGradesInfo]) -> str:
    """Render exams & grades FAQ entries as a plain-text list."""
    if not grades:
        return "  (אין נתונים זמינים / No data available)"

    lines: list[str] = []
    for g in grades:
        lines.append(f"  ❓ {g.question}")
        lines.append(f"     ✓ {g.answer}")
    return "\n".join(lines)


def _format_library_services(library: list[LibraryServicesInfo]) -> str:
    """Render library services FAQ entries as a plain-text list."""
    if not library:
        return "  (אין נתונים זמינים / No data available)"

    lines: list[str] = []
    for l in library:
        lines.append(f"  ❓ {l.question}")
        lines.append(f"     ✓ {l.answer}")
    return "\n".join(lines)


def _format_student_services(services: list[StudentServicesInfo]) -> str:
    """Render student services FAQ entries as a plain-text list."""
    if not services:
        return "  (אין נתונים זמינים / No data available)"

    lines: list[str] = []
    for s in services:
        lines.append(f"  ❓ {s.question}")
        lines.append(f"     ✓ {s.answer}")
    return "\n".join(lines)


# The <<CONTEXT_BLOCK>> placeholder is replaced at call time with live DB data.
# Keeping it as a single template constant makes unit-testing the prompt
# structure trivial — just assert the placeholder is replaced correctly.

_SYSTEM_PROMPT_TEMPLATE = """\
You are "Campus Assistant" (עוזר הקמפוס), the official AI assistant for \
an academic campus. You help students and staff with:
  • exam schedules and reception hours  # fixed: removed raw key from user-facing label
  • room locations and campus navigation  # fixed: removed raw key from user-facing label
  • technical issues and system support  # fixed: removed raw key from user-facing label
  • exam grades and grade appeals  # fixed: removed raw key from user-facing label
  • library services and databases  # fixed: removed raw key from user-facing label
  • student housing and union activities  # fixed: removed raw key from user-facing label

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATEGORIZATION INSTRUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The system has classified the user's question into ONE of these 6 categories:
  1. schedule           — exam dates, reception hours, office availability
  2. general_info       — room locations, navigation, campus facilities
  3. technical_issue    — IT support, login, passwords, Wi-Fi, systems
  4. exams_and_grades   — grades, appeals, exam policy, academic records
  5. library_services   — library hours, databases, borrowing, research
  6. student_union_and_dorms — housing, student clubs, union services, events

Your answer MUST be grounded ONLY in the CAMPUS DATA CONTEXT below.
Do NOT make up answers outside this scope.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE RULE — HIGHEST PRIORITY, DO NOT OVERRIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**CRITICAL INSTRUCTION:** {language_instruction}

STRICT LANGUAGE MATCHING RULES:
1. DETECT the user's language FIRST:
   - If the question contains Hebrew characters (שׂ-ת) → User is asking in Hebrew
   - If the question contains ONLY English (A-Z, a-z, 0-9) → User is asking in English

2. RESPOND EXCLUSIVELY in the user's language:
   - If user asked in HEBREW → respond 100% in HEBREW (no English words)
   - If user asked in ENGLISH → respond 100% in ENGLISH (no Hebrew words)
   - This rule OVERRIDES all other formatting or context considerations

3. TRANSLATION REQUIREMENT:
   - If the database context is in Hebrew but the user asked in English,
     you MUST translate all relevant facts into English
   - If the database context is in English but the user asked in Hebrew,
     you MUST translate all relevant facts into Hebrew
   - Never include the original language alongside translations

4. ABSOLUTE NO-MIX RULE:
   - NEVER mix Hebrew and English in the same response
   - NEVER include Hebrew snippets in an English answer
   - NEVER include English snippets in a Hebrew answer
   - This is your PRIMARY obligation before any other instruction

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROUNDING RULES — MANDATORY, NO EXCEPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST follow ALL of these rules on every single response:

1. ONLY use information that appears explicitly in the CAMPUS DATA CONTEXT
   section below. Do NOT use any knowledge from your training data.
2. If the answer is not found in the context, you MUST respond with the
   exact fallback message defined in the FALLBACK RULES section.
   DO NOT guess, infer, or approximate any fact.
3. Do NOT invent course names, room numbers, dates, times, phone numbers,
   email addresses, staff names, or any other factual detail.
4. Do NOT say "I think", "probably", "I believe", or any other hedging
   phrase that implies you are guessing. If you don't know, use the fallback.
5. Do NOT refer to external websites, search engines, or sources outside
   this system. All answers must come from the context below.
6. Quote data from the context accurately. Do not paraphrase numbers,
   times, dates, or proper names.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FALLBACK RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When the requested information is NOT present in the context, respond with
EXACTLY this message in the user's detected language:

  Hebrew fallback:
  "מצטער/ת, אין לי את המידע הזה במערכת. לשאלות נוספות, אנא פנה/י ישירות
   למזכירות האוניברסיטה בטלפון 03-6789001 או בדוא״ל registrar@campus.ac.il."

  English fallback:
  "I'm sorry, I don't have that information in my system. For further
   assistance, please contact the University Registrar directly at
   03-6789001 or registrar@campus.ac.il."

Use this fallback for:
  – Questions about courses, departments, or people not listed in the data
  – Questions about academic content, grades, or admissions
  – Any question that requires knowledge outside campus logistics
  – Technical issues the IT department must resolve directly
  – Any other topic not covered by the six data categories below

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATTING RULES — FEW-SHOT EXAMPLES (BUG FIX #2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A. ABSOLUTE PLAIN-TEXT RULE:
Your response MUST be PLAIN TEXT ONLY. NEVER use:
  - Markdown syntax: ** * __ _ # ` ~
  - Asterisks (*) for any reason — not for emphasis, not for bullets
  - Underscores (_) for any reason — not for formatting or emphasis
  - Hash symbols (#) for headers
  - Backticks (`) for code blocks
  - HTML tags: angle brackets, curly braces, or any markup
  - Bullet dashes or numbered list dots with markdown
  - Any special formatting characters whatsoever

Write ONLY plain text as if typing in a basic text editor (like Notepad).

B. FEW-SHOT EXAMPLES (Label each INCORRECT → CORRECT pair):

EXAMPLE 1 — Reception Hours Response:

INCORRECT (do NOT output like this):
**Monday-Friday:** 09:00–17:00
**Saturday:** 10:00–14:00
**Sunday:** Closed
**Contact:** +972-3-6789001

CORRECT (output EXACTLY like this):
Monday-Friday: 09:00 to 17:00
Saturday: 10:00 to 14:00
Sunday: Closed
Contact: +972-3-6789001

EXAMPLE 2 — Exam Schedule Response:

INCORRECT (do NOT output like this):
**Course:** Data Structures (CS201)
**Date:** 15 March 2026
**Time:** 14:00–16:00
**Location:** Building 72, Room 204

CORRECT (output EXACTLY like this):
Course: Data Structures (CS201)
Date: 15 March 2026
Time: 14:00 to 16:00
Location: Building 72, Room 204

EXAMPLE 3 — Room Location Response:

INCORRECT (do NOT output like this):
* Building: Engineering 2
* Room number: 305
* Floor: 3
* Accessible: Yes
* Elevator: Available

CORRECT (output EXACTLY like this):
Building: Engineering 2
Room number: 305
Floor: 3
Accessible: Yes
Elevator: Available

C. LANGUAGE MATCHING RULE (BUG FIX #2 — Part B):
1. Detect the user's language (Hebrew or English) from their question.
2. Respond ENTIRELY in that language — do not mix.
3. If the database context is in Hebrew but the user asked in English:
   - Translate all relevant facts to English
   - Do not include Hebrew text in your response
4. If the database context is in English but the user asked in Hebrew:
   - Translate all relevant facts to Hebrew
   - Do not include English text in your response
5. Never include the original language alongside translations.
6. Never mix Hebrew and English in a single response.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Be concise and friendly. Address the student or staff member politely.
- Present exam schedules as structured lists (date, time, location).
- Present reception hours clearly, mentioning appointment requirements.
- For room directions, include floor and any accessibility notes.
- If multiple results match, list all of them.
- End factual answers with a brief offer to help further, in the
  user's language.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TODAY'S DATE / תאריך היום
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{today}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMPUS DATA CONTEXT — THE ONLY SOURCE OF TRUTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF CONTEXT — do not use any information beyond this boundary.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\
"""

def _build_context_block(
    exams: list[ExamSchedule],
    reception: list[ReceptionHours],
    rooms: list[RoomLocation],
    exams_grades: list[ExamsGradesInfo],
    library_services: list[LibraryServicesInfo],
    student_services: list[StudentServicesInfo],
) -> str:
    """
    Assemble all six data sections into a single formatted context string
    that will be injected into the system prompt.
    """
    return (
        "[ מבחנים / EXAM SCHEDULES ]\n"
        f"{_format_exams(exams)}\n\n"
        "[ שעות קבלה / RECEPTION HOURS ]\n"
        f"{_format_reception(reception)}\n\n"
        "[ מיקומי חדרים / ROOM LOCATIONS ]\n"
        f"{_format_rooms(rooms)}\n\n"
        "[ ציונים ובחינות / EXAMS & GRADES FAQ ]\n"
        f"{_format_exams_grades(exams_grades)}\n\n"
        "[ שירותי ספרייה / LIBRARY SERVICES FAQ ]\n"
        f"{_format_library_services(library_services)}\n\n"
        "[ שירותי סטודנטים / STUDENT SERVICES FAQ ]\n"
        f"{_format_student_services(student_services)}"
    )


def build_system_prompt(
    exams: list[ExamSchedule] | None = None,
    reception: list[ReceptionHours] | None = None,
    rooms: list[RoomLocation] | None = None,
    exams_grades: list[ExamsGradesInfo] | None = None,
    library_services: list[LibraryServicesInfo] | None = None,
    student_services: list[StudentServicesInfo] | None = None,
    user_language: str = "hebrew",
) -> str:
    """
    Return a fully-formed system prompt string with live DB data injected.

    If the caller passes pre-fetched lists (e.g. from a request-scoped DB
    session in routers.py), those are used directly — no extra DB round-trip.
    If any argument is None, the function fetches it using its own session.

    Args:
        exams:               Pre-fetched ExamSchedule rows, or None to auto-fetch.
        reception:           Pre-fetched ReceptionHours rows, or None to auto-fetch.
        rooms:               Pre-fetched RoomLocation rows, or None to auto-fetch.
        exams_grades:        Pre-fetched ExamsGradesInfo rows, or None to auto-fetch.
        library_services:    Pre-fetched LibraryServicesInfo rows, or None to auto-fetch.
        student_services:    Pre-fetched StudentServicesInfo rows, or None to auto-fetch.
        user_language:       "hebrew" or "english" — explicitly tells AI which language to use.

    Returns:
        A single string ready to be used as {"role": "system", "content": <here>}.
    """
    _exams           = exams           if exams           is not None else fetch_all_exams()
    _reception       = reception       if reception       is not None else fetch_reception_hours()
    _rooms           = rooms           if rooms           is not None else fetch_room_locations()
    _exams_grades    = exams_grades    if exams_grades    is not None else fetch_exams_grades()
    _library_services = library_services if library_services is not None else fetch_library_services()
    _student_services = student_services if student_services is not None else fetch_student_services()

    context_block = _build_context_block(_exams, _reception, _rooms, _exams_grades, _library_services, _student_services)
    today_str     = datetime.now().strftime("%A, %d %B %Y")   # e.g. "Sunday, 09 February 2025"
    
    # Create explicit language instruction
    if user_language == "english":
        language_instruction = "RESPOND IN ENGLISH ONLY. Do not use Hebrew. Use English for all words, names, and explanations."
    else:
        language_instruction = "השב בעברית בלבד. אל תשתמש באנגלית. השתמש בעברית לכל המילים, השמות וההסברים."

    return _SYSTEM_PROMPT_TEMPLATE.format(
        today=today_str,
        context_block=context_block,
        language_instruction=language_instruction,
    )


def build_messages(
    user_question: str,
    exams: list[ExamSchedule] | None = None,
    reception: list[ReceptionHours] | None = None,
    rooms: list[RoomLocation] | None = None,
    exams_grades: list[ExamsGradesInfo] | None = None,
    library_services: list[LibraryServicesInfo] | None = None,
    student_services: list[StudentServicesInfo] | None = None,
    conversation_history: list[dict] | None = None,
) -> list[dict[str, str]]:
    """
    Assemble the complete message list for chat_completion().
    
    Args:
        user_question: The raw question string from the POST /ask payload.
        exams:         Optional pre-fetched DB rows (see build_system_prompt).
        reception:     Optional pre-fetched DB rows.
        rooms:         Optional pre-fetched DB rows.
        exams_grades:  Optional pre-fetched DB rows.
        library_services: Optional pre-fetched DB rows.
        student_services: Optional pre-fetched DB rows.
        conversation_history: Optional list of prior messages (role, content) from session manager.

    Returns:
        A message list starting with system prompt, followed by conversation history,
        and ending with the current user question:
          [
            {"role": "system",  "content": "<full grounded system prompt>"},
            {"role": "user",    "content": "<prior user msg 1>"} (if history exists),
            {"role": "assistant", "content": "<prior assistant msg 1>"} (if history exists),
            ...
            {"role": "user",    "content": "<current user question>"},
          ]
    """
    # Detect user's language
    user_language = detect_user_language(user_question)
    
    # Build system prompt with explicit language instruction
    system_prompt = build_system_prompt(
        exams=exams, 
        reception=reception, 
        rooms=rooms,
        exams_grades=exams_grades,
        library_services=library_services,
        student_services=student_services,
        user_language=user_language,
    )
    
    # Start with system prompt
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add current user question
    messages.append({"role": "user", "content": user_question})
    
    return messages


if __name__ == "__main__":
    """
    Print the fully-rendered system prompt to stdout for manual inspection.
    Run:  python ai_prompt.py
    """
    from database import init_db
    init_db()

    sample_question = "מתי המבחן של CS101?"
    messages = build_messages(sample_question)

    print("=" * 72)
    print("SYSTEM PROMPT PREVIEW")
    print("=" * 72)
    print(messages[0]["content"])
    print("" + "=" * 72)
    print(f"USER MESSAGE: {messages[1]['content']}")
    print("=" * 72)
    print(f"{len(messages[0]['content'])} chars in system prompt | "
          f"{len(messages)} messages total")

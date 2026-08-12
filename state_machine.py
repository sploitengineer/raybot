import uuid
from datetime import datetime

# ── State Constants ─────────────────────────────────────────────────────
GREETING = "GREETING"
MAIN_MENU = "MAIN_MENU"

# Booking Flow
BOOK_APPT_SERVICE = "BOOK_APPT_SERVICE"
BOOK_APPT_STAFF = "BOOK_APPT_STAFF"
BOOK_APPT_DATE = "BOOK_APPT_DATE"
BOOK_APPT_TIME = "BOOK_APPT_TIME"
BOOK_APPT_NAME = "BOOK_APPT_NAME"
BOOK_APPT_EMAIL = "BOOK_APPT_EMAIL"

# Quote Flow
QUOTE_DESCRIBE = "QUOTE_DESCRIBE"
QUOTE_PHOTO = "QUOTE_PHOTO"
QUOTE_PENCIL_IN = "QUOTE_PENCIL_IN"

# FAQ / Ask Question Flow
FAQ_MENU = "FAQ_MENU"
FAQ_ANSWER = "FAQ_ANSWER"

# Talk to Person Flow
TALK_PERSON_CONTACT = "TALK_PERSON_CONTACT"
TALK_PERSON_DESCRIBE = "TALK_PERSON_DESCRIBE"

# Lead Capture
LEAD_CAPTURE = "LEAD_CAPTURE"

# Reschedule / Cancel Flow
FIND_BOOKING = "FIND_BOOKING"
MANAGE_BOOKING = "MANAGE_BOOKING"
RESCHEDULE_TIME = "RESCHEDULE_TIME"
CANCEL_CONFIRM = "CANCEL_CONFIRM"

class UserSession:
    """Tracks all data for one user's journey."""

    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.state = GREETING
        
        # Booking selections
        self.selected_service_id = None
        self.selected_staff_id = None
        self.selected_date = None
        self.selected_time = None
        self.booking_name = None
        self.booking_contact = None
        
        # Talk to a person data
        self.issue_description = None
        
        # Quote data
        self.quote_description = None
        
        self.created_at = datetime.now().isoformat()
        
        # A flag to ensure we don't ask for a lead capture twice
        self.has_asked_lead_capture = False

# ── Session Store ───────────────────────────────────────────────────────
_sessions: dict[str, UserSession] = {}

def get_session(phone: str) -> UserSession:
    """Get or create a session for a phone number."""
    if phone not in _sessions:
        _sessions[phone] = UserSession(phone)
    return _sessions[phone]

def reset_session(phone: str):
    """Reset a user's session (start fresh)."""
    _sessions[phone] = UserSession(phone)
    return _sessions[phone]

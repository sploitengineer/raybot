import os
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Local modules
from models import get_client_config, save_lead, save_ticket
from calendar_service import (
    get_available_slots, book_appointment, reschedule_appointment, 
    cancel_appointment, get_authorization_url, fetch_and_save_tokens
)
from state_machine import (
    get_session, reset_session, UserSession,
    GREETING, MAIN_MENU,
    BOOK_APPT_SERVICE, BOOK_APPT_STAFF, BOOK_APPT_DATE, BOOK_APPT_TIME, BOOK_APPT_NAME, BOOK_APPT_EMAIL,
    QUOTE_DESCRIBE, QUOTE_PHOTO, QUOTE_PENCIL_IN,
    FAQ_MENU, FAQ_ANSWER,
    TALK_PERSON_CONTACT, TALK_PERSON_DESCRIBE,
    LEAD_CAPTURE,
    FIND_BOOKING, MANAGE_BOOKING, RESCHEDULE_TIME, CANCEL_CONFIRM
)

load_dotenv()
app = Flask(__name__)

# ── Configuration ───────────────────────────────────────────────────────
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "TEST_PHONE_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "TEST_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "TEST_VERIFY")
WHATSAPP_API_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

SEEN_MESSAGES = {}
DEDUP_WINDOW = 60

def is_duplicate(msg_id: str) -> bool:
    now = time.time()
    for k in [k for k, v in SEEN_MESSAGES.items() if now - v > DEDUP_WINDOW]: del SEEN_MESSAGES[k]
    if msg_id in SEEN_MESSAGES: return True
    SEEN_MESSAGES[msg_id] = now
    return False

def _api_headers():
    return {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

def send_whatsapp_message(to: str, text: str):
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    try:
        requests.post(WHATSAPP_API_URL, headers=_api_headers(), json=payload).raise_for_status()
    except Exception as e: print(f"Error sending message: {e}")

def send_interactive_buttons(to: str, body: str, buttons: list):
    btn_list = [{"type": "reply", "reply": {"id": b[0], "title": b[1][:20]}} for b in buttons]
    payload = {
        "messaging_product": "whatsapp", "to": to, "type": "interactive",
        "interactive": {"type": "button", "body": {"text": body}, "action": {"buttons": btn_list}}
    }
    try:
        requests.post(WHATSAPP_API_URL, headers=_api_headers(), json=payload).raise_for_status()
    except Exception as e: print(f"Error sending buttons: {e}")

def send_interactive_list(to: str, body: str, button: str, sections: list):
    payload = {
        "messaging_product": "whatsapp", "to": to, "type": "interactive",
        "interactive": {"type": "list", "body": {"text": body}, "action": {"button": button, "sections": sections}}
    }
    try:
        requests.post(WHATSAPP_API_URL, headers=_api_headers(), json=payload).raise_for_status()
    except Exception as e: print(f"Error sending list: {e}")

# ── 1. Greeting ───────────────────────────────────────────────────────
def handle_greeting(to: str, session: UserSession, config):
    session.state = MAIN_MENU
    body = f"Hi! 👋 Welcome to {config.business_name}. How can I help you today?"
    send_interactive_buttons(to, body, [
        ("menu_book", "📅 Book appt"),
        ("menu_faq", "❓ Ask a question"),
        ("menu_talk", "🙋 Talk to person")
    ])

# ── 2A. Book an appointment ───────────────────────────────────────────
def handle_book_service(to: str, session: UserSession, config):
    if not config.services:
        handle_greeting(to, session, config)
        return
    if len(config.services) == 1:
        session.selected_service_id = config.services[0].id
        handle_book_staff(to, session, config)
        return
        
    session.state = BOOK_APPT_SERVICE
    rows = []
    for s in config.services:
        title = f"{s.name} - ${s.price}" if s.price_type == 'fixed_price' else f"{s.name} - Ask Quote"
        rows.append({"id": f"srv_{s.id}", "title": title[:24]})
        
    send_interactive_list(to, "Great! What would you like to book?", "Select Service", [
        {"title": "Services", "rows": rows}
    ])

def handle_book_staff(to: str, session: UserSession, config):
    # Check if selected service requires quote
    service = next((s for s in config.services if s.id == session.selected_service_id), None)
    if service and service.price_type == 'requires_quote':
        session.state = QUOTE_DESCRIBE
        send_whatsapp_message(to, f"{service.name} pricing depends on the job — can you tell me a bit about what you need done?")
        return

    if not config.has_multiple_staff or len(config.staff) <= 1:
        session.selected_staff_id = config.staff[0].id if config.staff else "default"
        handle_book_date(to, session, config)
        return
        
    session.state = BOOK_APPT_STAFF
    buttons = [("staff_no_pref", "No preference")]
    for st in config.staff[:2]:
        buttons.insert(0, (f"stf_{st.id}", st.name))
    send_interactive_buttons(to, "Who would you like to see?", buttons)

from datetime import datetime, timedelta

def handle_book_date(to: str, session: UserSession, config):
    session.state = BOOK_APPT_DATE
    
    today_str = datetime.now().strftime("%d %b")
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%d %b")
    
    send_interactive_buttons(to, "When would you like to come in?", [
        ("date_today", f"Today - {today_str}"),
        ("date_tomorrow", f"Tomorrow - {tomorrow_str}")
    ])

def handle_book_time(to: str, session: UserSession, config):
    session.state = BOOK_APPT_TIME
    slots = get_available_slots(session.selected_staff_id, session.selected_date)
    if not slots:
        send_interactive_buttons(to, f"Looks like we are fully booked on {session.selected_date}. Want to try another day or join waitlist?", [
            ("waitlist", "Join waitlist"), ("menu_main", "Main Menu")
        ])
        return

    rows = [{"id": f"time_{slot}", "title": slot} for slot in slots]
    send_interactive_list(to, f"Here are the next available times for {session.selected_date}:", "Select Time", [
        {"title": "Available Times", "rows": rows}
    ])

def handle_book_name(to: str, session: UserSession, config):
    session.state = BOOK_APPT_NAME
    send_whatsapp_message(to, "Almost done! Can I get your full name to confirm the booking?")

def handle_book_email(to: str, session: UserSession, config):
    session.state = BOOK_APPT_EMAIL
    send_whatsapp_message(to, f"Thanks {session.booking_name}! What is your email address so we can send you the calendar invite?")

def handle_confirm_booking(to: str, session: UserSession, config):
    success = book_appointment(session.selected_service_id, session.selected_staff_id, session.selected_date, session.selected_time, session.booking_name, session.booking_contact)
    service_name = next((s.name for s in config.services if s.id == session.selected_service_id), "Service")
    
    if success:
        send_whatsapp_message(to, f"✅ You're booked in for {service_name} on {session.selected_date.capitalize()} at {session.selected_time}. We've sent a calendar invite to {session.booking_contact}. See you then!")
        # Since they booked, don't pester them for lead capture later
        session.has_asked_lead_capture = True
    else:
        send_whatsapp_message(to, f"❌ Oops! Something went wrong while saving your calendar event. We will contact you shortly to confirm.")
        
    # Follow-up offer
    session.state = MAIN_MENU
    send_interactive_buttons(to, "Anything else I can help with?", [
        ("menu_book", "Book another"),
        ("menu_faq", "Ask a question"),
        ("menu_end", "No thanks")
    ])

# ── 2B. Ask a question (FAQ) ──────────────────────────────────────────
def handle_faq_menu(to: str, session: UserSession, config):
    session.state = FAQ_MENU
    rows = [{"id": f"faq_{i}", "title": f.topic[:24]} for i, f in enumerate(config.faqs)]
    send_interactive_list(to, "Sure — here are some things people often ask, or just type your question:", "Select FAQ", [
        {"title": "Questions", "rows": rows}
    ])

def handle_faq_answer(to: str, session: UserSession, config, faq_index: int):
    session.state = FAQ_ANSWER
    answer = config.faqs[faq_index].answer
    send_whatsapp_message(to, answer)
    send_interactive_buttons(to, "Was that helpful?", [
        ("faq_yes", "Yes"),
        ("menu_talk", "No, I need help"),
        ("menu_book", "Book appt")
    ])

# ── 2C. Talk to a person ──────────────────────────────────────────────
def handle_talk_contact(to: str, session: UserSession, config):
    session.state = TALK_PERSON_CONTACT
    send_whatsapp_message(to, "No problem — let me get someone to help. What's your name and the best way to reach you?")

def handle_talk_describe(to: str, session: UserSession, config):
    session.state = TALK_PERSON_DESCRIBE
    send_whatsapp_message(to, "What's this about, briefly?")

def handle_talk_confirm(to: str, session: UserSession, config, text: str):
    session.issue_description = text
    save_ticket("User", session.booking_contact or to, session.issue_description)
    send_whatsapp_message(to, f"Thanks! I've passed this on to the team at {config.business_name} — they'll be in touch shortly.")
    reset_session(session.phone_number)

# ── 10. Lead capture ──────────────────────────────────────────────────
def handle_lead_capture(to: str, session: UserSession, config, source: str):
    if session.has_asked_lead_capture:
        send_whatsapp_message(to, "No problem, feel free to come back anytime!")
        reset_session(session.phone_number)
        return
    session.state = LEAD_CAPTURE
    session.has_asked_lead_capture = True
    session.lead_source = source
    send_interactive_buttons(to, "No worries! Want us to keep you posted on offers/availability? Just drop your name and email/phone.", [
        ("lead_yes", "Yes, add me"),
        ("lead_no", "No thanks")
    ])

# ── Webhook Routing ───────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health_check(): return jsonify({"status": "healthy"}), 200

@app.route("/login")
def login(): return f'<a href="{get_authorization_url()}">Connect Google Calendar</a>'

@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    if code:
        fetch_and_save_tokens(code)
        return "Connected!"
    return "Failed", 400

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    if data.get("object") != "whatsapp_business_account": return jsonify({"status": "ok"}), 200

    config = get_client_config()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            messages = change.get("value", {}).get("messages", [])
            for message in messages:
                msg_id = message.get("id", "")
                if is_duplicate(msg_id): continue

                sender = message.get("from")
                msg_type = message.get("type")
                session = get_session(sender)
                
                text = message.get("text", {}).get("body", "").strip() if msg_type == "text" else ""
                selected_id = ""
                if msg_type == "interactive":
                    if "button_reply" in message["interactive"]: selected_id = message["interactive"]["button_reply"]["id"]
                    elif "list_reply" in message["interactive"]: selected_id = message["interactive"]["list_reply"]["id"]

                # Reset trigger
                if text.lower() in ["hi", "hello", "start"]:
                    handle_greeting(sender, session, config)
                    continue

                # Main Menu Actions
                if selected_id == "menu_book": handle_book_service(sender, session, config)
                elif selected_id == "menu_faq": handle_faq_menu(sender, session, config)
                elif selected_id == "menu_talk": handle_talk_contact(sender, session, config)
                elif selected_id == "menu_end": handle_lead_capture(sender, session, config, "main_menu")

                # Booking Flow
                elif selected_id.startswith("srv_"):
                    session.selected_service_id = selected_id.split("_")[1]
                    handle_book_staff(sender, session, config)
                elif selected_id.startswith("stf_") or selected_id == "staff_no_pref":
                    session.selected_staff_id = selected_id.split("_")[1] if selected_id != "staff_no_pref" else "any"
                    handle_book_date(sender, session, config)
                elif selected_id.startswith("date_"):
                    session.selected_date = selected_id.split("_")[1]
                    handle_book_time(sender, session, config)
                elif selected_id.startswith("time_"):
                    session.selected_time = selected_id.split("_")[1]
                    handle_book_name(sender, session, config)
                elif session.state == BOOK_APPT_NAME:
                    session.booking_name = text
                    handle_book_email(sender, session, config)
                elif session.state == BOOK_APPT_EMAIL:
                    session.booking_contact = text
                    handle_confirm_booking(sender, session, config)
                
                # FAQ Flow
                elif selected_id.startswith("faq_"):
                    if selected_id == "faq_yes":
                        handle_lead_capture(sender, session, config, "faq_no_booking")
                    else:
                        handle_faq_answer(sender, session, config, int(selected_id.split("_")[1]))

                # Talk to person Flow
                elif session.state == TALK_PERSON_CONTACT:
                    session.booking_contact = text
                    handle_talk_describe(sender, session, config)
                elif session.state == TALK_PERSON_DESCRIBE:
                    handle_talk_confirm(sender, session, config, text)

                # Quote Flow
                elif session.state == QUOTE_DESCRIBE:
                    session.quote_description = text
                    session.state = QUOTE_PHOTO
                    send_whatsapp_message(sender, "Got it. Do you have any photos? (Optional, you can skip this by saying 'skip')")
                elif session.state == QUOTE_PHOTO:
                    session.state = QUOTE_PENCIL_IN
                    send_interactive_buttons(sender, "Thanks! Want me to pencil in a tentative time?", [
                        ("quote_pencil_yes", "Yes, pencil in"), ("quote_pencil_no", "No just quote")
                    ])
                elif selected_id == "quote_pencil_yes":
                    handle_book_staff(sender, session, config) # Routes into booking flow tentatively
                elif selected_id == "quote_pencil_no":
                    save_ticket("User", sender, f"Quote Request: {session.quote_description}")
                    send_whatsapp_message(sender, "Done. We'll be in touch with a quote!")
                    reset_session(session.phone_number)

                # Lead Capture
                elif selected_id == "lead_yes":
                    session.state = "LEAD_CAPTURE_CONTACT"
                    send_whatsapp_message(sender, "Great! Drop your name and email/phone.")
                elif selected_id == "lead_no":
                    send_whatsapp_message(sender, "No problem, feel free to come back anytime!")
                    reset_session(session.phone_number)
                elif session.state == "LEAD_CAPTURE_CONTACT":
                    save_lead(text, sender, getattr(session, 'lead_source', 'general'))
                    send_whatsapp_message(sender, "Done, you're on the list!")
                    reset_session(session.phone_number)

                else:
                    # Fallback / Start over
                    handle_greeting(sender, session, config)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(port=5000)

import os
import json
from typing import List
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_FILE = 'token.json'

def get_google_auth_config():
    # Reconstruct the expected client_secret.json structure from env vars
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                # Support both local and render for the callback
                "http://localhost:5000/oauth2callback",
                os.getenv("RENDER_EXTERNAL_URL", "") + "/oauth2callback"
            ]
        }
    }

def get_authorization_url() -> str:
    config = get_google_auth_config()
    config["web"]["redirect_uris"] = [uri for uri in config["web"]["redirect_uris"] if uri]
    
    # Use Render URL if available, otherwise localhost
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    selected_redirect = f"{render_url}/oauth2callback" if render_url else "http://localhost:5000/oauth2callback"
    
    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=selected_redirect
    )
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return auth_url

def fetch_and_save_tokens(code: str):
    config = get_google_auth_config()
    
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    selected_redirect = f"{render_url}/oauth2callback" if render_url else "http://localhost:5000/oauth2callback"
    
    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=selected_redirect
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())

def get_calendar_service():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return build('calendar', 'v3', credentials=creds)
    return None

from datetime import datetime, timedelta, timezone

def get_available_slots(staff_id: str, date_str: str) -> List[str]:
    """
    Get available slots for a specific date (YYYY-MM-DD or 'today'/'tomorrow').
    """
    service = get_calendar_service()
    if not service:
        print("No calendar service available. User not authenticated?")
        return ["09:00 AM", "10:30 AM", "01:00 PM", "03:30 PM"]

    # For simplicity, returning fixed slots for now. 
    all_slots = ["09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"]
    
    valid_slots = []
    now = datetime.now()
    is_today = (date_str == "today")
    
    for slot in all_slots:
        try:
            t = datetime.strptime(slot, "%I:%M %p")
            if is_today:
                if t.hour > now.hour or (t.hour == now.hour and t.minute > now.minute):
                    valid_slots.append(slot)
            else:
                valid_slots.append(slot)
        except:
            valid_slots.append(slot)
            
    return valid_slots

def book_appointment(service_id: str, staff_id: str, date_str: str, time_str: str, name: str, email: str, tentative: bool = False) -> bool:
    """
    Create an event in Google Calendar.
    """
    service = get_calendar_service()
    if not service:
        print("Calendar service not available.")
        return False
        
    print(f"Creating event for {name} on {date_str} at {time_str}")
    
    # Parse date and time
    # If date_str is "today" or "tomorrow", resolve it
    target_date = datetime.now()
    if date_str.lower() == "tomorrow":
        target_date += timedelta(days=1)
    
    # Simple time parsing (e.g., "09:00 AM")
    try:
        t = datetime.strptime(time_str, "%I:%M %p")
        start_dt = target_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    except:
        start_dt = target_date.replace(hour=9, minute=0, second=0, microsecond=0)

    end_dt = start_dt + timedelta(hours=1)
    
    event_body = {
        'summary': f"{'TENTATIVE: ' if tentative else ''}{service_id} - {name}",
        'description': f"Service: {service_id}\nStaff: {staff_id}\nClient: {name}\nContact: {email}",
        'start': {
            'dateTime': start_dt.isoformat() + 'Z',
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_dt.isoformat() + 'Z',
            'timeZone': 'UTC',
        }
    }
    
    # Add attendee if email looks valid
    if "@" in email:
        event_body['attendees'] = [{'email': email}]

    try:
        event = service.events().insert(calendarId='primary', body=event_body, sendUpdates='all').execute()
        print(f"✅ Calendar Event Created: {event.get('htmlLink')}")
        return True
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
        return False

def reschedule_appointment(booking_ref: str, new_date: str, new_time: str) -> bool:
    """
    Mock function to reschedule an event in Google Calendar.
    """
    print(f"Calendar Event Rescheduled: {booking_ref} to {new_date} at {new_time}")
    return True

def cancel_appointment(booking_ref: str) -> bool:
    """
    Mock function to cancel an event in Google Calendar.
    """
    print(f"Calendar Event Cancelled: {booking_ref}")
    return True

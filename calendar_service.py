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
    config["web"]["redirect_uris"] = [uri for uri in config["web"]["redirect_uris"] if uri and not uri.endswith("/oauth2callback")]
    
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

def get_available_slots(staff_id: str, date: str) -> List[str]:
    """
    Mock function to get available slots.
    In real implementation, this will query Google Calendar Free/Busy API.
    """
    return ["09:00 AM", "10:30 AM", "01:00 PM", "03:30 PM"]

def book_appointment(service_id: str, staff_id: str, date: str, time: str, name: str, contact: str, tentative: bool = False) -> bool:
    """
    Mock function to create an event in Google Calendar.
    """
    print(f"Calendar Event Created: {service_id} with {staff_id} on {date} at {time} for {name} ({contact}). Tentative: {tentative}")
    return True

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

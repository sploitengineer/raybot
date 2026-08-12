import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Service:
    id: str
    name: str
    price_type: str # 'fixed_price' or 'requires_quote'
    price: float = 0.0

@dataclass
class Staff:
    id: str
    name: str

@dataclass
class FAQ:
    topic: str
    answer: str

@dataclass
class ClientConfig:
    business_name: str
    business_hours: str
    hours_summary: str
    next_open_time: str
    services: List[Service] = field(default_factory=list)
    staff: List[Staff] = field(default_factory=list)
    faqs: List[FAQ] = field(default_factory=list)
    has_multiple_staff: bool = False
    
# Mock Database for the single tenant
MOCK_CONFIG = ClientConfig(
    business_name="Rayvion Salon",
    business_hours="9 AM - 5 PM, Mon-Fri",
    hours_summary="Monday to Friday, 9am to 5pm",
    next_open_time="9am tomorrow",
    services=[
        Service(id="s1", name="Haircut", price_type="fixed_price", price=45.0),
        Service(id="s2", name="Colour", price_type="fixed_price", price=120.0),
        Service(id="s3", name="Custom Repair", price_type="requires_quote")
    ],
    staff=[
        Staff(id="staff1", name="Alice"),
        Staff(id="staff2", name="Bob")
    ],
    faqs=[
        FAQ(topic="Opening hours", answer="We are open 9 AM - 5 PM from Monday to Friday."),
        FAQ(topic="Pricing", answer="Haircuts start at $45, colours at $120."),
        FAQ(topic="Location", answer="We are located at 123 Main Street.")
    ],
    has_multiple_staff=True
)

def get_client_config() -> ClientConfig:
    return MOCK_CONFIG

# --- Persistence for Leads and Tickets ---
LEADS_FILE = "leads.json"
TICKETS_FILE = "tickets.json"

def save_lead(name: str, contact: str, source: str):
    leads = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            leads = json.load(f)
    leads.append({"name": name, "contact": contact, "source": source})
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=4)
    print(f"Lead saved: {name} ({contact}) from {source}")

def save_ticket(name: str, contact: str, description: str):
    tickets = []
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "r") as f:
            tickets = json.load(f)
    tickets.append({"name": name, "contact": contact, "description": description})
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)
    print(f"Ticket saved: {name} - {description}")

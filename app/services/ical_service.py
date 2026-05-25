from ics import Calendar, Event


def doctor_calendar(doctor_name: str, appointments: list[dict]) -> str:
    cal = Calendar()
    for a in appointments:
        ev = Event()
        ev.name = f"Turno: {a.get('patient_name', 'Paciente')}"
        ev.begin = a["starts_at"]
        ev.end = a["ends_at"]
        ev.description = a.get("reason") or ""
        if a.get("telemedicine_url"):
            ev.url = a["telemedicine_url"]
        cal.events.add(ev)
    return str(cal)

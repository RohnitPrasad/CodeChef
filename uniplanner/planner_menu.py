#!/usr/bin/env python3
"""
University Planner - Menu-based CLI (single file)
Save as planner_menu.py and run: python3 planner_menu.py
No external dependencies.
"""

import json
import os
import shutil
import sys
import uuid
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

DATA_FILE = "data.json"
BACKUP_DIR = "backups"
WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M"

# ---------- Terminal helpers ----------
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def color(text, code):
    return f"\033[{code}m{text}\033[0m"

def header(title):
    clear_screen()
    print(color("="*60, "1;34"))
    print(color(f"{title}".center(60), "1;32"))
    print(color("="*60, "1;34"))
    print()

def pause():
    input(color("\nPress Enter to continue...", "2;37"))

def now_iso():
    return datetime.now().isoformat()

# ---------- Storage ----------
def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        init = {"subjects": [], "attendance": [], "assignments": [], "meta": {"createdAt": now_iso()}}
        with open(DATA_FILE, "w") as f:
            json.dump(init, f, indent=2)

def load_data() -> Dict[str, Any]:
    ensure_data_file()
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d: Dict[str, Any]):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

def backup_data():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"data_backup_{ts}.json")
    shutil.copy2(DATA_FILE, dest)
    return dest

def gen_id():
    return uuid.uuid4().hex[:10]

# ---------- Utilities ----------
def parse_schedule_string(s: str):
    """
    Input example: Mon@09:00-10:30, Tue@11:00-12:30 Room201
    Returns list of dicts: {"day":"Mon","start":"09:00","end":"10:30","location":""}
    """
    items = []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    for p in parts:
        loc = ""
        if " " in p:
            p, loc = p.split(" ", 1)
            loc = loc.strip()
        try:
            day, times = p.split("@")
            start, end = times.split("-")
            items.append({"day": day.strip(), "start": start.strip(), "end": end.strip(), "location": loc})
        except Exception:
            raise ValueError("Bad schedule piece. Example: Mon@09:00-10:30")
    return items

def format_datetime_iso(s: Optional[str]):
    if not s:
        return "N/A"
    try:
        dt = datetime.fromisoformat(s)
        if "T" in s:
            return dt.strftime(DATETIME_FMT)
        return dt.strftime(DATE_FMT)
    except Exception:
        return s

# ---------- Core features ----------
def add_subject():
    header("Add Subject")
    name = input("Subject name (e.g. Calculus): ").strip()
    if not name:
        print(color("Name cannot be empty.", "1;31"))
        pause()
        return
    code = input("Code (optional, e.g. MA101): ").strip()
    prof = input("Professor (optional): ").strip()
    schedule_raw = input("Schedule (comma separated, e.g. Mon@09:00-10:30,Tue@11:00-12:30 Room201) [leave blank if none]: ").strip()
    schedule = []
    if schedule_raw:
        try:
            schedule = parse_schedule_string(schedule_raw)
        except Exception as e:
            print(color(f"Error parsing schedule: {e}", "1;31"))
            pause()
            return
    data = load_data()
    subj = {
        "id": gen_id(),
        "name": name,
        "code": code,
        "prof": prof,
        "schedule": schedule,
        "createdAt": now_iso()
    }
    data["subjects"].append(subj)
    save_data(data)
    print(color("Subject added successfully.", "1;32"))
    pause()

def list_subjects(show_ids: bool = True):
    header("Subjects")
    data = load_data()
    subs = data.get("subjects", [])
    if not subs:
        print(color("No subjects found. Add one from the menu.", "1;33"))
    else:
        for i, s in enumerate(subs, start=1):
            line = f"{i}. {s['name']}" + (f" [{s.get('code')}]" if s.get('code') else "")
            if show_ids:
                line += f" (id:{s['id']})"
            print(color(line, "1;36"))
            if s.get("prof"):
                print(f"   Prof: {s['prof']}")
            if s.get("schedule"):
                for sch in s["schedule"]:
                    loc = f" @ {sch['location']}" if sch.get("location") else ""
                    print(f"   - {sch['day']} {sch['start']}-{sch['end']}{loc}")
            print()
    pause()

def choose_subject(prompt: str) -> Optional[Dict[str, Any]]:
    data = load_data()
    subs = data.get("subjects", [])
    if not subs:
        print(color("No subjects available. Add subjects first.", "1;33"))
        pause()
        return None
    print(prompt)
    for idx, s in enumerate(subs, start=1):
        print(f"{idx}. {s['name']} ({s.get('code','')})")
    choice = input("Enter number: ").strip()
    if not choice.isdigit():
        print(color("Invalid input.", "1;31"))
        pause()
        return None
    n = int(choice)
    if n < 1 or n > len(subs):
        print(color("Number out of range.", "1;31"))
        pause()
        return None
    return subs[n-1]

def record_attendance():
    header("Record Attendance")
    subj = choose_subject("Select subject to record attendance for:")
    if not subj:
        return
    dt_in = input(f"Date (YYYY-MM-DD) [default today {date.today().isoformat()}]: ").strip()
    if dt_in:
        try:
            d = datetime.fromisoformat(dt_in).date()
        except Exception:
            print(color("Bad date format.", "1;31"))
            pause()
            return
    else:
        d = date.today()
    present_raw = input("Present? (y/n) [default y]: ").strip().lower()
    present = True if present_raw in ("", "y", "yes") else False
    data = load_data()
    rec = {"id": gen_id(), "subjectId": subj["id"], "date": d.isoformat(), "present": present, "createdAt": now_iso()}
    data.setdefault("attendance", []).append(rec)
    save_data(data)
    print(color(f"Recorded {'Present' if present else 'Absent'} for {subj['name']} on {d.isoformat()}", "1;32"))
    pause()

def compute_attendance_percent(subject_id: str) -> float:
    d = load_data()
    rows = [r for r in d.get("attendance", []) if r["subjectId"] == subject_id]
    if not rows:
        return 100.0
    present = sum(1 for r in rows if r["present"])
    return (present / len(rows)) * 100.0

def attendance_report():
    header("Attendance Report")
    d = load_data()
    subs = d.get("subjects", [])
    if not subs:
        print(color("No subjects.", "1;33"))
    else:
        for s in subs:
            pct = compute_attendance_percent(s["id"])
            status = color("OK", "1;32") if pct >= 75 else color("LOW (<75%)", "1;31")
            print(f"- {s['name']} ({s.get('code','')}) : {pct:.1f}% -> {status}")
    pause()

def add_assignment():
    header("Add Assignment")
    subj = choose_subject("Select subject to add assignment to (or press Enter to make unassigned):")
    subjectId = subj["id"] if subj else None
    title = input("Title: ").strip()
    if not title:
        print(color("Title cannot be empty.", "1;31"))
        pause()
        return
    description = input("Description (optional): ").strip()
    due = input("Due date (YYYY-MM-DD or YYYY-MM-DDTHH:MM) [optional]: ").strip()
    # validate date if provided
    if due:
        try:
            _ = datetime.fromisoformat(due)
        except Exception:
            print(color("Bad date format. Use YYYY-MM-DD or ISO datetime.", "1;31"))
            pause()
            return
    assignment = {
        "id": gen_id(),
        "subjectId": subjectId,
        "title": title,
        "description": description,
        "dueAt": due or None,
        "createdAt": now_iso(),
        "completed": False
    }
    data = load_data()
    data.setdefault("assignments", []).append(assignment)
    save_data(data)
    print(color("Assignment added.", "1;32"))
    pause()

def list_assignments(upcoming_days: int = 0):
    header("Assignments")
    data = load_data()
    assigns = data.get("assignments", [])
    now = datetime.now()
    if upcoming_days > 0:
        window = now + timedelta(days=upcoming_days)
        assigns = [a for a in assigns if a.get("dueAt") and now <= datetime.fromisoformat(a["dueAt"]) <= window]
    if not assigns:
        print(color("No assignments found.", "1;33"))
    else:
        for a in sorted(assigns, key=lambda x: x.get("dueAt") or ""):
            subj = next((s for s in data.get("subjects", []) if s["id"] == a.get("subjectId")), None)
            subj_name = subj["name"] if subj else "No subject"
            due_str = format_datetime_iso(a.get("dueAt"))
            status = color("Done", "1;32") if a.get("completed") else color("Pending", "1;33")
            print(color(f"- {a['title']} [{subj_name}] (id:{a['id']})", "1;36"))
            print(f"   Due: {due_str}   Status: {status}")
            if a.get("description"):
                print(f"   {a['description']}")
            print()
    pause()

def toggle_assignment_completion():
    header("Toggle Assignment Completion")
    data = load_data()
    assigns = data.get("assignments", [])
    if not assigns:
        print(color("No assignments.", "1;33"))
        pause()
        return
    for i, a in enumerate(assigns, start=1):
        subj = next((s for s in data.get("subjects", []) if s["id"] == a.get("subjectId")), None)
        subj_name = subj["name"] if subj else "No subject"
        status = "Done" if a.get("completed") else "Pending"
        print(f"{i}. {a['title']} [{subj_name}] - {status}")
    choice = input("Enter number to toggle: ").strip()
    if not choice.isdigit():
        print(color("Invalid input.", "1;31"))
        pause()
        return
    n = int(choice)
    if n < 1 or n > len(assigns):
        print(color("Out of range.", "1;31"))
        pause()
        return
    assigns[n-1]["completed"] = not assigns[n-1].get("completed", False)
    save_data(data)
    print(color("Toggled assignment status.", "1;32"))
    pause()

def get_todays_classes():
    data = load_data()
    weekday_name = WEEKDAYS[(date.today().weekday() + 1) % 7]
    out = []
    for s in data.get("subjects", []):
        for slot in s.get("schedule", []):
            if slot.get("day") == weekday_name:
                out.append({"subject": s, "slot": slot})
    return out

def dashboard():
    header("Dashboard")
    data = load_data()
    # Today's classes
    classes = get_todays_classes()
    if classes:
        print(color("Today's classes:", "1;33"))
        for c in classes:
            s = c["subject"]
            slot = c["slot"]
            loc = f" @ {slot['location']}" if slot.get("location") else ""
            print(f"- {s['name']} {slot['start']}-{slot['end']}{loc}")
    else:
        print(color("No classes scheduled for today.", "1;33"))
    print()
    # Upcoming assignments (7 days)
    now = datetime.now()
    upcoming = []
    for a in data.get("assignments", []):
        if a.get("dueAt"):
            try:
                d = datetime.fromisoformat(a["dueAt"])
            except Exception:
                continue
            if now <= d <= now + timedelta(days=7):
                upcoming.append((d,a))
    upcoming.sort(key=lambda x: x[0])
    if upcoming:
        print(color("Upcoming assignments (next 7 days):", "1;33"))
        for d,a in upcoming:
            subj = next((s for s in data.get("subjects", []) if s["id"] == a.get("subjectId")), None)
            subj_name = subj["name"] if subj else "No subject"
            print(f"- {a['title']} [{subj_name}] due {d.strftime(DATETIME_FMT)}")
    else:
        print(color("No upcoming assignments in the next 7 days.", "2;37"))
    print()
    # Attendance alerts
    print(color("Attendance alerts (below 75%):", "1;33"))
    alerts = []
    for s in data.get("subjects", []):
        pct = compute_attendance_percent(s["id"])
        if pct < 75.0:
            alerts.append((s,pct))
    if alerts:
        for s,pct in alerts:
            print(f"- {s['name']}: {pct:.1f}% (Below 75%)")
    else:
        print(color("No attendance alerts. You're safe.", "1;32"))
    pause()

def export_data():
    header("Export Data")
    data = load_data()
    target = input("Filename to export to [default export_<timestamp>.json]: ").strip()
    if not target:
        target = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(target, "w") as f:
        json.dump(data, f, indent=2)
    print(color(f"Exported to {target}", "1;32"))
    pause()

def import_data():
    header("Import Data (replaces current data)")
    fname = input("Path to JSON file to import: ").strip()
    if not fname or not os.path.exists(fname):
        print(color("File not found.", "1;31"))
        pause()
        return
    backup_data()
    with open(fname, "r") as f:
        payload = json.load(f)
    save_data(payload)
    print(color("Imported data and backed up previous data.json", "1;32"))
    pause()

def init_demo():
    header("Initialize Demo Data")
    demo_subs = [
        {"id": gen_id(), "name": "Engineering Mechanics", "code": "ME101", "prof": "Dr. Seenu", "schedule": [{"day":"Mon","start":"09:00","end":"10:30","location":"Room 101"}], "createdAt": now_iso()},
        {"id": gen_id(), "name": "Calculus", "code": "MA101", "prof": "Dr. Roy", "schedule": [{"day":"Tue","start":"11:00","end":"12:30"}], "createdAt": now_iso()},
    ]
    data = {"subjects": demo_subs, "attendance": [], "assignments": [], "meta": {"createdAt": now_iso()}}
    save_data(data)
    print(color("Demo data created.", "1;32"))
    pause()

def backup_now():
    header("Backup Data")
    dest = backup_data()
    print(color(f"Backup created at {dest}", "1;32"))
    pause()

# ---------- Menu ----------
def main_menu():
    while True:
        header("University Planner — Menu")
        print("1) Add Subject")
        print("2) List Subjects")
        print("3) Record Attendance")
        print("4) Attendance Report")
        print("5) Add Assignment")
        print("6) List Assignments")
        print("7) Toggle Assignment Completion")
        print("8) Dashboard")
        print("9) Export Data")
        print("10) Import Data")
        print("11) Backup Data")
        print("12) Init Demo Data")
        print("0) Exit")
        choice = input("\nChoose an option: ").strip()
        if choice == "1":
            add_subject()
        elif choice == "2":
            list_subjects()
        elif choice == "3":
            record_attendance()
        elif choice == "4":
            attendance_report()
        elif choice == "5":
            add_assignment()
        elif choice == "6":
            list_assignments()
        elif choice == "7":
            toggle_assignment_completion()
        elif choice == "8":
            dashboard()
        elif choice == "9":
            export_data()
        elif choice == "10":
            import_data()
        elif choice == "11":
            backup_now()
        elif choice == "12":
            init_demo()
        elif choice == "0":
            print(color("Goodbye.", "1;34"))
            break
        else:
            print(color("Invalid option. Enter a number from the menu.", "1;31"))
            pause()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)

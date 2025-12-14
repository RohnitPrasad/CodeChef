#!/usr/bin/env python3
"""
University Planner - Tkinter GUI (single file)
Save as planner_gui.py and run: python3 planner_gui.py
No external dependencies.
"""

import json
import os
import shutil
import sys
import uuid
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

# ---------- Config ----------
DATA_FILE = "data.json"
BACKUP_DIR = "backups"
WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M"

# ---------- Storage ----------
def now_iso() -> str:
    return datetime.now().isoformat()

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

def backup_data() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"data_backup_{ts}.json")
    shutil.copy2(DATA_FILE, dest)
    return dest

def list_backups() -> List[str]:
    if not os.path.isdir(BACKUP_DIR):
        return []
    files = sorted(os.listdir(BACKUP_DIR))
    return [os.path.join(BACKUP_DIR, f) for f in files]

def gen_id() -> str:
    return uuid.uuid4().hex[:10]

# ---------- Utilities ----------
def parse_schedule_string(s: str) -> List[Dict[str, str]]:
    items = []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    for p in parts:
        loc = ""
        if " " in p:
            p, loc = p.split(" ", 1)
            loc = loc.strip()
        try:
            day, times = p.split("@")
            day = day.strip()
            if day not in WEEKDAYS:
                raise ValueError(f"Unknown weekday: {day}. Use one of: {', '.join(WEEKDAYS)}")
            start, end = times.split("-")
            items.append({"day": day, "start": start.strip(), "end": end.strip(), "location": loc})
        except Exception:
            raise ValueError("Bad schedule piece. Example: Mon@09:00-10:30")
    return items

def format_datetime_iso(s: Optional[str]) -> str:
    if not s:
        return "N/A"
    try:
        dt = datetime.fromisoformat(s)
        if dt.time().hour != 0 or dt.time().minute != 0 or dt.time().second != 0:
            return dt.strftime(DATETIME_FMT)
        return dt.strftime(DATE_FMT)
    except Exception:
        return s

def compute_attendance_percent(subject_id: str) -> float:
    d = load_data()
    rows = [r for r in d.get("attendance", []) if r["subjectId"] == subject_id]
    if not rows:
        return 100.0
    present = sum(1 for r in rows if r["present"])
    return (present / len(rows)) * 100.0

# ---------- GUI App ----------
class PlannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("University Planner")
        self.geometry("900x600")
        self.minsize(780, 480)

        # layout: left nav frame, right content frame
        self.left_frame = ttk.Frame(self, width=220)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.right_frame = ttk.Frame(self)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_nav()
        self.content_widgets: Dict[str, tk.Widget] = {}
        self.current_screen = None

        # initial screen
        self.show_dashboard()

    # ---------- Navigation ----------
    def _create_nav(self):
        pad = {"padx": 8, "pady": 6}

        ttk.Label(self.left_frame, text="Planner", font=("TkDefaultFont", 14, "bold")).pack(pady=(10,6))

        btns = [
            ("Dashboard", self.show_dashboard),
            ("Subjects", self.show_subjects),
            ("Add Subject", self.add_subject_dialog),
            ("Attendance", self.show_attendance),
            ("Record Attendance", self.record_attendance_dialog),
            ("Assignments", self.show_assignments),
            ("Add Assignment", self.add_assignment_dialog),
            ("Backup Data", self.backup_now),
            ("Import Data", self.import_data),
            ("Export Data", self.export_data),
            ("Init Demo Data", self.init_demo),
            ("Exit", self.on_exit),
        ]

        for (text, cmd) in btns:
            b = ttk.Button(self.left_frame, text=text, command=cmd)
            b.pack(fill=tk.X, **pad)

        # show backups list
        ttk.Separator(self.left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(self.left_frame, text="Backups", font=("TkDefaultFont", 10, "bold")).pack()
        self.backup_listbox = tk.Listbox(self.left_frame, height=6)
        self.backup_listbox.pack(fill=tk.X, padx=8, pady=4)
        self._refresh_backups()
        backup_btn_frame = ttk.Frame(self.left_frame)
        backup_btn_frame.pack(fill=tk.X, padx=8)
        ttk.Button(backup_btn_frame, text="Refresh", command=self._refresh_backups).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(backup_btn_frame, text="Restore", command=self.restore_selected_backup).pack(side=tk.LEFT, expand=True, fill=tk.X)

    def _clear_right(self):
        for child in self.right_frame.winfo_children():
            child.destroy()
        self.content_widgets.clear()

    def _refresh_backups(self):
        self.backup_listbox.delete(0, tk.END)
        for b in list_backups():
            self.backup_listbox.insert(tk.END, b)

    def restore_selected_backup(self):
        sel = self.backup_listbox.curselection()
        if not sel:
            messagebox.showinfo("Restore", "Select a backup first.")
            return
        path = self.backup_listbox.get(sel[0])
        if not os.path.exists(path):
            messagebox.showerror("Restore", "Backup file not found.")
            self._refresh_backups()
            return
        if messagebox.askyesno("Confirm Restore", f"Restore from {os.path.basename(path)}? This will replace current data."):
            backup_data()
            shutil.copy2(path, DATA_FILE)
            messagebox.showinfo("Restore", "Restore complete.")
            self._refresh_backups()

    # ---------- Screens ----------
    def show_dashboard(self):
        self._clear_right()
        frame = self.right_frame
        ttk.Label(frame, text="Dashboard", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W, pady=(10,6), padx=10)

        data = load_data()

        # Today's classes
        today_frame = ttk.LabelFrame(frame, text="Today's classes")
        today_frame.pack(fill=tk.X, padx=10, pady=6)
        classes = self.get_todays_classes()
        if classes:
            for c in classes:
                s = c["subject"]
                slot = c["slot"]
                loc = f" @ {slot['location']}" if slot.get("location") else ""
                ttk.Label(today_frame, text=f"{s['name']} — {slot['start']}-{slot['end']}{loc}").pack(anchor=tk.W, padx=8, pady=2)
        else:
            ttk.Label(today_frame, text="No classes scheduled for today.").pack(anchor=tk.W, padx=8, pady=4)

        # upcoming assignments
        assign_frame = ttk.LabelFrame(frame, text="Upcoming assignments (7 days)")
        assign_frame.pack(fill=tk.X, padx=10, pady=6)
        now_dt = datetime.now()
        upcoming = []
        for a in data.get("assignments", []):
            if a.get("dueAt"):
                try:
                    d = datetime.fromisoformat(a["dueAt"])
                except Exception:
                    continue
                if now_dt <= d <= now_dt + timedelta(days=7):
                    upcoming.append((d, a))
        upcoming.sort(key=lambda x: x[0])
        if upcoming:
            for d, a in upcoming:
                subj = next((s for s in data.get("subjects", []) if s["id"] == a.get("subjectId")), None)
                subj_name = subj["name"] if subj else "No subject"
                ttk.Label(assign_frame, text=f"{a['title']} [{subj_name}] due {d.strftime(DATETIME_FMT)}").pack(anchor=tk.W, padx=8, pady=2)
        else:
            ttk.Label(assign_frame, text="No upcoming assignments in the next 7 days.").pack(anchor=tk.W, padx=8, pady=4)

        # attendance alerts
        attend_frame = ttk.LabelFrame(frame, text="Attendance alerts (<75%)")
        attend_frame.pack(fill=tk.X, padx=10, pady=6)
        alerts = []
        for s in data.get("subjects", []):
            pct = compute_attendance_percent(s["id"])
            if pct < 75.0:
                alerts.append((s, pct))
        if alerts:
            for s, pct in alerts:
                ttk.Label(attend_frame, text=f"{s['name']}: {pct:.1f}%").pack(anchor=tk.W, padx=8, pady=2)
        else:
            ttk.Label(attend_frame, text="No attendance alerts. You're safe.").pack(anchor=tk.W, padx=8, pady=4)

    def show_subjects(self):
        self._clear_right()
        frame = self.right_frame
        ttk.Label(frame, text="Subjects", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W, pady=(10,6), padx=10)

        data = load_data()
        cols = ("#1", "#2", "#3")
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("#1", text="Name")
        tree.heading("#2", text="Code")
        tree.heading("#3", text="Professor")
        tree.column("#1", width=260)
        tree.column("#2", width=80)
        tree.column("#3", width=180)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.content_widgets["subjects_tree"] = tree

        for s in data.get("subjects", []):
            tree.insert("", tk.END, iid=s["id"], values=(s["name"], s.get("code", ""), s.get("prof", "")))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(btn_frame, text="Add", command=self.add_subject_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Edit", command=self.edit_subject_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self.delete_subject_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="View Schedule", command=self.view_subject_schedule).pack(side=tk.LEFT, padx=4)

    def add_subject_dialog(self):
        d = simpledialog.Dialog(self, title="Add Subject")
        # We'll use our own simple dialog with inputs via Toplevel because simpledialog.Dialog is abstract;
        # implement using a custom Toplevel.
        self._subject_form(initial=None)

    def _subject_form(self, initial: Optional[Dict[str, Any]]):
        top = tk.Toplevel(self)
        top.transient(self)
        top.grab_set()
        is_edit = bool(initial)
        top.title("Edit Subject" if is_edit else "Add Subject")
        top.geometry("480x300")

        lbl_name = ttk.Label(top, text="Subject name:")
        lbl_name.pack(anchor=tk.W, padx=10, pady=(10,0))
        ent_name = ttk.Entry(top)
        ent_name.pack(fill=tk.X, padx=10)

        lbl_code = ttk.Label(top, text="Code (optional):")
        lbl_code.pack(anchor=tk.W, padx=10, pady=(8,0))
        ent_code = ttk.Entry(top)
        ent_code.pack(fill=tk.X, padx=10)

        lbl_prof = ttk.Label(top, text="Professor (optional):")
        lbl_prof.pack(anchor=tk.W, padx=10, pady=(8,0))
        ent_prof = ttk.Entry(top)
        ent_prof.pack(fill=tk.X, padx=10)

        lbl_sched = ttk.Label(top, text="Schedule (comma separated, e.g. Mon@09:00-10:30,Tue@11:00-12:30 Room201):")
        lbl_sched.pack(anchor=tk.W, padx=10, pady=(8,0))
        ent_sched = ttk.Entry(top)
        ent_sched.pack(fill=tk.X, padx=10)

        if initial:
            ent_name.insert(0, initial.get("name", ""))
            ent_code.insert(0, initial.get("code", ""))
            ent_prof.insert(0, initial.get("prof", ""))
            # show schedule as original format if present
            if initial.get("schedule"):
                parts = []
                for sch in initial["schedule"]:
                    part = f"{sch['day']}@{sch['start']}-{sch['end']}"
                    if sch.get("location"):
                        part += " " + sch["location"]
                    parts.append(part)
                ent_sched.insert(0, ",".join(parts))

        def on_save():
            name = ent_name.get().strip()
            if not name:
                messagebox.showerror("Validation", "Name cannot be empty.")
                return
            code = ent_code.get().strip()
            prof = ent_prof.get().strip()
            schedule_raw = ent_sched.get().strip()
            schedule = []
            if schedule_raw:
                try:
                    schedule = parse_schedule_string(schedule_raw)
                except Exception as e:
                    messagebox.showerror("Schedule", f"Error parsing schedule: {e}")
                    return
            data = load_data()
            if is_edit and initial:
                # mutate existing subject
                for s in data.get("subjects", []):
                    if s["id"] == initial["id"]:
                        s["name"] = name
                        s["code"] = code
                        s["prof"] = prof
                        s["schedule"] = schedule
                        break
                save_data(data)
                messagebox.showinfo("Edit", "Subject updated.")
            else:
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
                messagebox.showinfo("Add", "Subject added.")
            top.destroy()
            self.show_subjects()

        btn_frame = ttk.Frame(top)
        btn_frame.pack(fill=tk.X, padx=10, pady=12)
        ttk.Button(btn_frame, text="Save", command=on_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=6)

    def edit_subject_dialog(self):
        tree: ttk.Treeview = self.content_widgets.get("subjects_tree")  # type: ignore
        if not tree:
            messagebox.showinfo("Edit Subject", "Open Subjects screen first.")
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Edit Subject", "Select a subject to edit.")
            return
        subj_id = sel[0]
        data = load_data()
        subj = next((s for s in data.get("subjects", []) if s["id"] == subj_id), None)
        if not subj:
            messagebox.showerror("Edit Subject", "Subject not found.")
            return
        self._subject_form(initial=subj)

    def delete_subject_dialog(self):
        tree: ttk.Treeview = self.content_widgets.get("subjects_tree")  # type: ignore
        if not tree:
            messagebox.showinfo("Delete Subject", "Open Subjects screen first.")
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Delete Subject", "Select a subject to delete.")
            return
        subj_id = sel[0]
        data = load_data()
        subj = next((s for s in data.get("subjects", []) if s["id"] == subj_id), None)
        if not subj:
            messagebox.showerror("Delete Subject", "Subject not found.")
            return
        if messagebox.askyesno("Confirm", f"Delete subject '{subj['name']}' and all related attendance/assignments?"):
            data["subjects"] = [x for x in data.get("subjects", []) if x["id"] != subj_id]
            data["attendance"] = [r for r in data.get("attendance", []) if r.get("subjectId") != subj_id]
            data["assignments"] = [a for a in data.get("assignments", []) if a.get("subjectId") != subj_id]
            save_data(data)
            messagebox.showinfo("Delete", "Deleted subject and related records.")
            self.show_subjects()

    def view_subject_schedule(self):
        tree: ttk.Treeview = self.content_widgets.get("subjects_tree")  # type: ignore
        if not tree:
            messagebox.showinfo("View Schedule", "Open Subjects screen first.")
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("View Schedule", "Select a subject first.")
            return
        subj_id = sel[0]
        data = load_data()
        subj = next((s for s in data.get("subjects", []) if s["id"] == subj_id), None)
        if not subj:
            messagebox.showerror("View Schedule", "Subject not found.")
            return
        msg = f"Schedule for {subj['name']}:\n\n"
        if subj.get("schedule"):
            for sch in subj["schedule"]:
                loc = f" @ {sch['location']}" if sch.get("location") else ""
                msg += f"- {sch['day']} {sch['start']}-{sch['end']}{loc}\n"
        else:
            msg += "No schedule set."
        messagebox.showinfo("Schedule", msg)

    # ---------- Attendance ----------
    def show_attendance(self):
        self._clear_right()
        frame = self.right_frame
        ttk.Label(frame, text="Attendance", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W, pady=(10,6), padx=10)

        data = load_data()
        cols = ("#1", "#2", "#3")
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("#1", text="Subject")
        tree.heading("#2", text="Date")
        tree.heading("#3", text="Present")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.content_widgets["attendance_tree"] = tree

        for r in data.get("attendance", []):
            subj = next((s for s in data.get("subjects", []) if s["id"] == r["subjectId"]), None)
            subj_name = subj["name"] if subj else "Unknown"
            tree.insert("", tk.END, iid=r["id"], values=(subj_name, r["date"], "Yes" if r["present"] else "No"))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(btn_frame, text="Record", command=self.record_attendance_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Report", command=self.attendance_report).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self.delete_attendance_entry).pack(side=tk.LEFT, padx=4)

    def record_attendance_dialog(self):
        # choose subject then date and present Y/N
        data = load_data()
        subs = data.get("subjects", [])
        if not subs:
            messagebox.showinfo("Record Attendance", "No subjects present. Add subjects first.")
            return
        choices = [f"{i+1}. {s['name']}" for i, s in enumerate(subs)]
        sel = simpledialog.askstring("Record Attendance", "Select subject number:\n" + "\n".join(choices))
        if not sel:
            return
        if not sel.isdigit():
            messagebox.showerror("Input", "Invalid input.")
            return
        n = int(sel)
        if n < 1 or n > len(subs):
            messagebox.showerror("Input", "Number out of range.")
            return
        subj = subs[n - 1]
        dt_in = simpledialog.askstring("Date", f"Date (YYYY-MM-DD) [default {date.today().isoformat()}]:")
        if dt_in:
            try:
                d = datetime.fromisoformat(dt_in).date()
            except Exception:
                messagebox.showerror("Date", "Bad date format.")
                return
        else:
            d = date.today()
        present_raw = simpledialog.askstring("Present", "Present? (y/n) [default y]:")
        present = True if (present_raw is None or present_raw.strip().lower() in ("", "y", "yes")) else False
        rec = {"id": gen_id(), "subjectId": subj["id"], "date": d.isoformat(), "present": present, "createdAt": now_iso()}
        data.setdefault("attendance", []).append(rec)
        save_data(data)
        messagebox.showinfo("Attendance", f"Recorded {'Present' if present else 'Absent'} for {subj['name']} on {d.isoformat()}")
        self.show_attendance()

    def delete_attendance_entry(self):
        tree: ttk.Treeview = self.content_widgets.get("attendance_tree")  # type: ignore
        if not tree:
            messagebox.showinfo("Delete Attendance", "Open Attendance screen first.")
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Delete Attendance", "Select an entry to delete.")
            return
        entry_id = sel[0]
        data = load_data()
        rec = next((r for r in data.get("attendance", []) if r["id"] == entry_id), None)
        if not rec:
            messagebox.showerror("Delete", "Entry not found.")
            return
        if messagebox.askyesno("Confirm", "Delete selected attendance entry?"):
            data["attendance"] = [r for r in data.get("attendance", []) if r["id"] != entry_id]
            save_data(data)
            messagebox.showinfo("Delete", "Deleted.")
            self.show_attendance()

    def attendance_report(self):
        data = load_data()
        subs = data.get("subjects", [])
        if not subs:
            messagebox.showinfo("Attendance Report", "No subjects.")
            return
        msg_lines = []
        for s in subs:
            pct = compute_attendance_percent(s["id"])
            status = "OK" if pct >= 75 else "LOW (<75%)"
            msg_lines.append(f"- {s['name']} ({s.get('code','')}) : {pct:.1f}% -> {status}")
        messagebox.showinfo("Attendance Report", "\n".join(msg_lines))

    # ---------- Assignments ----------
    def show_assignments(self):
        self._clear_right()
        frame = self.right_frame
        ttk.Label(frame, text="Assignments", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W, pady=(10,6), padx=10)

        data = load_data()
        cols = ("#1", "#2", "#3", "#4")
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("#1", text="Title")
        tree.heading("#2", text="Subject")
        tree.heading("#3", text="Due")
        tree.heading("#4", text="Status")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.content_widgets["assign_tree"] = tree

        for a in data.get("assignments", []):
            subj = next((s for s in data.get("subjects", []) if s["id"] == a.get("subjectId")), None)
            subj_name = subj["name"] if subj else "No subject"
            due_str = format_datetime_iso(a.get("dueAt"))
            status_str = "Done" if a.get("completed") else "Pending"
            tree.insert("", tk.END, iid=a["id"], values=(a["title"], subj_name, due_str, status_str))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(btn_frame, text="Add", command=self.add_assignment_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Toggle Done", command=self.toggle_assignment_completion).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self.delete_assignment).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Upcoming 7d", command=lambda: self.list_assignments(upcoming_days=7)).pack(side=tk.LEFT, padx=4)

    def add_assignment_dialog(self):
        # choose subject optionally
        data = load_data()
        subs = data.get("subjects", [])
        subj_choice = None
        if subs:
            choices = [f"{i+1}. {s['name']}" for i, s in enumerate(subs)]
            sel = simpledialog.askstring("Assignment", "Select subject number (or leave blank for none):\n" + "\n".join(choices))
            if sel and sel.isdigit():
                n = int(sel)
                if 1 <= n <= len(subs):
                    subj_choice = subs[n-1]
        title = simpledialog.askstring("Title", "Title:")
        if not title:
            messagebox.showerror("Input", "Title required.")
            return
        description = simpledialog.askstring("Description", "Description (optional):")
        due = simpledialog.askstring("Due (YYYY-MM-DD or YYYY-MM-DDTHH:MM)", "Due date (optional):")
        if due:
            try:
                _ = datetime.fromisoformat(due)
            except Exception:
                messagebox.showerror("Date", "Bad date format.")
                return
        assignment = {
            "id": gen_id(),
            "subjectId": subj_choice["id"] if subj_choice else None,
            "title": title,
            "description": description or "",
            "dueAt": due or None,
            "createdAt": now_iso(),
            "completed": False
        }
        data.setdefault("assignments", []).append(assignment)
        save_data(data)
        messagebox.showinfo("Assignment", "Added.")
        self.show_assignments()

    def toggle_assignment_completion(self):
        tree: ttk.Treeview = self.content_widgets.get("assign_tree")  # type: ignore
        if not tree:
            messagebox.showinfo("Toggle", "Open Assignments first.")
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Toggle", "Select an assignment.")
            return
        aid = sel[0]
        data = load_data()
        for a in data.get("assignments", []):
            if a["id"] == aid:
                a["completed"] = not a.get("completed", False)
                break
        save_data(data)
        messagebox.showinfo("Toggle", "Toggled status.")
        self.show_assignments()

    def delete_assignment(self):
        tree: ttk.Treeview = self.content_widgets.get("assign_tree")  # type: ignore
        if not tree:
            messagebox.showinfo("Delete", "Open Assignments first.")
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select an assignment.")
            return
        aid = sel[0]
        data = load_data()
        a = next((x for x in data.get("assignments", []) if x["id"] == aid), None)
        if not a:
            messagebox.showerror("Delete", "Assignment not found.")
            return
        if messagebox.askyesno("Confirm", f"Delete assignment '{a['title']}'?"):
            data["assignments"] = [x for x in data.get("assignments", []) if x["id"] != aid]
            save_data(data)
            messagebox.showinfo("Delete", "Deleted.")
            self.show_assignments()

    def list_assignments(self, upcoming_days: int = 0):
        data = load_data()
        assigns = data.get("assignments", [])
        now_dt = datetime.now()
        if upcoming_days > 0:
            window = now_dt + timedelta(days=upcoming_days)
            assigns = [a for a in assigns if a.get("dueAt") and now_dt <= datetime.fromisoformat(a["dueAt"]) <= window]
        if not assigns:
            messagebox.showinfo("Assignments", "No assignments found.")
            return
        lines = []
        for a in sorted(assigns, key=lambda x: x.get("dueAt") or ""):
            subj = next((s for s in data.get("subjects", []) if s["id"] == a.get("subjectId")), None)
            subj_name = subj["name"] if subj else "No subject"
            due_str = format_datetime_iso(a.get("dueAt"))
            status = "Done" if a.get("completed") else "Pending"
            lines.append(f"- {a['title']} [{subj_name}] due: {due_str} status: {status}")
            if a.get("description"):
                lines.append(f"   {a['description']}")
        messagebox.showinfo("Assignments", "\n".join(lines))

    # ---------- Misc ----------
    def get_todays_classes(self) -> List[Dict[str, Any]]:
        data = load_data()
        # use %a to get short weekday name like Mon, Tue
        weekday_name = datetime.today().strftime("%a")
        out = []
        for s in data.get("subjects", []):
            for slot in s.get("schedule", []):
                if slot.get("day") == weekday_name:
                    out.append({"subject": s, "slot": slot})
        return out

    def export_data(self):
        target = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialfile=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        if not target:
            return
        data = load_data()
        with open(target, "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Export", f"Exported to {target}")

    def import_data(self):
        fname = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not fname:
            return
        if not os.path.exists(fname):
            messagebox.showerror("Import", "File not found.")
            return
        if not messagebox.askyesno("Confirm Import", "Import will replace current data.json (a backup will be created). Continue?"):
            return
        backup_data()
        with open(fname, "r") as f:
            payload = json.load(f)
        save_data(payload)
        messagebox.showinfo("Import", "Imported data and backed up previous data.json")
        # refresh UI if needed
        self.show_dashboard()

    def backup_now(self):
        dest = backup_data()
        messagebox.showinfo("Backup", f"Backup created at {dest}")
        self._refresh_backups()

    def init_demo(self):
        if not messagebox.askyesno("Demo Data", "Initialize demo data? This will replace current data.json (a backup will be created)."):
            return
        demo_subs = [
            {"id": gen_id(), "name": "Engineering Mechanics", "code": "ME101", "prof": "Dr. Seenu", "schedule": [{"day": "Mon", "start": "09:00", "end": "10:30", "location": "Room 101"}], "createdAt": now_iso()},
            {"id": gen_id(), "name": "Calculus", "code": "MA101", "prof": "Dr. Roy", "schedule": [{"day": "Tue", "start": "11:00", "end": "12:30"}], "createdAt": now_iso()},
        ]
        data = {"subjects": demo_subs, "attendance": [], "assignments": [], "meta": {"createdAt": now_iso()}}
        backup_data()
        save_data(data)
        messagebox.showinfo("Demo", "Demo data created (previous data backed up).")
        self.show_dashboard()
        self._refresh_backups()

    def on_exit(self):
        if messagebox.askyesno("Exit", "Exit application?"):
            self.destroy()
            sys.exit(0)

# ---------- Run ----------
if __name__ == "__main__":
    app = PlannerApp()
    app.mainloop()
"""Repeatable fictional fixtures. Run `python -m app.seed [--reset]` after migrations.

--reset deletes only the two known seeded clinics' owned records, preserving all other clinics.
Run from an operator shell; it is deliberately not exposed as a public API.
"""
import argparse
from datetime import date, datetime, time, timedelta
from uuid import NAMESPACE_DNS, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import password_hasher
from .config import get_settings
from .db import SessionLocal
from .models import Appointment, AuditEvent, AuthSession, Clinic, Encounter, Generation, NoteVersion, Patient, Task, TranscriptVersion, User
from .services import audit, snapshot


def fixture_id(name: str) -> str:
    return str(uuid5(NAMESPACE_DNS, f"clinicflow.demo.{name}"))


VISITS = [
    ("Avery Morgan", 1992, "Rash review", "Symptoms: Itchy rash on both forearms for two weeks.\nHistory: No new medications. No known drug allergies.\nFindings: Dry red patches on both forearms; no drainage.\nPlan: The clinician advised continuing the existing moisturizer.\nFollow-up: Schedule a rash review in two weeks."),
    ("Jordan Lee", 1985, "Acne follow-up", "Symptoms: Fewer breakouts over the past month.\nHistory: Reports using the previously prescribed cream; dose not documented.\nFindings: A few papules on the cheeks.\nPlan: The clinician stated to continue the current routine.\nTask: Call to check progress in four weeks."),
    ("Samira Patel", 1978, "Skin check", "Symptoms: No itching, bleeding, or pain.\nHistory: Requests a routine skin check.\nFindings: The clinician documented no concerning change in the examined spot.\nPlan: No follow-up appointment requested."),
    ("Theo Bennett", 2000, "Dry skin consultation", "Symptoms: Dry skin on the hands after frequent washing.\nHistory: No fever.\nFindings: Dry skin with superficial cracking.\nPlan: The clinician discussed the patient's current moisturizer.\nFollow-up: Arrange a review next month."),
    ("Priya Shah", 1996, "Scalp concern", "Symptoms: Intermittent scalp itching for one month.\nHistory: No prior scalp treatment reported.\nFindings: Mild visible scaling.\nPlan: The clinician explained the documented findings.\nTask: Send the existing visit summary."),
    ("Elliot Brooks", 1969, "Routine review", "Symptoms: Rash improving; no pain.\nHistory: Reports no medication changes since the last visit.\nFindings: Small dry patch on the left elbow.\nPlan: Continue the clinician's previously documented plan.\nFollow-up: Book a review in three weeks."),
]


def seed(db: Session, password: str, reset: bool = False):
    if len(password) < 12:
        raise ValueError("Set DEMO_PASSWORD to at least 12 characters before seeding.")
    clinic_ids = [fixture_id("clinic-willow"), fixture_id("clinic-other")]
    if reset:
        user_ids = select(User.id).where(User.clinic_id.in_(clinic_ids))
        db.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))
        for model in (AuditEvent, Task, NoteVersion, Generation, TranscriptVersion, Encounter, Appointment, Patient, User, Clinic):
            field = model.id if model is Clinic else model.clinic_id
            db.execute(delete(model).where(field.in_(clinic_ids)))
        db.flush()
    if db.get(Clinic, clinic_ids[0]) is not None:
        return False
    password_hash = password_hasher.hash(password)
    now = datetime.combine(date.today(), time(9), tzinfo=ZoneInfo("Asia/Kolkata"))
    for clinic_index, (name, suffix) in enumerate((("Willow Dermatology", "clinicflow"), ("Cedar Skin Clinic", "other"))):
        clinic_id = clinic_ids[clinic_index]
        db.add(Clinic(id=clinic_id, name=name, timezone="Asia/Kolkata"))
        db.flush()
        doctor = User(id=fixture_id(f"doctor-{suffix}"), clinic_id=clinic_id, name="Dr. Maya Chen" if not clinic_index else "Dr. Alex Rowan",
                      email=f"doctor@{suffix}.demo", password_hash=password_hash, role="doctor")
        staff = User(id=fixture_id(f"staff-{suffix}"), clinic_id=clinic_id, name="Jamie Rivera" if not clinic_index else "Casey Hart",
                     email=f"staff@{suffix}.demo", password_hash=password_hash, role="staff")
        db.add_all([doctor, staff])
        db.flush()
        for index, (patient_name, year, reason, transcript) in enumerate(VISITS if not clinic_index else VISITS[:2]):
            patient = Patient(id=fixture_id(f"patient-{suffix}-{index}"), clinic_id=clinic_id,
                              name=patient_name if not clinic_index else f"Cedar {patient_name}", date_of_birth=date(year, 3, 14))
            db.add(patient)
            db.flush()
            appointment = Appointment(id=fixture_id(f"appointment-{suffix}-{index}"), clinic_id=clinic_id,
                                      patient_id=patient.id, scheduled_at=now + timedelta(minutes=index * 30), reason=reason)
            db.add(appointment)
            db.flush()
            encounter = Encounter(id=fixture_id(f"encounter-{suffix}-{index}"), clinic_id=clinic_id,
                                  appointment_id=appointment.id, transcript=transcript, transcript_revision=1)
            db.add(encounter)
            db.flush()
            db.add(TranscriptVersion(clinic_id=clinic_id, encounter_id=encounter.id, revision=1, text=transcript))
            snapshot(db, encounter, doctor, "seeded")
            audit(db, encounter, doctor, "demo_seeded")
    db.commit()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Restore only the two fictional demo clinics and revoke their sessions.")
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            changed = seed(db, get_settings().demo_password, reset=args.reset)
        print("Fictional demo clinics seeded." if changed else "Demo clinics already exist. Use --reset to restore the walkthrough.")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

from datetime import datetime, timezone

from database import (
    PublishAttempt,
    ScheduleSlot,
    SessionLocal,
    Variant
)
from publishers import (
    MockLinkedInPublisher,
    MockXPublisher,
    TelegramPublisher
)


def get_due_schedule_slots(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    return (
        db.query(ScheduleSlot)
        .filter(ScheduleSlot.scheduled_for <= now)
        .all()
    )


def get_publisher(platform):
    publishers = {
        "telegram": TelegramPublisher(),
        "mock_x": MockXPublisher(),
        "mock_linkedin": MockLinkedInPublisher()
    }

    return publishers.get(platform)


def process_due_slots(db):
    slots = get_due_schedule_slots(db)

    for slot in slots:
        variant = db.query(Variant).filter(
            Variant.id == slot.variant_id
        ).first()

        if not variant:
            continue

        successful_attempt = db.query(PublishAttempt).filter(
            PublishAttempt.schedule_slot_id == slot.id,
            PublishAttempt.success == 1
        ).first()

        if successful_attempt:
            continue

        publisher = get_publisher(variant.platform)

        if not publisher:
            continue

        result = publisher.publish(
            variant,
            slot.idempotency_key
        )

        attempt = PublishAttempt(
            schedule_slot_id=slot.id,
            success=1 if result.success else 0,
            detail=result.detail,
            external_post_id=result.external_post_id
        )

        db.add(attempt)

        if result.success:
            variant.status = "published"

        db.commit()


if __name__ == "__main__":
    db = SessionLocal()

    try:
        process_due_slots(db)
        print("Worker run completed")
    finally:
        db.close()
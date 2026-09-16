# Social Media Studio — Design

## Problem
One blog post (URL or pasted Markdown) becomes a set of platform-specific
social posts. A human must approve each variant before it can be scheduled.
A scheduler publishes approved variants at their scheduled time, exactly
once, even if the worker crashes and restarts mid-batch.

## Non-goal
No image generation, no analytics/engagement tracking, no real API
integration with Instagram, X, or LinkedIn. Those three are mock adapters
that record what would have been posted. Telegram is the one real,
live publish target.

## Data model

- **Post**: id, source_url (nullable), raw_content (text), created_at
- **Variant**: id, post_id (FK), platform (telegram / mock_x / mock_linkedin),
  content (text), status (draft / approved / rejected / published),
  created_at
- **ScheduleSlot**: id, variant_id (FK, one slot per variant),
  scheduled_for (datetime), idempotency_key (unique)
- **PublishAttempt**: id, schedule_slot_id (FK), attempted_at,
  success (bool), detail (text), external_post_id (nullable)

The idempotency_key is what makes retries safe — the publisher checks
"has this key already succeeded?" before calling the real adapter, not
after.

## API surface (rough — firmed up in Phase 2/3)

The current API supports post ingestion, variant generation and review,
scheduling, publishing history, and platform-specific publishing.

See `README.md` for the current endpoint list and usage examples.

## Constraint profiles

| Platform      | Max length | Tone            | Max hashtags |
|---------------|-----------|-----------------|--------------|
| mock_x        | 280       | short, punchy   | 2            |
| mock_linkedin | 3000      | professional    | 3            |
| telegram      | 1024      | casual, informative | 3        |

## SocialPublisher interface

    class SocialPublisher(ABC):
        @abstractmethod
        def publish(self, variant, idempotency_key: str) -> PublishResult:
            ...

Every adapter (TelegramPublisher, MockXPublisher, MockLinkedInPublisher)
implements this one method. The app calls `publish()` and never knows
which platform it's talking to.
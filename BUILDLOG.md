# Build Log

This document records the development process of the Social Media Studio
capstone, including where AI tools were used, decisions made during
development, testing, and corrections.

## AI Usage

AI tools were used as development assistants during the project.

They were mainly used for:

- Discussing project architecture before implementation
- Breaking the project into smaller implementation steps
- Explaining FastAPI and backend concepts
- Reviewing code structure and separation of responsibilities
- Suggesting validation and error handling approaches
- Helping debug implementation issues
- Reviewing Git workflow and commit decisions
- Reviewing test results and identifying missing evidence
- Helping prepare project documentation

The implementation was tested manually after each major feature rather than
assuming that generated or suggested code was correct.

## Development Approach

The project was developed incrementally.

The general workflow was:

```text
Plan
  ↓
Implement
  ↓
Run
  ↓
Test
  ↓
Fix
  ↓
Review
  ↓
Commit
```

Features were implemented in small stages so that the behavior could be
verified before moving to the next part.

## Major Development Stages

### 1. Initial Project Setup

The project structure, virtual environment, dependencies, database setup,
and initial documentation were created.

The initial design was documented in `DESIGN.md` before the main features
were implemented.

### 2. Post Ingestion and Storage

The API was implemented to create and store blog posts.

Database operations were kept separate from API request handling where
appropriate.

### 3. AI Social Content Generation

The project was extended to generate platform-specific social media
variants from stored post content.

Different platform constraint profiles were introduced for:

* Mock X
* Mock LinkedIn
* Telegram

### 4. Variant Review and Scheduling

Variants were given review states so that they could be approved or rejected
before publishing.

Scheduling was restricted to approved variants.

A stable idempotency key was also introduced for each scheduled variant.

### 5. Publishing Worker and Adapters

The publishing worker was implemented to process due schedule slots.

A publisher interface was used so that the worker could select different
publishing implementations based on the target platform.

The project includes:

* Telegram publisher
* Mock X publisher
* Mock LinkedIn publisher

Telegram was tested as the real external publishing target, while the other
platforms were kept as mock adapters.

### 6. Idempotency and Restart Handling

The worker was updated to check for an existing successful publishing attempt
using the schedule's idempotency key.

Database commits were placed inside the per-slot processing loop so that a
completed slot is saved before the worker moves to the next slot.

A manual interruption/restart test was performed using three fresh scheduled
variants.

The worker successfully completed the first slot, was interrupted before
starting the second slot, and after restart skipped the already-completed
slot and processed the remaining slots.

The exact test results are documented in `EVIDENCE.md`.

### 7. Publish History

A `/publish-history` endpoint was added to expose publishing attempts,
including successful and failed attempts.

This endpoint was tested using the actual publishing records created by the
worker.

## Corrections and Debugging

### Worker Environment Variables

The first standalone worker run failed to publish to Telegram because the
worker process was not loading the `.env` file.

The failure was:

```text
Telegram credentials are not configured
```

The worker was then updated to load environment variables using
`python-dotenv`.

After the fix, Telegram publishing succeeded and the message was confirmed
to arrive in Telegram.

This was an important reminder that running the worker as a separate Python
process has its own application startup path.

### Scheduling Idempotency

The first implementation generated a new random UUID as the idempotency
key every time `/schedule` was called. This was insufficient: calling
`/schedule` twice on the same variant created two separate `ScheduleSlot`
rows, each with its own key, so a client retry (e.g. after a timeout)
could result in the worker publishing the same variant twice.

The second attempt made the key deterministic but derived it from both
the variant ID and the scheduled time
(`f"{variant.id}-{scheduled_for.isoformat()}"`). This fixed the exact-retry
case but broke rescheduling: scheduling the same variant for a new time
produced a different key, and therefore a second `ScheduleSlot` row,
instead of updating the existing one.

The final design decouples the key from the schedule time entirely:

```text
variant-{variant_id}-schedule
```

`/schedule` now looks up any existing slot for the variant and updates its
`scheduled_for` in place if one exists, rather than always inserting a new
row. `ScheduleSlot.variant_id` is also constrained `unique=True` at the
database level, so the one-slot-per-variant rule holds even under a race
between two near-simultaneous requests, not just at the application layer.

This was the one area of the project that took multiple iterations to get
right, and it was validated with a real interruption test (see
`EVIDENCE.md`) rather than by inspection alone.

### Worker Idempotency

The worker originally needed stronger protection against duplicate publishing
after a restart.

The final implementation checks for an existing successful
`PublishAttempt` using the schedule's idempotency key before calling the
publisher.

This was then verified through a real worker interruption/restart test.

## Testing

Testing was performed through Swagger UI, terminal commands, worker runs,
and direct database inspection.

The tested areas included:

* Content length constraint enforcement
* Review and approval workflow
* Scheduling restrictions
* Mock X publishing
* Telegram publishing
* Publishing failure recording
* Publish history
* Idempotent publishing
* Worker interruption and restart
* Git secret protection

Detailed outputs are stored in `EVIDENCE.md`.

## Dependency Decision

During review, unused or unnecessary dependencies in `requirements.txt` were
identified.

The decision was made not to perform a late dependency cleanup because the
application was already working and changing the dependency file at that
stage could introduce unnecessary risk.

This decision was documented rather than making unrelated changes close to
the final stage of the project.

## Documentation

The project documentation was created progressively.

Current documentation includes:

* `DESIGN.md` — project design and architecture
* `README.md` — project overview, setup, API, workflow, testing, and
  limitations
* `EVIDENCE.md` — manual testing evidence
* `BUILDLOG.md` — development process and AI usage

## Final Notes

AI assistance was used throughout the project, but test results were checked
against the running application.

When an AI suggestion did not match the actual implementation or project
scope, it was corrected rather than blindly applied.

The goal of using AI was to support understanding, debugging, review, and
documentation while keeping the final implementation understandable and
appropriate for a junior backend project.

# Craaft Python SDK

The official Python client for the [Craaft API](https://craaft.io). It wraps the REST endpoints with typed dataclasses, a sensible retry policy, and a friendly exception hierarchy.

## Install

```bash
pip install craaft
```

Python 3.10 or newer.

## Quickstart

```python
from datetime import datetime, timedelta, timezone

from craaft import CraaftClient

# Reads CRAAFT_API_TOKEN (and optionally CRAAFT_BASE_URL) from the environment.
with CraaftClient() as client:
    me = client.me.get()
    print(f"Hi {me.name}")

    project = client.projects.create(name="Demo", description="A new board")

    card = client.projects.create_card(
        project.id,
        title="Ship the SDK",
        column="todo",
        position=1.0,
        description="all the bits",
    )

    # Metadata (priority, due_date, size, tags) is set via PATCH after create.
    client.cards.update(
        card.id,
        priority="high",
        size=3,
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
    )

    client.cards.add_comment(card.id, body="lgtm")

    # upcoming() and search() return CardSummary previews, not full cards.
    for summary in client.cards.upcoming():
        print(summary.title, summary.due_date, summary.project_name)
```

## Examples

The [`examples/`](examples/) directory has runnable scripts for the most common patterns. Each one is self-contained and cleans up after itself, so they're safe to run repeatedly:

| File | What it shows |
|------|---------------|
| [`quickstart.py`](examples/quickstart.py) | Sign in, create a card, leave a comment. |
| [`card_lifecycle.py`](examples/card_lifecycle.py) | Create, set priority and due date via PATCH, comment, move between columns, delete. |
| [`error_handling.py`](examples/error_handling.py) | Which exceptions to catch and what fields they carry. |
| [`retries.py`](examples/retries.py) | Tuning `RetryConfig` and reacting to `RateLimitError` yourself. |
| [`searching.py`](examples/searching.py) | `cards.search()` and `cards.upcoming()`, both returning `CardSummary`. |
| [`advanced_client.py`](examples/advanced_client.py) | Custom session, alternate base URL, user-agent, debug logging. |

Set `CRAAFT_API_TOKEN` (and optionally `CRAAFT_BASE_URL`) in your environment, then `python examples/quickstart.py`.

## Configuration

```python
from craaft import CraaftClient, RetryConfig

client = CraaftClient(
    api_key="cra_...",                     # or CRAAFT_API_TOKEN env var
    base_url="https://craaft.io/api/v1",   # or CRAAFT_BASE_URL env var (default: prod)
    timeout=30.0,                          # seconds, or (connect, read) tuple
    retry=RetryConfig(max_attempts=5),     # or retry=None to disable
    user_agent="my-app/1.0",
)
```

## Resources

| Sub-client          | Methods |
|---------------------|---------|
| `client.me`         | `get()`, `update(name=, email=, username=)` |
| `client.projects`   | `list()`, `get(id)`, `create(...)`, `update(id, ...)`, `delete(id)`, `export(id)`, `list_tags(id)`, `enable_share(id)`, `disable_share(id)`, `list_cards(id)`, `create_card(id, ...)`, `bulk_create_cards(id, cards)`, `list_milestones(id)`, `add_milestone(id, name=, due_on=)`, `add_column(id, title=)`, `list_members(id)`, `add_member(id, ...)`, `update_member(id, ...)`, `remove_member(id, ...)` |
| `client.cards`      | `update(id, ...)`, `bulk_update(cards)`, `bulk_move(ids, column=, target_project_id=)`, `delete(id)`, `move(id, ...)`, `upcoming()`, `focus()`, `hygiene(type=)`, `list_events(id)`, `search(q=, limit=20)`, `list_comments(id)`, `add_comment(id, body=)`, `list_checklist(id)`, `add_checklist_item(id, text=)` |
| `client.attachments`| `list_for_card(card_id)`, `upload(card_id, file=, filename=, content_type=)`, `download(attachment_id)`, `delete(attachment_id)` |
| `client.comments`   | `update(id, body=)`, `delete(id)` |
| `client.checklist`  | `update(id, text=, done=)`, `delete(id)` |
| `client.columns`    | `update(id, ...)`, `delete(id)`, `archive(id)` |
| `client.milestones` | `update(id, name=, due_on=, achieved=)`, `delete(id)` |
| `client.members`    | `list()`, `list_invitations()`, `create_invitation(...)` |

`upcoming()` and `search()` return `list[CardSummary]` - lightweight previews. `focus()` returns a `FocusResponse` with `due`, `attention`, and `hygiene` buckets.

## Bulk operations

Three methods batch card work into a single all-or-nothing transaction (max 100 items each). Items are dicts using the API's camelCase field names, passed through verbatim:

```python
# Create - title and column required per item; position omitted = append.
# Unlike create_card, the assignee is NOT defaulted to the caller.
cards = client.projects.bulk_create_cards(project.id, [
    {"title": "Ship it", "column": "todo"},
    {"title": "Review copy", "column": "doing", "priority": "high", "tags": ["launch"]},
])

# Update - {"id": ...} plus any single-PATCH fields. A key set to None sends
# JSON null and CLEARS the field (dueDate, assignedUserId, size, priority);
# an absent key leaves the field alone.
client.cards.bulk_update([
    {"id": cards[0].id, "priority": "urgent"},
    {"id": cards[1].id, "dueDate": None},
])

# Move - sweep cards to a column on their own board, or to another board in
# the same workspace via target_project_id.
client.cards.bulk_move([c.id for c in cards], column="done")
```

One invalid item rolls back the whole batch; the raised `ValidationError`'s message names the offending index (`cards[3]: title is required`). Bulk requests never send notification emails. `datetime` values under `dueDate` are serialized for you.

## Checklists and milestones

Per-card checklists (any board member may write) and per-project milestones (board admins only - `CraaftPermissionError` on 403):

```python
item = client.cards.add_checklist_item(card.id, text="write tests")
client.checklist.update(item.id, done=True)

m = client.projects.add_milestone(project.id, name="Beta", due_on=date(2026, 9, 1))
client.milestones.update(m.id, achieved=True)   # stamps achieved_at once
```

## Models

Frozen dataclasses, keyword-only. Highlights:

- `User`, `Project`, `Column`, `Card`, `Comment`, `Attachment`
- `ChecklistItem`, `Milestone` (`due_on` is a `datetime.date`; `achieved_at` is `datetime | None`)
- `CardSummary`, `AttentionCard`, `FocusResponse`, `HygieneCounts`, `CardEvent`
- `BoardMember`, `BoardMemberGrant`, `WorkspaceMember`, `Invitation`
- `ProjectExport` (+ nested export types)

`Card.size` is an optional **integer** estimate. `Card.priority` is one of `low`, `medium`, `high`, `urgent`. `Card.checklist_done` / `Card.checklist_total` are denormalized checklist progress counts (0 when the card has no checklist). Set metadata via `cards.update()` after `create_card()` - the create endpoint only accepts `title`, `column`, `position`, and optional `description`.

`attachments.upload()` sends multipart form data (max **25 MiB** per file) and requires a Pro/Team workspace; use `project.can_upload_attachments` to check first.

## Errors

```python
from craaft import CraaftAPIError, NotFoundError, RateLimitError

try:
    client.projects.get("missing")
except NotFoundError:
    ...
except RateLimitError as e:
    sleep(e.retry_after or 1)
except CraaftAPIError as e:
    print(e.status_code, e.message, e.request_id)
```

Hierarchy: `CraaftError` is the root. API failures raise `CraaftAPIError` or one of its subclasses (`AuthenticationError`, `PermissionError`, `NotFoundError`, `ConflictError`, `PlanLimitError`, `ValidationError`, `RateLimitError`, `ServerError`). Network failures raise `CraaftConnectionError` or `CraaftTimeoutError`.

## Retries

The client retries `429`, `502`, `503`, `504`, and network errors with exponential backoff and `Retry-After`-aware pauses. Writes (`POST` / `PATCH` / `DELETE`) skip 5xx retries by default, since the server may have applied the change before responding. Set `RetryConfig(retry_writes_on_5xx=True)` if your workload is safe to retry.

## Logging

The client logs one DEBUG line per HTTP attempt (method, path, status, duration, attempt number) on the `craaft` logger. The auth header is never logged.

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("craaft").setLevel(logging.DEBUG)
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check
mypy
```

## License

MIT

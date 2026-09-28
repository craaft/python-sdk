# Craaft Python SDK

The official Python client for [Craaft](https://craaft.io), the kanban board for one person or a small team who wants to see the work, not administer the tool.

Drive the same boards, cards, comments and members you see in the app: typed dataclasses instead of raw dicts, retries that honour `Retry-After`, and exceptions you can catch by failure type instead of by status code. Every call runs as the user who minted the token, with exactly the permissions they have in the UI.

## Install

```bash
pip install craaft
```

Python 3.10 or newer. `requests` is the only runtime dependency.

## Get a token

Open **Settings → API keys** in Craaft, or go straight to
[craaft.io/settings/api-keys](https://craaft.io/settings/api-keys).

A token looks like `cra_...` and is shown exactly once, so copy it before you
close the dialog. The `cra_` prefix is deliberate: it makes an accidental commit
scannable by tooling like GitHub Push Protection.

```bash
export CRAAFT_API_TOKEN=cra_...
```

The client reads that variable by default, so nothing in your code has to hold
the token.

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

    # upcoming() returns lightweight UpcomingCard previews, not full cards.
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
| [`searching.py`](examples/searching.py) | `cards.search()` (`SearchResult`) and `cards.upcoming()` (`UpcomingCard`). |
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
| `client.projects`   | `list()`, `get(id)`, `create(..., template=)`, `update(id, ...)`, `delete(id)`, `list_templates()`, `export(id)`, `export_csv(id)`, `list_tags(id)`, `enable_share(id)`, `disable_share(id)`, `list_cards(id)`, `list_archived_cards(id)`, `create_card(id, ...)`, `bulk_create_cards(id, cards)`, `rebalance_cards(id, ids, column=)`, `upload_background(id, file=)`, `download_background(id)`, `delete_background(id)`, `list_milestones(id)`, `add_milestone(id, name=, due_on=)`, `add_column(id, title=)`, `list_members(id)`, `add_member(id, ...)`, `update_member(id, ...)`, `remove_member(id, ...)` |
| `client.cards`      | `get(id)`, `detail(id)`, `update(id, ...)`, `bulk_update(cards)`, `bulk_move(ids, column=, target_project_id=)`, `delete(id)`, `archive(id)`, `restore(id)`, `move(id, ...)`, `follow(id)`, `unfollow(id)`, `upcoming()`, `focus()`, `hygiene(type=)`, `list_events(id)`, `search(q=, limit=20)`, `list_comments(id)`, `add_comment(id, body=)`, `list_checklist(id)`, `add_checklist_item(id, text=)` |
| `client.attachments`| `list_for_card(card_id)`, `upload(card_id, file=, filename=, content_type=)`, `download(attachment_id)`, `delete(attachment_id)` |
| `client.comments`   | `update(id, body=)`, `delete(id)` |
| `client.checklist`  | `update(id, text=, done=)`, `delete(id)` |
| `client.columns`    | `update(id, ...)`, `delete(id)`, `archive(id)`, `archive_with_ids(id)` |
| `client.milestones` | `update(id, name=, due_on=, achieved=)`, `delete(id)` |
| `client.members`    | `list()`, `update_role(user_id, role=)`, `remove(user_id)`, `list_invitations()`, `create_invitation(...)`, `revoke_invitation(id)` |
| `client.webhooks`   | `list_for_project(project_id)`, `create(project_id, url=, ...)`, `update(id, ...)`, `delete(id)` |
| `client.inbound_email` | `get(project_id)`, `enable(project_id, target_column=)`, `update(project_id, ...)`, `disable(project_id)` |
| `client.public`     | `board(token)`, `board_background(token)`, `avatar(user_id)` - no auth required |

`search()` returns `list[SearchResult]` and `upcoming()` returns `list[UpcomingCard]` - lightweight, endpoint-specific previews (see [Models](#models)). `focus()` returns a `FocusResponse` with `due` (`list[UpcomingCard]`), `attention`, and `hygiene` buckets. `client.version()` returns the server's build info and needs no auth, which makes it a cheap liveness probe.

The one endpoint the SDK deliberately does not wrap is `GET /projects/{id}/events`. That is the realtime SSE stream, not an activity log: it opens a `text/event-stream` that never completes, so a request/response client would simply hang on it. Per-card history is `cards.list_events(id)`, which is ordinary JSON.

### Following and board maintenance

```python
card = client.cards.get(card_id)      # single fetch, no board scan
detail = client.cards.detail(card_id)  # card + comments + events + checklist + attachments, one call
if not card.following:
    client.cards.follow(card_id)      # idempotent, returns None

# Only when repeated midpoint inserts have run out of room between two
# neighbours. Request order becomes positions 1, 2, 3, ...
client.projects.rebalance_cards(project.id, ordered_ids, column="doing")
```

### Board templates

```python
for template in client.projects.list_templates():
    print(template.key, template.name, len(template.columns))

# Seed the new board with the "sprint" template's columns instead of the
# default Kanban three. Omit template= (or pass "") for the default.
project = client.projects.create(name="Q3 Sprint", template="sprint")
```

An unrecognised `template` key raises `ValidationError` (400). The create response doesn't include the board's columns; call `client.projects.get()` on the new id to read their keys (only the default template uses `todo` / `doing` / `done`).

### Archiving cards

```python
client.cards.archive(card.id)              # off the board, still searchable
archived = client.projects.list_archived_cards(project.id)
client.cards.restore(archived[0].id)       # back to its original column + position

# Bulk-archive every live card in a done column.
count = client.columns.archive(done_column.id)

# Same, but also returning the archived card ids so you can offer an undo.
result = client.columns.archive_with_ids(done_column.id)
print(result.archived, result.ids)
```

Archiving a card that is already archived, or restoring one that isn't, raises `NotFoundError`. `columns.archive()` / `archive_with_ids()` only take effect on a column flagged `is_done` - any other column answers `archived=0` rather than an error.

### Board backgrounds

```python
project = client.projects.upload_background(project.id, file="hero.png")
raw = client.projects.download_background(project.id)
client.projects.delete_background(project.id)
```

Board admins only, max 10 MiB, and PNG / JPEG / WebP / GIF only - the server sniffs the leading bytes as well as the declared type, so a renamed file is rejected. A background and a `background_color` are mutually exclusive.

### Public boards

```python
board = client.public.board(share_token)   # no auth needed
print(board.project.name, len(board.cards))
```

The share token is the access check. Revoking sharing, or re-enabling it (which mints a fresh token), invalidates old links immediately and raises `NotFoundError`. The snapshot is trimmed: no workspace or ownership fields, and no card metadata beyond priority and assignee.

### Webhooks and email-to-card

Board admins on a Pro plan can wire a board up to outbound webhooks and an intake email address. Both are 402 (`PlanLimitError`) on a Free board for every operation except delete/disable, which stay open so a downgraded workspace can still clean up:

```python
catalogue = client.webhooks.list_for_project(project.id)
print(catalogue.event_catalogue)   # broadcast names you can filter on

hook = client.webhooks.create(
    project.id,
    url="https://hooks.slack.com/services/...",
    format="slack",
    events=["card.created", "card.archived"],
)
client.webhooks.update(hook.id, active=False)
client.webhooks.delete(hook.id)
```

`hook.secret` is the HMAC signing secret for `"craaft"`-format deliveries (`X-Craaft-Signature`); it is returned on every read, not redacted. Slack and Discord deliveries are unsigned.

```python
status = client.inbound_email.get(project.id)
if not status.enabled:
    address = client.inbound_email.enable(project.id, target_column="todo")
    print(address.email)   # mail sent here becomes a card

client.inbound_email.update(project.id, rotate=True)     # mint a new address
client.inbound_email.update(project.id, target_column="")  # clear back to the first column
client.inbound_email.disable(project.id)
```

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
from datetime import date

item = client.cards.add_checklist_item(card.id, text="write tests")
client.checklist.update(item.id, done=True)

milestone = client.projects.add_milestone(project.id, name="Beta", due_on=date(2026, 9, 1))
client.milestones.update(milestone.id, achieved=True)   # stamps achieved_at once
```

## Models

Frozen dataclasses, keyword-only. Highlights:

- `User`, `Project`, `Column`, `Card`, `Comment`, `Attachment`
- `ChecklistItem`, `Milestone` (`due_on` is a `datetime.date`; `achieved_at` is `datetime | None`)
- `SearchResult` (`cards.search()`), `UpcomingCard` (`cards.upcoming()` and `FocusResponse.due`), `AttentionCard`, `FocusResponse`, `HygieneCounts`, `CardEvent`
- `BoardMember`, `BoardMemberGrant`, `WorkspaceMember`, `Invitation` (`consumed` is `True` when a verified account was added to the workspace immediately instead of being left pending)
- `BoardTemplate` (+ `BoardTemplateColumn`), `ColumnArchiveResult`
- `WebhookSubscription` (+ `WebhookDelivery`), `BoardWebhooks`
- `InboundEmailAddress`, `InboundEmailStatus`
- `ProjectExport` (+ nested export types)
- `PublicBoard` (+ `PublicBoardProject`, `PublicBoardColumn`, `PublicBoardCard`)

`Card.size` is an optional **integer** estimate. `Card.priority` is one of `low`, `medium`, `high`, `urgent`. `Card.checklist_done` / `Card.checklist_total` are denormalized checklist progress counts (0 when the card has no checklist). `Card.following` is whether **the authenticated caller** follows the card, so it differs per token for the same card. `Card.archived_at` is set only by `projects.list_archived_cards()`; `None` everywhere else, including a live card. Set metadata via `cards.update()` after `create_card()` - the create endpoint only accepts `title`, `column`, `position`, and optional `description`.

`attachments.upload()` sends multipart form data (max **25 MiB** per file) and requires a Pro/Team workspace; use `project.can_upload_attachments` to check first.

`CardSummary` is deprecated: it used to be the shared return type of both `search()` and `upcoming()`, which was a bug since the two endpoints return different shapes (one has no due date/assignee/priority, the other has no description/updated_at/archived). It has been split into `SearchResult` and `UpcomingCard`; `CardSummary` is kept importable, and the two replacements keep its unused fields around too (always their default) so old code reading them doesn't raise `AttributeError`, but new code should use the two specific types.

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

## Reference

The API this client wraps is documented at
[craaft.io/openapi.yaml](https://craaft.io/openapi.yaml), which the running
server publishes directly, so it always matches the deployment you are talking
to. There is a PHP client at
[github.com/craaft/php-sdk](https://github.com/craaft/php-sdk) covering the same
surface.

Found a bug or a missing endpoint?
[Open an issue](https://github.com/craaft/python-sdk/issues).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check
mypy
```

## License

MIT

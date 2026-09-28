from datetime import date, datetime, timezone

from craaft.models import (
    BoardTemplate,
    BoardWebhooks,
    Card,
    CardSummary,
    ChecklistItem,
    Column,
    ColumnArchiveResult,
    Comment,
    InboundEmailStatus,
    Invitation,
    Milestone,
    Project,
    SearchResult,
    UpcomingCard,
    User,
    WebhookSubscription,
)


def test_user_from_api():
    u = User.from_api(
        {
            "id": "u1",
            "email": "a@b.co",
            "name": "Alice",
            "username": "alice",
            "avatarUrl": "https://example.com/a.png",
            "hasPassword": True,
        }
    )
    assert u.id == "u1"
    assert u.avatar_url == "https://example.com/a.png"
    assert u.has_password is True


def test_column_from_api():
    c = Column.from_api(
        {
            "id": "col1",
            "key": "todo",
            "title": "To Do",
            "color": "#aaa",
            "position": 1.5,
            "isDone": False,
            "cardLimit": None,
        }
    )
    assert c.key == "todo"
    assert c.position == 1.5


def test_card_from_api_full():
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "Do thing",
            "position": 2.0,
            "description": "do it",
            "dueDate": "2026-06-01T00:00:00+00:00",
            "assignedUserId": "u2",
            "assignedUserName": "Bob",
            "size": 3,
            "priority": "high",
            "createdBy": "u1",
            "createdByName": "Alice",
            "updatedBy": "u1",
            "updatedByName": "Alice",
            "attachmentCount": 3,
            "checklistDone": 2,
            "checklistTotal": 5,
            "tags": ["api", "sdk"],
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T11:00:00+00:00",
        }
    )
    assert c.assigned_user_id == "u2"
    assert c.size == 3
    assert c.priority == "high"
    assert c.checklist_done == 2
    assert c.checklist_total == 5
    assert c.tags == ["api", "sdk"]
    assert c.due_date == datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert c.archived_at is None


def test_card_from_api_archived():
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "Do thing",
            "position": 2.0,
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T11:00:00+00:00",
            "archivedAt": "2026-05-09T09:00:00Z",
        }
    )
    assert c.archived_at == datetime(2026, 5, 9, 9, 0, 0, tzinfo=timezone.utc)


def test_card_from_api_legacy_assignee_id_key():
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "x",
            "position": 1.0,
            "assigneeId": "u2",
            "attachmentCount": 0,
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.assigned_user_id == "u2"
    # checklistDone / checklistTotal absent from the payload - safe default 0.
    assert c.checklist_done == 0
    assert c.checklist_total == 0


def test_card_summary_from_search_shape():
    # CardSummary is deprecated (superseded by SearchResult / UpcomingCard)
    # but kept parseable for backward compatibility.
    c = CardSummary.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "projectName": "Launch board",
            "columnKey": "doing",
            "columnTitle": "In Progress",
            "title": "Ship",
            "description": "do it",
            "updatedAt": "2026-05-08T10:00:00Z",
            "archived": True,
        }
    )
    assert c.archived is True
    assert c.description == "do it"


def test_search_result_from_api():
    r = SearchResult.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "projectName": "Launch board",
            "columnKey": "doing",
            "columnTitle": "In Progress",
            "title": "Ship",
            "description": "do it",
            "updatedAt": "2026-05-08T10:00:00Z",
            "archived": True,
        }
    )
    assert r.archived is True
    assert r.description == "do it"
    # Deprecated fields this endpoint never sends: always their default.
    assert r.due_date is None
    assert r.assigned_user_id is None
    assert r.assigned_user_name is None
    assert r.priority is None


def test_upcoming_card_from_api():
    u = UpcomingCard.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "projectName": "Launch board",
            "columnKey": "doing",
            "columnTitle": "In Progress",
            "title": "Ship",
            "dueDate": "2026-05-08T10:00:00Z",
            "assignedUserId": "u2",
            "assignedUserName": "Bob",
            "priority": "high",
        }
    )
    assert u.due_date is not None
    assert u.assigned_user_id == "u2"
    assert u.priority == "high"
    # Deprecated fields this endpoint never sends: always their default.
    assert u.description is None
    assert u.updated_at is None
    assert u.archived is False


def test_upcoming_card_from_api_omitted_assignee():
    u = UpcomingCard.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "projectName": "Launch board",
            "columnKey": "doing",
            "columnTitle": "In Progress",
            "title": "Ship",
            "dueDate": "2026-05-08T10:00:00Z",
        }
    )
    assert u.assigned_user_id is None
    assert u.assigned_user_name is None
    assert u.priority is None


def test_board_template_from_api():
    t = BoardTemplate.from_api(
        {
            "key": "sprint",
            "name": "Sprint",
            "description": "Backlog through review for time-boxed work.",
            "columns": [
                {"title": "Backlog", "color": "", "isDone": False},
                {"title": "Done", "color": "green", "isDone": True},
            ],
        }
    )
    assert t.key == "sprint"
    assert len(t.columns) == 2
    assert t.columns[1].is_done is True
    assert t.columns[1].color == "green"


def test_column_archive_result_from_api():
    r = ColumnArchiveResult.from_api({"archived": 2, "ids": ["c1", "c2"]})
    assert r.archived == 2
    assert r.ids == ["c1", "c2"]


def test_webhook_subscription_from_api():
    w = WebhookSubscription.from_api(
        {
            "id": "wh1",
            "endpointId": "ep1",
            "url": "https://example.com/hook",
            "secret": "shh",
            "description": "CI notifier",
            "format": "slack",
            "events": ["card.created"],
            "active": True,
            "createdAt": "2026-05-08T10:00:00Z",
            "recentDeliveries": [
                {
                    "event": "card.created",
                    "status": "delivered",
                    "statusCode": 200,
                    "attempts": 1,
                    "error": "",
                    "createdAt": "2026-05-08T10:05:00Z",
                }
            ],
        }
    )
    assert w.format == "slack"
    assert w.events == ["card.created"]
    assert w.recent_deliveries[0].status == "delivered"
    assert w.recent_deliveries[0].error == ""


def test_webhook_delivery_failed_carries_an_error_string():
    from craaft.models import WebhookDelivery

    d = WebhookDelivery.from_api(
        {
            "event": "card.created",
            "status": "failed",
            "statusCode": 502,
            "attempts": 3,
            "error": "connection refused",
            "createdAt": "2026-05-08T10:05:00Z",
        }
    )
    assert d.status == "failed"
    assert d.error == "connection refused"


def test_webhook_delivery_error_defaults_to_empty_string_not_none():
    from craaft.models import WebhookDelivery

    d = WebhookDelivery.from_api(
        {
            "event": "card.created",
            "status": "delivered",
            "statusCode": 200,
            "attempts": 1,
            "error": None,
            "createdAt": "2026-05-08T10:05:00Z",
        }
    )
    assert d.error == ""


def test_webhook_subscription_defaults():
    w = WebhookSubscription.from_api(
        {
            "id": "wh1",
            "endpointId": "ep1",
            "url": "https://example.com/hook",
            "secret": "shh",
            "createdAt": "2026-05-08T10:00:00Z",
        }
    )
    assert w.format == "craaft"
    assert w.events == []
    assert w.recent_deliveries == []
    assert w.active is False


def test_board_webhooks_from_api():
    bw = BoardWebhooks.from_api(
        {
            "webhooks": [],
            "eventCatalogue": ["card.created", "card.updated"],
        }
    )
    assert bw.webhooks == []
    assert bw.event_catalogue == ["card.created", "card.updated"]


def test_inbound_email_status_disabled():
    s = InboundEmailStatus.from_api({"enabled": False, "address": None})
    assert s.enabled is False
    assert s.address is None


def test_inbound_email_status_enabled():
    s = InboundEmailStatus.from_api(
        {
            "enabled": True,
            "address": {
                "email": "in-abc123@mail.craaft.io",
                "token": "abc123",
                "targetColumn": "todo",
                "active": True,
                "createdAt": "2026-05-08T10:00:00Z",
            },
        }
    )
    assert s.enabled is True
    assert s.address is not None
    assert s.address.email == "in-abc123@mail.craaft.io"
    assert s.address.target_column == "todo"


def test_invitation_from_api_defaults_consumed_false():
    inv = Invitation.from_api(
        {
            "id": "inv1",
            "email": "a@b.co",
            "role": "member",
            "invitedBy": "u1",
            "invitedByName": "Alice",
            "createdAt": "2026-05-08T10:00:00Z",
            "expiresAt": "2026-06-08T10:00:00Z",
            "boardGrants": [],
        }
    )
    assert inv.consumed is False


def test_invitation_from_api_consumed_true():
    inv = Invitation.from_api(
        {
            "id": "inv1",
            "email": "a@b.co",
            "role": "member",
            "invitedBy": "u1",
            "invitedByName": "Alice",
            "createdAt": "2026-05-08T10:00:00Z",
            "expiresAt": "2026-06-08T10:00:00Z",
            "boardGrants": [],
            "consumed": True,
        }
    )
    assert inv.consumed is True


def test_comment_from_api():
    c = Comment.from_api(
        {
            "id": "cm1",
            "cardId": "card1",
            "authorId": "u1",
            "body": "hi",
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.body == "hi"


def test_checklist_item_from_api():
    i = ChecklistItem.from_api(
        {
            "id": "cl1",
            "cardId": "card1",
            "text": "write tests",
            "done": True,
            "position": 2.5,
            "createdAt": "2026-07-18T10:00:00Z",
            "updatedAt": "2026-07-18T11:00:00Z",
        }
    )
    assert i.card_id == "card1"
    assert i.text == "write tests"
    assert i.done is True
    assert i.position == 2.5
    assert i.created_at == datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)


def test_milestone_from_api():
    m = Milestone.from_api(
        {
            "id": "m1",
            "projectId": "p1",
            "name": "Beta launch",
            "dueOn": "2026-09-01",
            "achievedAt": "2026-08-30T09:00:00Z",
            "createdAt": "2026-07-18T10:00:00Z",
            "updatedAt": "2026-07-18T10:00:00Z",
        }
    )
    assert m.project_id == "p1"
    assert m.due_on == date(2026, 9, 1)
    assert m.achieved_at == datetime(2026, 8, 30, 9, 0, 0, tzinfo=timezone.utc)


def test_milestone_from_api_null_achieved_at():
    m = Milestone.from_api(
        {
            "id": "m1",
            "projectId": "p1",
            "name": "Beta launch",
            "dueOn": "2026-09-01",
            "achievedAt": None,
            "createdAt": "2026-07-18T10:00:00Z",
            "updatedAt": "2026-07-18T10:00:00Z",
        }
    )
    assert m.achieved_at is None


def test_project_from_api_with_columns():
    p = Project.from_api(
        {
            "id": "p1",
            "workspaceId": "w1",
            "workspaceName": "Personal",
            "name": "Demo",
            "description": "desc",
            "isFavorite": True,
            "publicToken": "tok",
            "backgroundImage": None,
            "backgroundColor": "#aabbcc",
            "colorScheme": None,
            "textColor": "dark",
            "myRole": "owner",
            "visibility": "private",
            "myBoardRole": "admin",
            "canUploadAttachments": True,
            "totalCards": 5,
            "columnCounts": {"todo": 2, "doing": 3},
            "columns": [
                {
                    "id": "c1",
                    "key": "todo",
                    "title": "To Do",
                    "color": "#aaa",
                    "position": 1.0,
                    "isDone": False,
                    "cardLimit": None,
                }
            ],
            "members": [{"id": "u1", "name": "Alice", "avatarUrl": ""}],
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert p.workspace_name == "Personal"
    assert p.background_color == "#aabbcc"
    assert p.visibility == "private"
    assert p.can_upload_attachments is True
    assert len(p.members) == 1
    assert p.members[0].name == "Alice"

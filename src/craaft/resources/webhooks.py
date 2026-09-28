from __future__ import annotations

from craaft.models import BoardWebhooks, WebhookFormat, WebhookSubscription
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg


class WebhooksResource(BaseResource):
    """Outbound webhook endpoints.

    Board-scoped list/create live under ``/projects/{id}/webhooks``;
    subscription-scoped update/delete live under ``/webhooks/{id}``, mirroring
    how :class:`~craaft.resources.attachments.AttachmentsResource` mixes a
    card id and an attachment id across one resource. Board admins only;
    list/create/update additionally require a Pro plan (402 on Free) -
    delete is never plan-gated so a downgraded workspace can still clean up.
    """

    def list_for_project(self, project_id: str) -> BoardWebhooks:
        """List a board's webhook subscriptions plus the broadcast event catalogue."""
        data = self._transport.request(
            "GET", f"/projects/{id_seg(project_id)}/webhooks"
        )
        return BoardWebhooks.from_api(data)

    def create(
        self,
        project_id: str,
        *,
        url: str,
        description: str | None = None,
        format: WebhookFormat | None = None,
        events: list[str] | None = None,
    ) -> WebhookSubscription:
        """Register a new webhook endpoint and subscribe this board to events.

        ``format`` defaults to ``"craaft"`` (a signed JSON envelope) on the
        server when omitted; ``"slack"`` and ``"discord"`` post unsigned
        message JSON to webhook URLs registered with those services.
        ``events`` filters which broadcast names trigger a delivery; omit it
        (or pass an empty list) to subscribe to everything. The URL must be
        absolute http(s) - a literal private, loopback or link-local address
        is rejected. The response carries the signing secret, as does every
        later read.
        """
        body: dict[str, object] = {"url": url}
        if description is not None:
            body["description"] = description
        if format is not None:
            body["format"] = format
        if events is not None:
            body["events"] = events
        data = self._transport.request(
            "POST", f"/projects/{id_seg(project_id)}/webhooks", json=body
        )
        return WebhookSubscription.from_api(data)

    def update(
        self,
        webhook_id: str,
        *,
        url: str | None = None,
        description: str | None = None,
        format: WebhookFormat | None = None,
        events: list[str] | None = None,
        active: bool | None = None,
    ) -> WebhookSubscription:
        """Partially update a webhook subscription.

        ``webhook_id`` is the subscription id from
        :meth:`list_for_project`, not the underlying endpoint id.
        """
        body: dict[str, object] = {}
        if url is not None:
            body["url"] = url
        if description is not None:
            body["description"] = description
        if format is not None:
            body["format"] = format
        if events is not None:
            body["events"] = events
        if active is not None:
            body["active"] = active
        data = self._transport.request(
            "PATCH", f"/webhooks/{id_seg(webhook_id)}", json=body
        )
        return WebhookSubscription.from_api(data)

    def delete(self, webhook_id: str) -> None:
        """Delete a webhook subscription. Board admin only, not plan-gated."""
        self._transport.request("DELETE", f"/webhooks/{id_seg(webhook_id)}")

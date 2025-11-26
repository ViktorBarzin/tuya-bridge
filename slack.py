from slack_sdk.webhook import WebhookClient, WebhookResponse
import os

url: str | None = os.environ.get("SLACK_URL")


def send_message(msg: str) -> WebhookResponse | None:
    if not url:
        return None
    webhook = WebhookClient(url)

    response = webhook.send(text=f"Tuya bridge message: {msg}")
    assert response.status_code == 200
    assert response.body == "ok"
    return response

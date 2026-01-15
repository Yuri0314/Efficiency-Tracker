"""
Notification Module.

This module handles sending report notifications via DingTalk and Email.
"""

from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests


class DingTalkNotifier:
    """
    DingTalk personal message notifier using enterprise internal application.

    This uses DingTalk's work notification API to send messages to specific users.

    Attributes:
        corp_id: The corporation ID.
        app_key: The application key.
        app_secret: The application secret.
        agent_id: The agent ID for the internal application.
        user_id: The target user's ID (staff ID or unionid).
    """

    def __init__(
        self,
        corp_id: str,
        app_key: str,
        app_secret: str,
        agent_id: str,
        user_id: str,
    ) -> None:
        """
        Initialize the DingTalk notifier.

        Args:
            corp_id: The corporation ID.
            app_key: The application key.
            app_secret: The application secret.
            agent_id: The agent ID for the internal application.
            user_id: The target user's ID.
        """
        self.corp_id = corp_id
        self.app_key = app_key
        self.app_secret = app_secret
        self.agent_id = agent_id
        self.user_id = user_id
        self._access_token: str | None = None

    def _get_access_token(self) -> str:
        """
        Get access token from DingTalk API.

        Returns:
            The access token string.

        Raises:
            RuntimeError: If token retrieval fails.
        """
        if self._access_token:
            return self._access_token

        url = "https://oapi.dingtalk.com/gettoken"
        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        if result.get("errcode") != 0:
            raise RuntimeError(f"Failed to get DingTalk token: {result}")

        self._access_token = result["access_token"]
        return self._access_token

    def send(self, title: str, content: str) -> bool:
        """
        Send a work notification to the user.

        Args:
            title: The message title.
            content: The message content (supports markdown).

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        try:
            token = self._get_access_token()

            url = f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2?access_token={token}"

            # Truncate content if too long (DingTalk limit)
            if len(content) > 5000:
                content = content[:4900] + "\n\n...(内容过长，已截断)"

            payload = {
                "agent_id": self.agent_id,
                "userid_list": self.user_id,
                "msg": {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,
                        "text": content,
                    },
                },
            }

            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            if result.get("errcode") != 0:
                print(f"DingTalk send failed: {result}")
                return False

            return True

        except Exception as e:
            print(f"DingTalk notification error: {e}")
            return False


class EmailNotifier:
    """
    Email notifier using SMTP.

    Attributes:
        smtp_host: The SMTP server hostname.
        smtp_port: The SMTP server port.
        smtp_user: The SMTP username.
        smtp_password: The SMTP password.
        to_address: The recipient email address.
        use_ssl: Whether to use SSL (default True).
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        to_address: str,
        use_ssl: bool = True,
    ) -> None:
        """
        Initialize the email notifier.

        Args:
            smtp_host: The SMTP server hostname.
            smtp_port: The SMTP server port.
            smtp_user: The SMTP username.
            smtp_password: The SMTP password.
            to_address: The recipient email address.
            use_ssl: Whether to use SSL. Defaults to True.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.to_address = to_address
        self.use_ssl = use_ssl

    def send(self, title: str, content: str) -> bool:
        """
        Send an email notification.

        Args:
            title: The email subject.
            content: The email body (markdown format, sent as plain text).

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = self.smtp_user
            msg["To"] = self.to_address

            # Send as plain text (markdown)
            text_part = MIMEText(content, "plain", "utf-8")
            msg.attach(text_part)

            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_host, self.smtp_port, context=context
                ) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, self.to_address, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, self.to_address, msg.as_string())

            return True

        except Exception as e:
            print(f"Email notification error: {e}")
            return False


def send_notification(
    config: dict[str, Any],
    title: str,
    content: str,
) -> dict[str, bool]:
    """
    Send notifications via all enabled channels.

    Args:
        config: The notification configuration dictionary.
        title: The notification title.
        content: The notification content.

    Returns:
        A dictionary mapping channel names to success status.
    """
    results: dict[str, bool] = {}

    if not config.get("enabled", False):
        return results

    channels = config.get("channels", {})

    # DingTalk
    dingtalk_config = channels.get("dingtalk", {})
    if dingtalk_config.get("enabled", False):
        notifier = DingTalkNotifier(
            corp_id=dingtalk_config["corp_id"],
            app_key=dingtalk_config["app_key"],
            app_secret=dingtalk_config["app_secret"],
            agent_id=dingtalk_config["agent_id"],
            user_id=dingtalk_config["user_id"],
        )
        results["dingtalk"] = notifier.send(title, content)

    # Email
    email_config = channels.get("email", {})
    if email_config.get("enabled", False):
        notifier = EmailNotifier(
            smtp_host=email_config["smtp_host"],
            smtp_port=email_config.get("smtp_port", 465),
            smtp_user=email_config["smtp_user"],
            smtp_password=email_config["smtp_password"],
            to_address=email_config["to_address"],
            use_ssl=email_config.get("use_ssl", True),
        )
        results["email"] = notifier.send(title, content)

    return results

import asyncio
import logging

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.header import decode_header

from .config import SMTP_PORT, SMTP_SERVER, IMAP_PORT, IMAP_SERVER


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_email(payload: str, subject: str, from_email: str, from_email_password: str, to_email: str):
    await asyncio.sleep(5)
    email_message = MIMEText(payload)
    email_message["From"] = from_email
    email_message["To"] = to_email
    email_message["Subject"] = subject
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as SMTP_client:
        SMTP_client.starttls()
        SMTP_client.login(from_email, from_email_password)
        SMTP_client.sendmail(from_email, to_email, email_message.as_string())


def parse_email_id(IMAP_client: imaplib.IMAP4_SSL, email_id: str):
    email_status, email_data = IMAP_client.fetch(email_id, "(RFC822)")

    parsed_responses = []
    for response_data in email_data:
        if not isinstance(response_data, tuple):
            continue

        email_bytes = response_data[1]
        email_message = email.message_from_bytes(email_bytes)
        payload = email_message.get_payload()
        if email_message["Subject"]:
            decoded_subject, subject_encoding = decode_header(email_message["Subject"])[0]

            email_subject = decoded_subject.decode(subject_encoding) if isinstance(decoded_subject, bytes) else (
                decoded_subject)
        else:
            email_subject = ""

        unclear_to_email_address = email_message.get("To")
        if "<" in unclear_to_email_address:
            to_email_address = unclear_to_email_address[unclear_to_email_address.index("<") + 1:
                                                        unclear_to_email_address.index(">")]
        else:
            to_email_address = unclear_to_email_address

        unclear_from_email_address = email_message.get("From")
        if "<" in unclear_from_email_address:
            from_email_address = unclear_from_email_address[unclear_from_email_address.index("<") + 1:
                                                            unclear_from_email_address.index(">")]
        else:
            from_email_address = unclear_from_email_address

        date = email_message.get("Date")
        message_id = email_message.get("Message-ID")

        parsed_email = {
            "payload": payload,
            "subject": email_subject,
            "to": to_email_address,
            "from": from_email_address,
            "date": date,
            "message_id": message_id
        }
        parsed_responses.append(parsed_email)

    return parsed_responses


def get_email_ids(IMAP_client):
    inbox_status, inbox_messages = IMAP_client.search(None, "ALL")
    email_ids = inbox_messages[0].split()
    return email_ids


class EmailMessage:
    def __init__(self, payload: str, subject: str, to_email_address: str, from_email_address: str, date: str,
                 message_id: str):
        self.payload: str = payload
        self.subject: str = subject
        self.to_email_address: str = to_email_address
        self.from_email_address: str = from_email_address
        self.date: str = date
        self.message_id: str = message_id

    def __repr__(self):
        payload = self.payload.replace("\r", "").replace("\n", "")
        return (f"EmailMessage(payload={payload},subject={self.subject},to_email_address={self.to_email_address},"
                f"from_email_address={self.from_email_address},date={self.date},message_id={self.message_id})")


class EmailAccount:
    def __init__(self, email_address: str, email_password: str, messages: list[EmailMessage] = None):
        self.email_address: str = email_address
        self.email_password: str = email_password
        self.inbox: list[EmailMessage] = [] if not messages else messages

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.refresh_inbox())

    def __repr__(self):
        return f"EmailAccount(email_address={self.email_address},email_password={self.email_password})"

    async def send_email(self, payload: str, subject: str, to_email: str):
        logging.log(logging.INFO, f"Sending Email ({payload}) To {to_email}")
        await send_email(payload, subject, self.email_address, self.email_password, to_email)

    def read_inbox(self):
        cached_message_id = self.inbox[-1].message_id if len(self.inbox) > 0 else None
        last_message_id = None
        new_messages = []

        with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT) as IMAP_client:
            IMAP_client.login(self.email_address, self.email_password)
            status, messages = IMAP_client.select("INBOX")

            email_ids = get_email_ids(IMAP_client)
            for email_id in email_ids[::-1]:
                if last_message_id == cached_message_id and last_message_id is not None:
                    break

                parsed_responses = parse_email_id(IMAP_client, email_id)
                for parsed_email in parsed_responses:
                    payload, subject, to_email_address, from_email_address, date, message_id = parsed_email.values()
                    message = EmailMessage(payload, subject, to_email_address, from_email_address, date, message_id)
                    new_messages.append(message)
                    last_message_id = message.message_id
        self.inbox += new_messages[::-1]
        return self.inbox

    async def refresh_inbox(self):
        while True:
            await asyncio.sleep(5)
            self.read_inbox()

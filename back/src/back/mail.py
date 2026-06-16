from email.message import EmailMessage

import aiosmtplib

from back import Settings


async def send_plain_mail(to: str, subject: str, body: str) -> None:
    if Settings.MAIL_HOST is None:
        raise RuntimeError('MAIL_HOST is not configured')

    message = EmailMessage()
    message['From'] = Settings.MAIL_FROM
    message['To'] = to
    message['Subject'] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=Settings.MAIL_HOST,
        port=Settings.MAIL_PORT,
        username=Settings.MAIL_USERNAME,
        password=Settings.MAIL_PASSWORD,
        start_tls=Settings.MAIL_START_TLS,
    )

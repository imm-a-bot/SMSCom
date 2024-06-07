import asyncio
import logging

import discord
import emailapi

from .config import CHANNEL_ID, RECEIVER_EMAIL_ADDRESS, ENDING_TAG


class DiscordClient(discord.Client):
    def __init__(self, email_client: emailapi.EmailAccount):
        super().__init__()
        self.email_client: emailapi.EmailAccount = email_client
        self.messages_sent = self.email_client.read_inbox()

    async def on_ready(self):
        logging.log(logging.INFO, f"Logged in as {self.user} (ID: {self.user.id})")
        await self.loop.create_task(self.send_received_messages())

    async def on_message(self, message: discord.Message):
        if message.channel.id != CHANNEL_ID:
            return
        if message.author.id == self.user.id:
            return
        await self.email_client.send_email(message.content, message.author.display_name, RECEIVER_EMAIL_ADDRESS)
        logging.log(logging.INFO, f"({message.content}) From ({message.author.display_name})")

    async def send_received_messages(self):
        while True:
            await asyncio.sleep(5)
            sent_message_ids = [sent_message.message_id for sent_message in self.messages_sent]

            inbox = self.email_client.read_inbox()
            for email_message in inbox[::-1]:
                if email_message.message_id in sent_message_ids:
                    break
                channel = self.get_channel(CHANNEL_ID)

                if "--=" in email_message.payload:
                    response = email_message.payload[0: email_message.payload.index("--=")]
                else:
                    response = email_message.payload

                response = response.replace("=C2=A0", " ")
                response += f"\n {ENDING_TAG}"
                await channel.send(response)

                self.messages_sent.append(email_message)
                logging.log(logging.INFO, f"Sent Received Message {email_message.payload}")

import logging

import emailapi
import discordreader
from config import TEST_GUILD, DISCORD_TOKEN, EMAIL_ADDRESS, EMAIL_PASSWORD
        

if __name__ == "__main__":
    email_client = emailapi.EmailAccount(EMAIL_ADDRESS, EMAIL_PASSWORD)

    client = discordreader.DiscordClient(email_client)
    client.run("MTE0MzkxNzE1NjYxOTI1OTkzNA.GGtC5a.BAazz7TaAT8RTfGuFGpC7TAcYNpwzC--FcmpWo")

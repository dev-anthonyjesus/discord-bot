from nextcord.ext import tasks

_bot = None


def setup_ticket_system(bot):
    global _bot
    _bot = bot


@tasks.loop(hours=6)
async def ticket_reminder_loop():
    return


@ticket_reminder_loop.before_loop
async def before_ticket_reminder_loop():
    if _bot:
        await _bot.wait_until_ready()

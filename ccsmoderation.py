import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import sqlite3
import os
import datetime
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_user_table():
    connection = sqlite3.connect(os.path.join(BASE_DIR, "user_warnings.db"))
    cursor = connection.cursor()
    
    # Original tracking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users_per_guild (
        "user_id" INTEGER,
        "warnings_count" INTEGER DEFAULT 0,
        "guild_id" INTEGER,
        PRIMARY KEY("user_id", "guild_id")
    )
    ''')
    
    # Detailed database log structure for time-based tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mod_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        mod_id INTEGER,
        target_id INTEGER,
        action_type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    connection.commit()
    connection.close()

create_user_table()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")

# Helper function to log actions for stats tracking
def log_moderation_action(guild_id, mod_id, target_id, action_type):
    connection = sqlite3.connect(os.path.join(BASE_DIR, "user_warnings.db"))
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO mod_logs (guild_id, mod_id, target_id, action_type) VALUES (?, ?, ?, ?)",
        (guild_id, mod_id, target_id, action_type)
    )
    connection.commit()
    connection.close()

async def log_mod_action_channel(ctx, action, target, reason="No reason provided", extra=None):
    channel = discord.utils.get(ctx.guild.text_channels, name="✨│mod-actions")

    if not channel:
        return

    embed = discord.Embed(
        title=f"🛡️ {action.upper()}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(
        name="Moderator",
        value=f"{ctx.author.mention} (`{ctx.author.id}`)",
        inline=True
    )

    embed.add_field(
        name="Target",
        value=f"{target.mention} (`{target.id}`)",
        inline=True
    )

    embed.add_field(
        name="Reason",
        value=reason,
        inline=False
    )

    if extra:
        embed.add_field(
            name="Details",
            value=extra,
            inline=False
        )

    embed.set_footer(text=f"Guild: {ctx.guild.name}")

    await channel.send(embed=embed)

# Helper utility to cleanly evaluate time duration parameters (s, m, h, d)
def parse_duration(time_str: str):
    match = re.match(r"^(\d+)([smhd])$", time_str.lower().strip())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    units_map = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    return datetime.timedelta(**{units_map[unit]: amount})

# --- REPAIRED MODERATION COMMANDS ---

@bot.command(name="help")
@commands.has_permissions(moderate_members=True)
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 Moderation Bot — Help",
        description=(
            "Here are all available moderation commands.\n"
            "Prefix: `,`\n\n"
            "**Arguments:**\n"
            "`<required>` • `(optional)`"
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🧹 Purge",
        value=(
            "`,purge <user_id> <amount>`\n"
            "Deletes up to the specified number of messages from a user.\n\n"
            "`,purge <user_id>`\n"
            "Deletes all messages from that user that can be found."
        ),
        inline=False
    )

    embed.add_field(
    name="🧹 Clean",
    value=(
        "`,clean`\n"
        "Deletes the 10 most recent messages sent by bots in the channel."
    ),
    inline=False
    )

    embed.add_field(
        name="⚠️ Warn",
        value=(
            "`,warn <user> (reason)`\n"
            "Warns a user and increases their warning count."
        ),
        inline=False
    )

    embed.add_field(
        name="🔇 Mute",
        value=(
            "`,mute <user> <duration> (reason)`\n"
            "Times out a user.\n"
            "Duration examples: `30s`, `10m`, `2h`, `7d`."
        ),
        inline=False
    )

    embed.add_field(
        name="🔊 Unmute",
        value=(
            "`,unmute <user> (reason)`\n"
            "Removes the user's timeout."
        ),
        inline=False
    )

    embed.add_field(
        name="🔒 Jail",
        value=(
            "`,jail <user> (reason)`\n"
            "Removes the user's roles and gives them the `Jailed` role."
        ),
        inline=False
    )

    embed.add_field(
        name="🔓 Unjail",
        value=(
            "`,unjail <user>`\n"
            "Removes the `Jailed` role from a user."
        ),
        inline=False
    )

    embed.add_field(
        name="🔨 Ban",
        value=(
            "`,ban <user> (reason)`\n"
            "Permanently bans a user from the server."
        ),
        inline=False
    )

    embed.add_field(
        name="🔓 Unban",
        value=(
            "`,unban <user_id> (reason)`\n"
            "Unbans a user using their Discord ID."
        ),
        inline=False
    )

    embed.add_field(
        name="👢 Kick",
        value=(
            "`,kick <user> (reason)`\n"
            "Kicks a user from the server."
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Moderation Stats",
        value=(
            "`,ms`\n"
            "Shows your moderation statistics.\n\n"
            "`,ms <user_id>`\n"
            "Shows another moderator's statistics, including "
            "7-day, 30-day, and all-time totals."
        ),
        inline=False
    )

    embed.add_field(
    name="🏷️ Force Nickname",
    value=(
        "`,forcenick <user> <nickname>`\n"
        "Forcefully changes a member's nickname.\n"
        "User can be specified by ID, username, or @mention."
    ),
    inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author.display_name}"
    )

    await ctx.send(embed=embed)

from datetime import datetime, timezone, timedelta

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clean(ctx):
    messages = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)

    async for message in ctx.channel.history(limit=500):
        if message.created_at < cutoff:
            break

        if message.author.bot:
            messages.append(message)

            if len(messages) >= 10:
                break

    if messages:
        await ctx.channel.delete_messages(messages)

    await ctx.message.delete()

    await log_mod_action_channel(
        ctx,
        "Clean",
        ctx.author,
        "Bot messages cleaned",
        extra=f"Bot messages deleted: `{len(messages)}`"
    )

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, user_id: int, amount: int = None):
    if amount is not None and amount <= 0:
        await ctx.send("The number of messages must be greater than 0.")
        return

    try:
        user = await bot.fetch_user(user_id)
    except discord.NotFound:
        await ctx.send("Could not find that user ID.")
        return

    def check(message):
        return message.author.id == user.id

    if amount is None:
        deleted = await ctx.channel.purge(
            limit=None,
            check=check
        )
    else:
        deleted = await ctx.channel.purge(
            limit=amount,
            check=check
        )

    await ctx.send(
        f"Deleted `{len(deleted)}` messages from {user.mention}. "
        f"Responsible Moderator: {ctx.author.mention}.",
        delete_after=5
    )
    await log_mod_action_channel(
    ctx,
    "Purge",
    user,
    "Messages purged",
    extra=f"Messages deleted: `{len(deleted)}`"
    )

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(
    ctx,
    target: discord.User,
    *,
    reason: str = "No reason provided"
):
    await ctx.guild.ban(
        target,
        reason=f"Banned by {ctx.author}: {reason}"
    )

    log_moderation_action(
        ctx.guild.id,
        ctx.author.id,
        target.id,
        "ban"
    )
    await log_mod_action_channel(
    ctx,
    "Ban",
    target,
    reason
)


    await ctx.send(
        f"{target.mention} has been banned for {reason}. "
        f"Responsible Moderator: {ctx.author.mention}."
    )

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await ctx.guild.kick(member, reason=f"Kicked by {ctx.author}: {reason}")
    log_moderation_action(ctx.guild.id, ctx.author.id, member.id, "kick")
    await ctx.send(f"{member.mention} has been kicked for {reason}, Responsible Moderator:{ctx.author.mention}.")
    await log_mod_action_channel(
    ctx,
    "Kick",
    member,
    reason
    )

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, target: discord.User, *, reason: str = "No reason provided"):
    connection = sqlite3.connect(os.path.join(BASE_DIR, "user_warnings.db"))
    cursor = connection.cursor()
    
    cursor.execute(
        "INSERT INTO users_per_guild (user_id, warnings_count, guild_id) VALUES (?, 1, ?) "
        "ON CONFLICT(user_id, guild_id) DO UPDATE SET warnings_count = warnings_count + 1",
        (target.id, ctx.guild.id)
    )
    cursor.execute("SELECT warnings_count FROM users_per_guild WHERE user_id = ? AND guild_id = ?", (target.id, ctx.guild.id))
    result = cursor.fetchone()
    total_warnings = result[0] if result else 1
    
    connection.commit()
    connection.close()
    
    log_moderation_action(ctx.guild.id, ctx.author.id, target.id, "warn")
    await ctx.send(f"{target.mention} has been warned for {reason}, Responsible Moderator {ctx.author.mention}. Total Warnings: {total_warnings}")
    await log_mod_action_channel(
    ctx,
    "Warn",
    target,
    reason,
    extra=f"Total Warnings: `{total_warnings}`"
    )

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, limit: str, *, reason: str = "No reason provided"):
    duration = parse_duration(limit)
    if not duration:
        await ctx.send("Invalid time format! Use numbers followed by `s` (seconds), `m` (minutes), `h` (hours), or `d` (days). Example: `30m`")
        return

    if duration > datetime.timedelta(days=28):
        await ctx.send("Discord timeouts cannot exceed 28 days.")
        return

    await member.timeout(duration, reason=reason)
    log_moderation_action(ctx.guild.id, ctx.author.id, member.id, "mute")
    await ctx.send(f"{member.mention} has been muted for {limit}. Reason: {reason}.Responsible Moderator: {ctx.author.mention}.")
    await log_mod_action_channel(
    ctx,
    "Mute",
    member,
    reason,
    extra=f"Duration: `{limit}`"
    )

@bot.command()
@commands.has_permissions(moderate_members=True)
async def jail(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")

    if not jail_role:
        jail_role = await ctx.guild.create_role(name="Jailed")

    roles_to_remove = [
        role for role in member.roles
        if not role.is_default() and role != jail_role
    ]

    await member.remove_roles(*roles_to_remove)
    await member.add_roles(jail_role)

    log_moderation_action(
        ctx.guild.id,
        ctx.author.id,
        member.id,
        "jail"
    )
    await log_mod_action_channel(
    ctx,
    "Jail",
    member,
    reason
   )

    await ctx.send(
        f"{member.mention} has been jailed for {reason}. "
        f"Responsible Moderator: {ctx.author.mention}."
    )  

# --- REVERSAL COMMANDS (Excluded from MS Tracking) ---

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if not member.is_timed_out():
        await ctx.send(f"{member.mention} is not currently muted.")
        return

    await member.timeout(None, reason=reason)
    await ctx.send(f"{member.mention} has been unmuted. Responsible Moderator: {ctx.author.mention}.")
    await log_mod_action_channel(
    ctx,
    "Unmute",
    member,
    reason
    )

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unjail(ctx, member: discord.Member):
    jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    
    if not jail_role or jail_role not in member.roles:
        await ctx.send(f"{member.mention} is not currently in jail.")
        return

    await member.remove_roles(jail_role)
    await ctx.send(f"{member.mention} has been released from jail. Responsible Moderator: {ctx.author.mention}.")
    await log_mod_action_channel(
    ctx,
    "Unjail",
    member,
    "Jail removed"
   )
    
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author}: {reason}")
        await ctx.send(f"{user.name} has been unbanned. Responsible Moderator: {ctx.author.mention}")
    except discord.NotFound:
        await ctx.send("User ban not found or user ID is invalid.")
    except discord.Forbidden:
        await ctx.send("I do not have permissions to unban this user.")
    await log_mod_action_channel(
    ctx,
    "Unban",
    user,
    reason
   )

# --- STATISTICS & HISTORY COMMANDS ---

@bot.command()
async def ms(ctx, user_id: int = None):
    target_id = user_id if user_id else ctx.author.id

    try:
        member = await bot.fetch_user(target_id)
    except discord.NotFound:
        await ctx.send("Could not find that user ID.")
        return

    connection = sqlite3.connect(
        os.path.join(BASE_DIR, "user_warnings.db")
    )
    cursor = connection.cursor()

    actions = ("mute", "warn", "ban", "kick", "jail")

    def get_count(action, days=None):
        if days:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM mod_logs
                WHERE mod_id = ?
                AND guild_id = ?
                AND action_type = ?
                AND timestamp >= datetime('now', ?)
                """,
                (
                    member.id,
                    ctx.guild.id,
                    action,
                    f"-{days} days"
                )
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM mod_logs
                WHERE mod_id = ?
                AND guild_id = ?
                AND action_type = ?
                """,
                (
                    member.id,
                    ctx.guild.id,
                    action
                )
            )

        result = cursor.fetchone()
        return result[0] if result else 0

    def get_total(days=None):
        return sum(get_count(action, days) for action in actions)

    embed = discord.Embed(
        title=f"Moderation Statistics — {member.display_name}",
        color=discord.Color.blue()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name=" Last 7 Days",
        value=(
            f"**Total Actions:** `{get_total(7)}`\n"
            f" Mutes: `{get_count('mute', 7)}`\n"
            f" Warns: `{get_count('warn', 7)}`\n"
            f" Bans: `{get_count('ban', 7)}`\n"
            f" Kicks: `{get_count('kick', 7)}`\n"
            f" Jails: `{get_count('jail', 7)}`"
        ),
        inline=False
    )

    embed.add_field(
        name=" Last 30 Days",
        value=(
            f"**Total Actions:** `{get_total(30)}`\n"
            f" Mutes: `{get_count('mute', 30)}`\n"
            f" Warns: `{get_count('warn', 30)}`\n"
            f" Bans: `{get_count('ban', 30)}`\n"
            f" Kicks: `{get_count('kick', 30)}`\n"
            f" Jails: `{get_count('jail', 30)}`"
        ),
        inline=False
    )

    embed.add_field(
        name=" All Time",
        value=(
            f"**Total Actions:** `{get_total()}`\n"
            f" Mutes: `{get_count('mute')}`\n"
            f" Warns: `{get_count('warn')}`\n"
            f" Bans: `{get_count('ban')}`\n"
            f" Kicks: `{get_count('kick')}`\n"
            f" Jails: `{get_count('jail')}`"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"User ID: {member.id} • Guild: {ctx.guild.name}"
    )

    connection.close()

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def forcenick(ctx, target: str, *, nickname: str):
    """Forcefully changes and locks a member's nickname."""

    target = target.strip("<@!>")

    member = None

    # Try User ID
    if target.isdigit():
        member = ctx.guild.get_member(int(target))

    # Try username/display name
    if member is None:
        member = discord.utils.find(
            lambda m: (
                m.name.lower() == target.lower()
                or m.display_name.lower() == target.lower()
            ),
            ctx.guild.members
        )

    if member is None:
        await ctx.send("❌ I couldn't find that member.")
        return

    if len(nickname) > 32:
        await ctx.send("❌ Nicknames cannot be longer than 32 characters.")
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send(
            "❌ I can't change this user's nickname because their highest "
            "role is equal to or higher than my highest role."
        )
        return

    old_nickname = member.nick or member.name

    try:
        # Change nickname immediately
        await member.edit(
            nick=nickname,
            reason=f"Forced nickname by {ctx.author}"
        )

        # Save the forced nickname
        connection = sqlite3.connect(
            os.path.join(BASE_DIR, "user_warnings.db")
        )
        cursor = connection.cursor()

        cursor.execute(
            '''
            INSERT INTO forced_nicknames (guild_id, user_id, nickname)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET nickname = excluded.nickname
            ''',
            (ctx.guild.id, member.id, nickname)
        )

        connection.commit()
        connection.close()

        # Moderation database log
        log_moderation_action(
            ctx.guild.id,
            ctx.author.id,
            member.id,
            "forcenick"
        )

        # Mod-actions channel log
        await log_mod_action_channel(
            ctx,
            "Force Nickname",
            member,
            reason="Nickname forcibly locked",
            extra=(
                f"Old nickname: `{old_nickname}`\n"
                f"Forced nickname: `{nickname}`"
            )
        )

        await ctx.send(
            f"✅ {member.mention}'s nickname has been forced to "
            f"`{nickname}`.\n"
            f"Responsible Moderator: {ctx.author.mention}"
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to change this user's nickname."
        )

    except discord.HTTPException as e:
        await ctx.send(
            f"❌ Discord rejected the nickname change: `{e}`"
        )

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def unforcenick(ctx, target: str):
    """Removes a member's forced nickname."""

    target = target.strip("<@!>")

    member = None

    # Try User ID
    if target.isdigit():
        member = ctx.guild.get_member(int(target))

    # Try username/display name
    if member is None:
        member = discord.utils.find(
            lambda m: (
                m.name.lower() == target.lower()
                or m.display_name.lower() == target.lower()
            ),
            ctx.guild.members
        )

    if member is None:
        await ctx.send("❌ I couldn't find that member.")
        return

    connection = sqlite3.connect(
        os.path.join(BASE_DIR, "user_warnings.db")
    )
    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT nickname
        FROM forced_nicknames
        WHERE guild_id = ? AND user_id = ?
        ''',
        (ctx.guild.id, member.id)
    )

    result = cursor.fetchone()

    if not result:
        connection.close()
        await ctx.send(
            f"❌ {member.mention} doesn't have a forced nickname."
        )
        return

    forced_nickname = result[0]

    cursor.execute(
        '''
        DELETE FROM forced_nicknames
        WHERE guild_id = ? AND user_id = ?
        ''',
        (ctx.guild.id, member.id)
    )

    connection.commit()
    connection.close()

    # Log the removal
    await log_mod_action_channel(
        ctx,
        "Unforce Nickname",
        member,
        reason="Forced nickname removed",
        extra=f"Removed forced nickname: `{forced_nickname}`"
    )

    await ctx.send(
        f"Removed the forced nickname from {member.mention}.\n"
        f"They can now change their nickname normally."
    )

@bot.command()
async def light(ctx):
    await ctx.send("Light is the most good-looking person that has ever existed ✨")

@bot.command()
async def winter(ctx):
    await ctx.send("Winter, mostly known as Wintersoul, is Light's kitten")

@bot.command()
async def ily(ctx):
    await ctx.send("Ily too <3")

@bot.command()
async def drake(ctx):
    await ctx.send("Out in the six i'm a national treasure")

@bot.command()
async def Kendrick(ctx):
    await ctx.send("They not like us")

@bot.command()
async def phantom(ctx):
    await ctx.send("Auntie")

@bot.command()
async def diddle(ctx):
    await ctx.send("Winter")

@bot.command()
async def help_me(ctx):
    await ctx.send("You need to ask Light for help, he is the most good-looking person that has ever existed ✨")

@bot.command()
async def potato(ctx):
    await ctx.send("Potatoes")

@bot.command()
async def daksh(ctx):
    await ctx.send("Daksh is a very good boy")

@bot.command()
async def iamnoob(ctx):
    await ctx.send("lol")

@bot.event
async def Isphantomauntie(ctx):
    await ctx.send("Yes, Phantom is a middle-aged auntie")

@bot.event
async def whoismizi(ctx):
    await ctx.send("GAY")

@bot.event
@commands.has_permissions(administrator=True)
async def potatoes(ctx):
    await ctx.send("Love")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")

@bot.event
async def on_member_update(before, after):
    # Only care if their nickname actually changed
    if before.nick == after.nick:
        return

    connection = sqlite3.connect(
        os.path.join(BASE_DIR, "user_warnings.db")
    )
    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT nickname
        FROM forced_nicknames
        WHERE guild_id = ? AND user_id = ?
        ''',
        (after.guild.id, after.id)
    )

    result = cursor.fetchone()
    connection.close()

    # No forced nickname for this user
    if not result:
        return

    forced_nickname = result[0]

    # Already has the correct nickname
    if after.nick == forced_nickname:
        return

    # Make sure the bot can actually edit them
    me = after.guild.me

    if not me:
        return

    if after.top_role >= me.top_role:
        return

    try:
        await after.edit(
            nick=forced_nickname,
            reason="Restoring forced nickname"
        )
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass

bot.run(TOKEN)
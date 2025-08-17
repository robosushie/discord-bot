import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import asyncio
from datetime import datetime, timedelta
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://localhost:8000/api/verify-discord')
API_KEY = os.getenv('SECRET_KEY')  # Use the same SECRET_KEY from backend
MEMBER_ROLE_NAME = os.getenv('MEMBER_ROLE_NAME', 'Member')
VERIFICATION_TIMEOUT = int(os.getenv('VERIFICATION_TIMEOUT', '300'))  # 5 minutes default

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store pending verifications {user_id: {'guild_id': int, 'join_time': datetime}}
pending_verifications = {}

class VerificationModal(discord.ui.Modal, title='🔐 Server Verification Required'):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    email = discord.ui.TextInput(
        label='📧 Email Address',
        placeholder='Enter your registered email address...',
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )

    verification_code = discord.ui.TextInput(
        label='🔑 Verification Code',
        placeholder='Enter your verification token...',
        required=True,
        max_length=20,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Show typing indicator
        async with interaction.followup.typing():
            # Call the API endpoint
            verification_result = await verify_user(
                self.email.value, 
                self.verification_code.value, 
                str(self.user_id)
            )
            
            if verification_result['success']:
                # Verification successful - assign Member role
                member_role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE_NAME)
                
                if member_role:
                    try:
                        # Add Member role
                        await interaction.user.add_roles(member_role)
                        
                        # Remove from pending verifications
                        if self.user_id in pending_verifications:
                            del pending_verifications[self.user_id]
                        
                        # Send success message
                        embed = discord.Embed(
                            title="✅ Welcome to the Server!",
                            description="Your email has been verified successfully. You now have full access to the server!",
                            color=0x00ff00
                        )
                        embed.add_field(
                            name="🎉 What's next:",
                            value="• Explore all the channels\n• Read the server rules\n• Introduce yourself\n• Have fun!",
                            inline=False
                        )
                        embed.set_footer(text=f"Welcome, {interaction.user.display_name}!")
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        
                        print(f"✅ User {interaction.user} ({self.user_id}) verified successfully")
                        
                    except discord.Forbidden:
                        await interaction.followup.send(
                            "❌ Bot permission error. Please contact a server administrator.",
                            ephemeral=True
                        )
                    except Exception as e:
                        print(f"Error assigning role: {e}")
                        await interaction.followup.send(
                            "❌ An error occurred. Please contact a server administrator.",
                            ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        f"❌ The '{MEMBER_ROLE_NAME}' role doesn't exist. Please contact a server administrator.",
                        ephemeral=True
                    )
            else:
                # Verification failed - kick the user
                embed = discord.Embed(
                    title="❌ Verification Failed",
                    description="Unable to verify your email and token.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🚫 You will be removed from the server",
                    value="Contact the server administrator if you believe this is an error.",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Wait a moment for user to see message, then kick
                await asyncio.sleep(3)
                try:
                    await interaction.user.kick(reason=f"Verification failed: {verification_result['message']}")
                    print(f"❌ Kicked user {interaction.user} ({self.user_id}) - verification failed")
                except discord.Forbidden:
                    print(f"❌ Cannot kick user {interaction.user} - insufficient permissions")
                except Exception as e:
                    print(f"❌ Error kicking user: {e}")
                
                # Remove from pending
                if self.user_id in pending_verifications:
                    del pending_verifications[self.user_id]

class VerificationView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=VERIFICATION_TIMEOUT)
        self.user_id = user_id

    @discord.ui.button(
        label='Verify Email & Token', 
        style=discord.ButtonStyle.primary, 
        emoji='🔐'
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This verification is not for you.", 
                ephemeral=True
            )
            return
        
        modal = VerificationModal(self.user_id)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        # User didn't verify in time - kick them
        if self.user_id in pending_verifications:
            guild_id = pending_verifications[self.user_id]['guild_id']
            guild = bot.get_guild(guild_id)
            
            if guild:
                member = guild.get_member(self.user_id)
                if member:
                    try:
                        await member.kick(reason="Verification timeout - did not verify within time limit")
                        print(f"⏰ Kicked user {member} ({self.user_id}) - verification timeout")
                    except discord.Forbidden:
                        print(f"❌ Cannot kick user {member} - insufficient permissions")
                    except Exception as e:
                        print(f"❌ Error kicking user on timeout: {e}")
            
            del pending_verifications[self.user_id]

async def verify_user(email: str, verification_code: str, discord_user_id: str) -> dict:
    """Send verification request to the API endpoint"""
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    }
    
    payload = {
        'email': email,
        'token': verification_code,  # Changed to match backend API
        'discord_user_id': discord_user_id
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_ENDPOINT, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get('success') or result.get('verified') or result.get('valid'):
                        return {
                            'success': True,
                            'message': result.get('message', 'Verification successful')
                        }
                    else:
                        return {
                            'success': False,
                            'message': result.get('message', 'Invalid verification code or email')
                        }
                
                elif response.status == 400:
                    error_data = await response.json()
                    return {
                        'success': False,
                        'message': error_data.get('message', 'Invalid verification code or email')
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Server error (Status: {response.status})'
                    }
                    
    except aiohttp.ClientTimeout:
        return {
            'success': False,
            'message': 'Request timeout'
        }
    except Exception as e:
        print(f"API request error: {e}")
        return {
            'success': False,
            'message': 'Network error'
        }

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} has logged in!')
    print(f'📡 Connected to {len(bot.guilds)} guild(s)')
    print(f'⏰ Verification timeout: {VERIFICATION_TIMEOUT} seconds')
    
    # Start cleanup task
    cleanup_expired_verifications.start()
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_member_join(member):
    """Trigger verification immediately when someone joins"""
    print(f"👤 New member joined: {member} ({member.id})")
    
    # Check if user already has Member role (shouldn't happen, but just in case)
    member_role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE_NAME)
    if member_role and member_role in member.roles:
        print(f"✅ User {member} already has Member role")
        return
    
    # Add to pending verifications
    pending_verifications[member.id] = {
        'guild_id': member.guild.id,
        'join_time': datetime.now()
    }
    
    # Create verification embed
    embed = discord.Embed(
        title="🔐 Verification Required",
        description=f"Welcome to **{member.guild.name}**!\n\nTo gain access to this server, you must verify your email and token within **{VERIFICATION_TIMEOUT // 60} minutes**.",
        color=0xff9900
    )
    
    embed.add_field(
        name="⚠️ Important:",
        value="• You will be **removed** from the server if you don't verify\n• Contact server administrator if you need help\n• Click the button below to start verification",
        inline=False
    )
    
    embed.add_field(
        name="📋 What you need:",
        value="• Your registered email address\n• Your verification token/code",
        inline=False
    )
    
    embed.set_footer(text=f"Time limit: {VERIFICATION_TIMEOUT // 60} minutes")
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    # Create verification view
    view = VerificationView(member.id)
    
    try:
        # Send DM to user
        await member.send(embed=embed, view=view)
        print(f"📨 Sent verification DM to {member}")
    except discord.Forbidden:
        # If DM fails, try to send in a verification channel or general
        verification_channel = discord.utils.get(member.guild.channels, name='verification')
        if not verification_channel:
            verification_channel = discord.utils.get(member.guild.channels, name='general')
        
        if verification_channel:
            await verification_channel.send(
                f"{member.mention} Please check your DMs for verification. If you can't receive DMs, click the button below:",
                embed=embed,
                view=view
            )
            print(f"📨 Sent verification message in channel for {member}")
        else:
            print(f"❌ Could not send verification message to {member}")

@tasks.loop(minutes=1)
async def cleanup_expired_verifications():
    """Remove users who haven't verified within the time limit"""
    current_time = datetime.now()
    expired_users = []
    
    for user_id, data in pending_verifications.items():
        if current_time - data['join_time'] > timedelta(seconds=VERIFICATION_TIMEOUT):
            expired_users.append(user_id)
    
    for user_id in expired_users:
        guild_id = pending_verifications[user_id]['guild_id']
        guild = bot.get_guild(guild_id)
        
        if guild:
            member = guild.get_member(user_id)
            if member:
                try:
                    await member.kick(reason="Verification timeout - did not verify within time limit")
                    print(f"⏰ Kicked user {member} ({user_id}) - verification timeout (cleanup)")
                except discord.Forbidden:
                    print(f"❌ Cannot kick user {member} - insufficient permissions")
                except Exception as e:
                    print(f"❌ Error kicking user in cleanup: {e}")
        
        del pending_verifications[user_id]

# Admin commands
@bot.tree.command(name="verification_status", description="Check pending verifications (Admin only)")
async def verification_status(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only command.", ephemeral=True)
        return
    
    if not pending_verifications:
        await interaction.response.send_message("✅ No pending verifications.", ephemeral=True)
        return
    
    embed = discord.Embed(title="📋 Pending Verifications", color=0xff9900)
    
    for user_id, data in pending_verifications.items():
        member = interaction.guild.get_member(user_id)
        if member:
            time_left = VERIFICATION_TIMEOUT - (datetime.now() - data['join_time']).seconds
            embed.add_field(
                name=f"{member.display_name}",
                value=f"Time left: {time_left // 60}m {time_left % 60}s",
                inline=True
            )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="force_verify", description="Manually verify a user (Admin only)")
async def force_verify(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only command.", ephemeral=True)
        return
    
    member_role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE_NAME)
    if not member_role:
        await interaction.response.send_message(f"❌ '{MEMBER_ROLE_NAME}' role not found.", ephemeral=True)
        return
    
    try:
        await member.add_roles(member_role)
        if member.id in pending_verifications:
            del pending_verifications[member.id]
        
        await interaction.response.send_message(f"✅ Manually verified {member.mention}", ephemeral=True)
        print(f"👑 Admin {interaction.user} manually verified {member}")
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="set_timeout", description="Set verification timeout in minutes (Admin only)")
async def set_timeout(interaction: discord.Interaction, minutes: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only command.", ephemeral=True)
        return
    
    if minutes < 1 or minutes > 60:
        await interaction.response.send_message("❌ Timeout must be between 1 and 60 minutes.", ephemeral=True)
        return
    
    global VERIFICATION_TIMEOUT
    VERIFICATION_TIMEOUT = minutes * 60
    
    await interaction.response.send_message(f"✅ Verification timeout set to {minutes} minutes.", ephemeral=True)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Command error: {error}")

async def start_discord_bot():
    """Start the Discord bot"""
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN environment variable is required!")
        return
    
    if not API_KEY:
        print("❌ SECRET_KEY environment variable is required!")
        return
    
    print("🚀 Starting Discord bot...")
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Failed to start Discord bot: {e}")

# For standalone bot usage
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Please set your DISCORD_TOKEN environment variable")
    elif not API_KEY:
        print("❌ Please set your SECRET_KEY environment variable")
    else:
        print("🚀 Starting private Discord verification bot...")
        print(f"⏰ Users have {VERIFICATION_TIMEOUT // 60} minutes to verify")
        asyncio.run(start_discord_bot()) 
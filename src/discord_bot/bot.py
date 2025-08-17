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
MEMBER_ROLE_NAME = os.getenv('MEMBER_ROLE_NAME', 'member')
UNVERIFIED_ROLE_NAME = os.getenv('UNVERIFIED_ROLE_NAME', 'unverified')
VERIFICATION_CHANNEL_NAME = os.getenv('VERIFICATION_CHANNEL_NAME', 'verification')
VERIFICATION_TIMEOUT = int(os.getenv('VERIFICATION_TIMEOUT', '300'))  # 5 minutes default

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store pending verifications {user_id: {'guild_id': int, 'join_time': datetime, 'message_id': int}}
pending_verifications = {}

class VerificationModal(discord.ui.Modal, title='🔐 Email & Token Verification'):
    def __init__(self, user_id: int, guild_id: int):
        super().__init__()
        self.user_id = user_id
        self.guild_id = guild_id

    email = discord.ui.TextInput(
        label='📧 Email Address',
        placeholder='Enter your registered email address...',
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )

    verification_code = discord.ui.TextInput(
        label='🔑 Verification Token',
        placeholder='Enter your verification token/code...',
        required=True,
        max_length=20,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Only allow the intended user to submit
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This verification is not for you.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        print(f"🔍 Verifying user {interaction.user} with email: {self.email.value}")
        
        # Call the API endpoint
        verification_result = await verify_user(
            self.email.value, 
            self.verification_code.value, 
            str(self.user_id)
        )
        
        print(f"🔍 API Response: {verification_result}")
        
        if verification_result['success']:
            # Verification successful
            guild = bot.get_guild(self.guild_id)
            member = guild.get_member(self.user_id) if guild else None
            
            if member:
                member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
                unverified_role = discord.utils.get(guild.roles, name=UNVERIFIED_ROLE_NAME)
                
                try:
                    # Add Member role and remove Unverified role
                    if member_role:
                        await member.add_roles(member_role)
                        print(f"✅ Added {MEMBER_ROLE_NAME} role to {member}")
                    
                    if unverified_role and unverified_role in member.roles:
                        await member.remove_roles(unverified_role)
                        print(f"🗑️ Removed {UNVERIFIED_ROLE_NAME} role from {member}")
                    
                    # Remove from pending verifications
                    if self.user_id in pending_verifications:
                        del pending_verifications[self.user_id]
                    
                    # Send success message
                    embed = discord.Embed(
                        title="✅ Verification Successful!",
                        description="Welcome! You now have full access to the server.",
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="🎉 You can now:",
                        value="• Access all server channels\n• Participate in discussions\n• Enjoy the community!",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    print(f"✅ User {member} verified successfully")
                    
                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ Bot permission error. Please contact an administrator.",
                        ephemeral=True
                    )
                    print(f"❌ No permission to manage roles for {member}")
                except Exception as e:
                    print(f"❌ Error managing roles: {e}")
                    await interaction.followup.send(
                        "❌ An error occurred. Please contact an administrator.",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "❌ User not found. Please try again.",
                    ephemeral=True
                )
        else:
            # Verification failed - kick the user
            print(f"❌ Verification failed for {interaction.user}: {verification_result['message']}")
            
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="Your email and token could not be verified.",
                color=0xff0000
            )
            embed.add_field(
                name="🚫 Reason:",
                value=verification_result['message'],
                inline=False
            )
            embed.add_field(
                name="⚠️ You will be removed:",
                value="Contact the server administrator if you believe this is an error.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Wait 3 seconds then kick
            await asyncio.sleep(3)
            
            guild = bot.get_guild(self.guild_id)
            member = guild.get_member(self.user_id) if guild else None
            
            if member:
                try:
                    await member.kick(reason=f"Email verification failed: {verification_result['message']}")
                    print(f"👢 Kicked {member} - verification failed: {verification_result['message']}")
                except discord.Forbidden:
                    print(f"❌ No permission to kick {member}")
                except discord.NotFound:
                    print(f"❌ User {member} not found (may have left)")
                except Exception as e:
                    print(f"❌ Error kicking {member}: {e}")
            
            # Remove from pending
            if self.user_id in pending_verifications:
                del pending_verifications[self.user_id]

class VerificationView(discord.ui.View):
    def __init__(self, user_id: int, guild_id: int):
        super().__init__(timeout=VERIFICATION_TIMEOUT)
        self.user_id = user_id
        self.guild_id = guild_id

    @discord.ui.button(
        label='🔐 Start Verification', 
        style=discord.ButtonStyle.primary, 
        emoji='✨'
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow the intended user to click
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This verification popup is not for you.", 
                ephemeral=True
            )
            return
        
        # Open the modal (popup)
        modal = VerificationModal(self.user_id, self.guild_id)
        await interaction.response.send_modal(modal)
        print(f"📝 Opened verification modal for {interaction.user}")

    async def on_timeout(self):
        # User didn't verify in time - kick them
        print(f"⏰ Verification timeout for user {self.user_id}")
        
        if self.user_id in pending_verifications:
            guild = bot.get_guild(self.guild_id)
            member = guild.get_member(self.user_id) if guild else None
            
            if member:
                try:
                    await member.kick(reason="Verification timeout - did not complete verification")
                    print(f"👢 Kicked {member} - verification timeout")
                except discord.Forbidden:
                    print(f"❌ No permission to kick {member}")
                except discord.NotFound:
                    print(f"❌ User {member} not found (may have left)")
                except Exception as e:
                    print(f"❌ Error kicking {member}: {e}")
            
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
    
    print(f"🌐 Calling API: {API_ENDPOINT}")
    print(f"📤 Payload: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_ENDPOINT, json=payload, headers=headers, timeout=30) as response:
                response_text = await response.text()
                print(f"📥 API Response Status: {response.status}")
                print(f"📥 API Response Body: {response_text}")
                
                if response.status == 200:
                    try:
                        result = await response.json()
                    except:
                        result = {"success": False, "message": "Invalid API response format"}
                    
                    # Check various success indicators
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
                
                else:
                    try:
                        error_data = await response.json()
                        error_message = error_data.get('message', f'Server error (Status: {response.status})')
                    except:
                        error_message = f'Server error (Status: {response.status})'
                    
                    return {
                        'success': False,
                        'message': error_message
                    }
                    
    except aiohttp.ClientTimeout:
        print("❌ API request timeout")
        return {
            'success': False,
            'message': 'Request timeout'
        }
    except Exception as e:
        print(f"❌ API request error: {e}")
        return {
            'success': False,
            'message': f'Network error: {str(e)}'
        }

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} has logged in!')
    print(f'📡 Connected to {len(bot.guilds)} guild(s)')
    print(f'⏰ Verification timeout: {VERIFICATION_TIMEOUT} seconds')
    print(f'🔑 API Endpoint: {API_ENDPOINT}')
    
    # Start cleanup task
    cleanup_expired_verifications.start()
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_member_join(member):
    """Show verification popup immediately when someone joins"""
    print(f"👤 New member joined: {member} ({member.id}) in {member.guild.name}")
    
    # Check if user already has Member role
    member_role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE_NAME)
    if member_role and member_role in member.roles:
        print(f"✅ User {member} already has {MEMBER_ROLE_NAME} role")
        return
    
    # Add Unverified role if it exists
    unverified_role = discord.utils.get(member.guild.roles, name=UNVERIFIED_ROLE_NAME)
    if unverified_role:
        try:
            await member.add_roles(unverified_role)
            print(f"🏷️ Added {UNVERIFIED_ROLE_NAME} role to {member}")
        except discord.Forbidden:
            print(f"❌ No permission to add {UNVERIFIED_ROLE_NAME} role to {member}")
    
    # Find verification channel
    verification_channel = discord.utils.get(member.guild.channels, name=VERIFICATION_CHANNEL_NAME)
    if not verification_channel:
        print(f"❌ Verification channel '{VERIFICATION_CHANNEL_NAME}' not found")
        return
    
    # Add to pending verifications
    pending_verifications[member.id] = {
        'guild_id': member.guild.id,
        'join_time': datetime.now()
    }
    
    # Create verification embed (like terms & conditions popup)
    embed = discord.Embed(
        title="🔐 Email Verification Required",
        description=f"**Welcome to {member.guild.name}!**\n\nTo access this server, you must verify your email and token within **{VERIFICATION_TIMEOUT // 60} minutes**.",
        color=0x0099ff
    )
    
    embed.add_field(
        name="📋 What you need:",
        value="• Your registered **email address**\n• Your **verification token/code**",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Important:",
        value="• Click the button below to start verification\n• You will be **removed** if you don't verify\n• Contact administrator if you need help",
        inline=False
    )
    
    embed.set_footer(text=f"⏰ Time limit: {VERIFICATION_TIMEOUT // 60} minutes • You must verify to stay")
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    # Create verification view with popup button
    view = VerificationView(member.id, member.guild.id)
    
    try:
        # Send verification message in verification channel
        message = await verification_channel.send(
            f"🚨 {member.mention} **Verification Required!**",
            embed=embed, 
            view=view
        )
        
        # Store message ID for cleanup
        pending_verifications[member.id]['message_id'] = message.id
        
        print(f"📨 Posted verification popup for {member} in #{verification_channel.name}")
        
    except discord.Forbidden:
        print(f"❌ No permission to send message in #{verification_channel.name}")
    except Exception as e:
        print(f"❌ Error sending verification message: {e}")

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
                    await member.kick(reason="Verification timeout - did not complete verification within time limit")
                    print(f"👢 Kicked {member} - verification timeout (cleanup)")
                except discord.Forbidden:
                    print(f"❌ No permission to kick {member}")
                except discord.NotFound:
                    print(f"❌ User {member} not found")
                except Exception as e:
                    print(f"❌ Error kicking {member}: {e}")
        
        del pending_verifications[user_id]

# Admin commands
@bot.tree.command(name="setup_roles", description="Create required verification roles (Admin only)")
async def setup_roles(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only command.", ephemeral=True)
        return
    
    guild = interaction.guild
    created_roles = []
    
    # Create Member role if doesn't exist
    member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
    if not member_role:
        try:
            member_role = await guild.create_role(
                name=MEMBER_ROLE_NAME,
                color=discord.Color.green(),
                reason="Verification system setup"
            )
            created_roles.append(MEMBER_ROLE_NAME)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating {MEMBER_ROLE_NAME} role: {e}", ephemeral=True)
            return
    
    # Create Unverified role if doesn't exist
    unverified_role = discord.utils.get(guild.roles, name=UNVERIFIED_ROLE_NAME)
    if not unverified_role:
        try:
            unverified_role = await guild.create_role(
                name=UNVERIFIED_ROLE_NAME,
                color=discord.Color.red(),
                reason="Verification system setup"
            )
            created_roles.append(UNVERIFIED_ROLE_NAME)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating {UNVERIFIED_ROLE_NAME} role: {e}", ephemeral=True)
            return
    
    message = "✅ Verification roles setup complete!\n\n"
    if created_roles:
        message += f"**Created roles:** {', '.join(created_roles)}\n"
    message += f"**Existing roles:** Member role exists, Unverified role exists\n\n"
    message += "**Next steps:**\n"
    message += f"1. Move bot role above {MEMBER_ROLE_NAME} and {UNVERIFIED_ROLE_NAME} in role hierarchy\n"
    message += f"2. Create #{VERIFICATION_CHANNEL_NAME} channel\n"
    message += "3. Remove @everyone permissions from channels, give access to @Member only"
    
    await interaction.response.send_message(message, ephemeral=True)

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
            time_elapsed = (datetime.now() - data['join_time']).seconds
            time_left = max(0, VERIFICATION_TIMEOUT - time_elapsed)
            embed.add_field(
                name=f"{member.display_name}",
                value=f"⏰ {time_left // 60}m {time_left % 60}s left",
                inline=True
            )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="force_verify", description="Manually verify a user (Admin only)")
async def force_verify(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only command.", ephemeral=True)
        return
    
    member_role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE_NAME)
    unverified_role = discord.utils.get(interaction.guild.roles, name=UNVERIFIED_ROLE_NAME)
    
    if not member_role:
        await interaction.response.send_message(f"❌ '{MEMBER_ROLE_NAME}' role not found.", ephemeral=True)
        return
    
    try:
        await member.add_roles(member_role)
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        
        if member.id in pending_verifications:
            del pending_verifications[member.id]
        
        await interaction.response.send_message(f"✅ Manually verified {member.mention}", ephemeral=True)
        print(f"👑 Admin {interaction.user} manually verified {member}")
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="test_api", description="Test API endpoint (Admin only)")
async def test_api(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Test API with dummy data
    result = await verify_user("test@example.com", "123456", "123456789")
    
    embed = discord.Embed(title="🧪 API Test Results", color=0x0099ff)
    embed.add_field(name="Endpoint", value=API_ENDPOINT, inline=False)
    embed.add_field(name="Success", value=str(result['success']), inline=True)
    embed.add_field(name="Message", value=result['message'], inline=True)
    
    await interaction.followup.send(embed=embed, ephemeral=True)

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
        print(f"📍 Verification channel: #{VERIFICATION_CHANNEL_NAME}")
        asyncio.run(start_discord_bot()) 
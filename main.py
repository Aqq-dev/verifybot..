import discord
from discord.ext import commands
from discord import app_commands
import os, json, requests
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
BOT_TOKEN = TOKEN

def load_tokens():
    with open("access_tokens.json", "r") as f:
        return json.load(f)

def save_tokens(data):
    with open("access_tokens.json", "w") as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)

@bot.tree.command(name="verify")
@app_commands.describe(role="認証で付与するロール")
async def verify(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title="認証", description="下のボタンを押して認証を進めてください。", color=discord.Color.random())
    view = discord.ui.View()
    button = discord.ui.Button(label="認証する", url=f"https://your-render-url.onrender.com/oauth?uid={interaction.user.id}&role={role.id}")
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="call")
@app_commands.describe(user_id="復元したいユーザーのID")
async def call(interaction: discord.Interaction, user_id: str):
    tokens = load_tokens()
    access_token = tokens.get(user_id)
    if not access_token:
        await interaction.response.send_message("❌ アクセストークンが見つかりません。", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    res = requests.put(
        f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}",
        headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"},
        json={"access_token": access_token}
    )

    if res.status_code in [200, 201, 204]:
        await interaction.response.send_message("✅ ユーザーをこのサーバーに追加しました。", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ 追加に失敗しました: {res.status_code}", ephemeral=True)

keep_alive()
bot.run(TOKEN)

import os
import sqlite3
import re
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# .envの読み込み
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# データベースファイル名
DB_FILE = 'hage_counter.db'

# Lv.2 禿判定用正規表現
# 語尾、絵文字、関連ワードを網羅 (.env の HAGE_WORDS でカスタム可能)
DEFAULT_HAGE_WORDS = r"ハゲ|はげ|禿|薄毛|毛根|むしり|ピカピカ|眩しい|光ってる|ツルツル|👨‍🦲|👴|🥚|🌞"
hage_words = os.getenv('HAGE_WORDS', DEFAULT_HAGE_WORDS)
RE_HAGE = re.compile(rf'({hage_words})')

class HageBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # データベース初期化
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS hage_counts
                     (guild_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
                     PRIMARY KEY(guild_id, user_id))''')
        conn.commit()
        conn.close()
        # スラッシュコマンドを同期
        await self.tree.sync()
        print("Hage system online. Commands synced.")

bot = HageBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # メッセージが禿パターンにマッチするか判定
    if RE_HAGE.search(message.content):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''INSERT INTO hage_counts (guild_id, user_id, count)
                     VALUES (?, ?, 1)
                     ON CONFLICT(guild_id, user_id) 
                     DO UPDATE SET count = count + 1''', 
                  (message.guild.id, message.author.id))
        conn.commit()
        conn.close()

        # 禿検知のリアクション
        try:
            await message.add_reaction('👨‍🦲')
        except discord.Forbidden:
            pass

    await bot.process_commands(message)

# --- スラッシュコマンド ---

@bot.tree.command(name="count", description="指定ユーザー（または自分）の禿カウントを確認します")
@app_commands.describe(user="確認したいユーザー")
async def hage_count(interaction: discord.Interaction, user: discord.Member = None):
    target_user = user or interaction.user
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT count FROM hage_counts WHERE guild_id = ? AND user_id = ?', 
              (interaction.guild.id, target_user.id))
    result = c.fetchone()
    conn.close()

    count_val = result[0] if result else 0
    await interaction.response.send_message(
        f'{target_user.display_name} さんの通算ハゲ回数: **{count_val}回** です。👨‍🦲'
    )

@bot.tree.command(name="ranking", description="サーバー内の禿ランキングを表示します")
async def hage_ranking(interaction: discord.Interaction):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT user_id, count FROM hage_counts 
                 WHERE guild_id = ? AND count > 0 
                 ORDER BY count DESC LIMIT 10''', 
              (interaction.guild.id,))
    results = c.fetchall()
    conn.close()

    if not results:
        await interaction.response.send_message("まだ禿はいません。フサフサなサーバーです。")
        return

    embed = discord.Embed(title="👨‍🦲 禿ランキング (Top 10)", color=0xf1c40f) # 輝くゴールド
    description = ""
    for i, (u_id, val) in enumerate(results, 1):
        # 1位には王冠を授与
        medal = "👑" if i == 1 else f"{i}位"
        description += f"**{medal}:** <@{u_id}> — `{val}回` \n"
    
    embed.description = description
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
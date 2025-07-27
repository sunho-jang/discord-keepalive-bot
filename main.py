import discord
from discord import app_commands
from discord.ext import tasks
from discord.ui import View, Select
from datetime import datetime, timedelta
import json
import os
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

DATA_FILE = "boss_data.json"
boss_data = {}

# JSON 저장/로드
def load_data():
    global boss_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            boss_data = json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(boss_data, f, ensure_ascii=False, indent=2)

# 수요일 06시마다 클리어 초기화
@tasks.loop(minutes=1)
async def reset_task():
    now = datetime.utcnow() + timedelta(hours=9)
    if now.weekday() == 2 and now.hour == 6 and now.minute == 0:
        for user_id in boss_data:
            for char in boss_data[user_id]:
                for boss in boss_data[user_id][char]:
                    boss_data[user_id][char][boss] = False
        save_data()
        print("🔄 수요일 06시 클리어 상태 초기화 완료")

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 봇 로그인: {bot.user}")
    load_data()
    reset_task.start()

# 캐릭터 추가
@tree.command(name="addchar", description="내 캐릭터를 추가합니다")
@app_commands.describe(character="캐릭터 이름")
async def addchar(interaction: discord.Interaction, character: str):
    uid = str(interaction.user.id)
    boss_data.setdefault(uid, {})
    if character in boss_data[uid]:
        await interaction.response.send_message("⚠️ 이미 있는 캐릭터입니다", ephemeral=True)
    else:
        boss_data[uid][character] = {}
        save_data()
        await interaction.response.send_message(f"➕ '{character}' 추가됨", ephemeral=True)

# 보스 추가
@tree.command(name="addboss", description="캐릭터에 보스를 추가합니다")
@app_commands.describe(character="캐릭터 이름", boss="보스 이름")
async def addboss(interaction: discord.Interaction, character: str, boss: str):
    uid = str(interaction.user.id)
    if character not in boss_data.get(uid, {}):
        await interaction.response.send_message("❗ 캐릭터가 없습니다", ephemeral=True)
        return
    bosses = boss_data[uid][character]
    boss_data[uid][character] = {boss: False, **bosses}  # 새 보스를 맨 위에
    save_data()
    await interaction.response.send_message(f"➕ 보스 '{boss}' 추가됨", ephemeral=True)

# 캐릭터 제거
@tree.command(name="removechar", description="캐릭터를 제거합니다")
@app_commands.describe(character="캐릭터 이름")
async def removechar(interaction: discord.Interaction, character: str):
    uid = str(interaction.user.id)
    if character in boss_data.get(uid, {}):
        del boss_data[uid][character]
        save_data()
        await interaction.response.send_message(f"🗑 '{character}' 제거됨", ephemeral=True)
    else:
        await interaction.response.send_message("❗ 해당 캐릭터가 없습니다", ephemeral=True)

# 보스 제거
@tree.command(name="removeboss", description="보스를 제거합니다")
@app_commands.describe(character="캐릭터 이름", boss="보스 이름")
async def removeboss(interaction: discord.Interaction, character: str, boss: str):
    uid = str(interaction.user.id)
    try:
        del boss_data[uid][character][boss]
        save_data()
        await interaction.response.send_message(f"🗑 보스 '{boss}' 제거됨", ephemeral=True)
    except:
        await interaction.response.send_message("❗ 해당 보스를 찾을 수 없습니다", ephemeral=True)

# 명령어 방식 클리어
@tree.command(name="clear", description="보스를 완료/미완료 상태로 토글합니다")
@app_commands.describe(character="캐릭터 이름", boss="보스 이름")
async def clear(interaction: discord.Interaction, character: str, boss: str):
    uid = str(interaction.user.id)
    try:
        current = boss_data[uid][character][boss]
        boss_data[uid][character][boss] = not current
        save_data()
        status = '✅ 완료' if not current else '❌ 미완료'
        await interaction.response.send_message(f"{character} - {boss}: {status} 처리됨", ephemeral=True)
    except:
        await interaction.response.send_message("❗ 캐릭터 또는 보스를 찾을 수 없습니다", ephemeral=True)

# 드롭다운 기반 클리어
class ClearDropdown(Select):
    def __init__(self, user_id):
        self.user_id = str(user_id)
        options = []
        for char, bosses in boss_data.get(self.user_id, {}).items():
            for boss, status in bosses.items():
                label = f"{char} - {boss}"
                emoji = "✅" if status else "❌"
                options.append(discord.SelectOption(label=label, description="클릭 시 상태 토글", emoji=emoji))
        super().__init__(placeholder="캐릭터-보스 선택", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        label = self.values[0]
        char, boss = label.split(" - ")
        current = boss_data[self.user_id][char][boss]
        boss_data[self.user_id][char][boss] = not current
        save_data()
        status = "✅ 완료" if not current else "❌ 미완료"
        await interaction.response.send_message(f"{char} - {boss}: {status} 처리됨", ephemeral=True)

class ClearView(View):
    def __init__(self, user_id):
        super().__init__()
        self.add_item(ClearDropdown(user_id))

@tree.command(name="clearselect", description="드롭다운으로 보스 상태를 변경합니다")
async def clearselect(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid not in boss_data or not boss_data[uid]:
        await interaction.response.send_message("📭 등록된 캐릭터와 보스가 없습니다", ephemeral=True)
        return
    await interaction.response.send_message("드롭다운에서 캐릭터와 보스를 선택하세요:", view=ClearView(uid), ephemeral=True)

# 상태 확인
@tree.command(name="status", description="보스 현황을 확인합니다")
@app_commands.describe(user="조회할 유저 (기본: 본인)")
async def status(interaction: discord.Interaction, user: discord.User = None):
    uid = str((user or interaction.user).id)
    name = (user or interaction.user).display_name

    if uid not in boss_data or not boss_data[uid]:
        await interaction.response.send_message(f"📭 {name}의 데이터가 없습니다", ephemeral=True)
        return

    embed = discord.Embed(title=f"{name}의 주간 보스 현황", color=0x00ffcc)
    for char, bosses in boss_data[uid].items():
        value = "\n".join([f"{b}: {'✅' if v else '❌'}" for b, v in bosses.items()])
        embed.add_field(name=f"🔸 {char}", value=value, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=False)

# 전체 유저 현황
@tree.command(name="status_all", description="전체 유저 현황을 확인합니다")
async def status_all(interaction: discord.Interaction):
    if not boss_data:
        await interaction.response.send_message("📭 데이터가 없습니다", ephemeral=True)
        return

    embed = discord.Embed(title="📊 전체 보스 클리어 현황", color=0x66ccff)
    for uid, chars in boss_data.items():
        user = await bot.fetch_user(int(uid))
        section = ""
        for char, bosses in chars.items():
            section += f"**[{char}]**\n" + "\n".join([f"· {b}: {'✅' if v else '❌'}" for b, v in bosses.items()]) + "\n"
        embed.add_field(name=user.display_name, value=section, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)

# 도움말
@tree.command(name="helpme", description="사용 가능한 명령어를 보여줍니다")
async def helpme(interaction: discord.Interaction):
    embed = discord.Embed(title="📘 사용 가능한 명령어", color=0xccccff)
    embed.add_field(name="/addchar [캐릭터]", value="캐릭터 추가", inline=False)
    embed.add_field(name="/addboss [캐릭터] [보스]", value="보스 추가", inline=False)
    embed.add_field(name="/removechar [캐릭터]", value="캐릭터 제거", inline=False)
    embed.add_field(name="/removeboss [캐릭터] [보스]", value="보스 제거", inline=False)
    embed.add_field(name="/clear [캐릭터] [보스]", value="보스 완료/미완료 토글", inline=False)
    embed.add_field(name="/clearselect", value="드롭다운으로 보스 토글", inline=False)
    embed.add_field(name="/status [유저]", value="보스 현황 확인", inline=False)
    embed.add_field(name="/status_all", value="전체 유저 현황", inline=False)
    embed.add_field(name="/helpme", value="이 도움말 보기", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 봇 실행
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))

import os
print("🔗 예상 주소:", f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co")

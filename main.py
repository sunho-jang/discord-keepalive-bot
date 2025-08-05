import firebase_connect
from firebase_admin import db

import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import View, Select
from datetime import datetime, timedelta
import os
import json
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

boss_data = {}

# ✅ Firebase에서 불러오기
def load_data():
    global boss_data
    ref = db.reference('boss_data')
    data = ref.get()
    if data:
        boss_data = data

# ✅ Firebase에 저장
def save_data():
    ref = db.reference('boss_data')
    ref.set(boss_data)

# 주간 초기화: 매주 수요일 오전 6시
@tasks.loop(minutes=1)
async def weekly_reset():
    now = datetime.now()
    if now.weekday() == 2 and now.hour == 6 and now.minute == 0:
        for user_id in boss_data:
            for character in boss_data[user_id]:
                for boss in boss_data[user_id][character]:
                    boss_data[user_id][character][boss] = False
        save_data()
        print("✅ Weekly reset complete")

@bot.event
async def on_ready():
    load_data()
    weekly_reset.start()
    
    for guild in bot.guilds:
        try:
            await tree.sync(guild=guild)
            print(f"✅ Synced commands for {guild.name}")
        except Exception as e:
            print(f"❌ Failed to sync for {guild.name}: {e}")

    print(f'🟢 Logged in as {bot.user}')


@tree.command(name="add", description="캐릭터를 추가합니다.")
async def add_character(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    if user_id not in boss_data:
        boss_data[user_id] = {}
    if character in boss_data[user_id]:
        await interaction.response.send_message("이미 존재하는 캐릭터입니다.", ephemeral=True)
        return
    boss_data[user_id][character] = {
        "카양겔": False,
        "상아탑": False,
        "에르가시아": False,
        "발탄": False,
        "비아키스": False,
        "쿠크세이튼": False,
        "아브렐슈드": False,
        "일리아칸": False,
        "카멘": False,
        "상급 카멘": False
    }
    save_data()
    await interaction.response.send_message(f"{character} 캐릭터가 추가되었습니다.", ephemeral=True)

@tree.command(name="delete", description="캐릭터를 삭제합니다.")
async def delete_character(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    if user_id in boss_data and character in boss_data[user_id]:
        del boss_data[user_id][character]
        save_data()
        await interaction.response.send_message(f"{character} 캐릭터가 삭제되었습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("해당 캐릭터를 찾을 수 없습니다.", ephemeral=True)

@tree.command(name="clear", description="보스 클리어 상태를 토글합니다.")
async def clear_boss(interaction: discord.Interaction, character: str, boss: str):
    user_id = str(interaction.user.id)
    if user_id in boss_data and character in boss_data[user_id] and boss in boss_data[user_id][character]:
        boss_data[user_id][character][boss] = not boss_data[user_id][character][boss]
        save_data()
        state = "✅ 클리어" if boss_data[user_id][character][boss] else "❌ 미클리어"
        await interaction.response.send_message(f"{character}의 {boss} 상태: {state}", ephemeral=True)
    else:
        await interaction.response.send_message("데이터를 찾을 수 없습니다.", ephemeral=True)

@tree.command(name="clearselect", description="드롭다운으로 보스를 선택하여 토글합니다.")
async def clear_boss_select(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in boss_data or not boss_data[user_id]:
        await interaction.response.send_message("먼저 캐릭터를 추가해주세요.", ephemeral=True)
        return

    class CharacterSelect(Select):
        def __init__(self):
            options = [discord.SelectOption(label=char) for char in boss_data[user_id].keys()]
            super().__init__(placeholder="캐릭터 선택", options=options)

        async def callback(self, interaction2: discord.Interaction):
            selected_character = self.values[0]

            class BossSelect(Select):
                def __init__(self):
                    options = [discord.SelectOption(label=boss, description="✅ 완료" if boss_data[user_id][selected_character][boss] else "❌ 미완료") for boss in boss_data[user_id][selected_character]]
                    super().__init__(placeholder="보스 선택", options=options)

                async def callback(self, interaction3: discord.Interaction):
                    selected_boss = self.values[0]
                    boss_data[user_id][selected_character][selected_boss] = not boss_data[user_id][selected_character][selected_boss]
                    save_data()
                    status = "✅ 클리어" if boss_data[user_id][selected_character][selected_boss] else "❌ 미클리어"
                    await interaction3.response.send_message(f"{selected_character}의 {selected_boss} 상태가 {status}로 변경되었습니다.", ephemeral=True)

            await interaction2.response.send_message("보스를 선택하세요.", view=View(BossSelect()), ephemeral=True)

    await interaction.response.send_message("캐릭터를 선택하세요.", view=View(CharacterSelect()), ephemeral=True)

@tree.command(name="status", description="자신의 보스 클리어 상태를 확인합니다.")
async def check_status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in boss_data:
        await interaction.response.send_message("등록된 캐릭터가 없습니다.", ephemeral=True)
        return

    embed = discord.Embed(title=f"{interaction.user.name}님의 캐릭터별 보스 상태", color=0x00ff00)
    for char, bosses in boss_data[user_id].items():
        value = "\n".join([f"· {boss}: {'✅' if status else '❌'}" for boss, status in bosses.items()])
        embed.add_field(name=f"[{char}]", value=value, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="status_all", description="전체 유저의 보스 클리어 현황을 확인합니다.")
async def check_all_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not boss_data:
        await interaction.followup.send("등록된 정보가 없습니다.", ephemeral=True)
        return

    embed = discord.Embed(title="전체 유저 보스 클리어 현황", color=0x3498db)
    for user_id, characters in boss_data.items():
        user = await bot.fetch_user(int(user_id))
        for char, bosses in characters.items():
            value = "\n".join([f"· {boss}: {'✅' if status else '❌'}" for boss, status in bosses.items()])
            embed.add_field(name=f"{user.name} → [{char}]", value=value, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


if "TOKEN" not in os.environ:
    print("❌ TOKEN 환경변수가 없습니다.")
else:
    print("✅ TOKEN 환경변수 존재함, 로그인 시도 중...")



keep_alive()
bot.run(os.environ['TOKEN'])



import discord
from discord.ext import commands
import os
import time
import sqlite3
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot aktif!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========================================
# VERİTABANI
# ========================================

DB_NAME = "kullanici_verileri.db"

def veritabani_kur():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ses_sureleri (
            user_id INTEGER PRIMARY KEY,
            toplam_saniye INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesaj_sayilari (
            user_id INTEGER PRIMARY KEY,
            toplam_mesaj INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

veritabani_kur()

# Aktif ses takibi
aktif_sesler = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/yardim"))
    print(f'✅ Bot hazır: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")

# ========================================
# MESAJ TAKİBİ (HER MESAJDA KAYDEDER)
# ========================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_id = message.author.id
    
    # Her mesajda veritabanına yaz
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mesaj_sayilari (user_id, toplam_mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET toplam_mesaj = toplam_mesaj + 1", (user_id,))
    conn.commit()
    conn.close()
    
    await bot.process_commands(message)

# ========================================
# SES TAKİBİ
# ========================================

@bot.event
async def on_voice_state_update(member, before, after):
    now = datetime.now()
    if before.channel is None and after.channel is not None:
        aktif_sesler[member.id] = now
    elif before.channel is not None and after.channel is None:
        if member.id in aktif_sesler:
            giris = aktif_sesler.pop(member.id)
            fark = (now - giris).seconds
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ses_sureleri (user_id, toplam_saniye) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET toplam_saniye = toplam_saniye + ?", (member.id, fark, fark))
            conn.commit()
            conn.close()
    elif before.channel != after.channel:
        if member.id in aktif_sesler:
            giris = aktif_sesler.pop(member.id)
            fark = (now - giris).seconds
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ses_sureleri (user_id, toplam_saniye) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET toplam_saniye = toplam_saniye + ?", (member.id, fark, fark))
            conn.commit()
            conn.close()
        if after.channel is not None:
            aktif_sesler[member.id] = now

# ========================================
# SLASH KOMUTLAR
# ========================================

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="yardim", description="Tüm komutları gösterir")
async def yardim(interaction: discord.Interaction):
    mesaj = "**📋 Bot Komutları**\n\n"
    mesaj += "`/ping` - Gecikme\n"
    mesaj += "`/yardim` - Bu mesaj\n"
    mesaj += "`/profil @kisi` - Kullanıcı profilini gösterir\n"
    await interaction.response.send_message(mesaj)

@bot.tree.command(name="profil", description="Kullanıcı profilini gösterir")
async def profil(interaction: discord.Interaction, kisi: discord.Member = None):
    if kisi is None:
        kisi = interaction.user
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT toplam_saniye FROM ses_sureleri WHERE user_id = ?", (kisi.id,))
    ses_sonuc = cursor.fetchone()
    toplam_saniye = ses_sonuc[0] if ses_sonuc else 0
    
    cursor.execute("SELECT toplam_mesaj FROM mesaj_sayilari WHERE user_id = ?", (kisi.id,))
    mesaj_sonuc = cursor.fetchone()
    toplam_mesaj = mesaj_sonuc[0] if mesaj_sonuc else 0
    conn.close()
    
    saat = toplam_saniye // 3600
    dakika = (toplam_saniye % 3600) // 60
    saniye = toplam_saniye % 60
    
    embed = discord.Embed(
        title=f"👤 {kisi.display_name} Profili",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    if kisi.avatar:
        embed.set_thumbnail(url=kisi.avatar.url)
    
    embed.add_field(
        name="📋 Hesap Bilgileri",
        value=f"**Kullanıcı Adı:** {kisi.name}\n**ID:** {kisi.id}\n**Katılma:** {kisi.joined_at.strftime('%d/%m/%Y %H:%M') if kisi.joined_at else 'Bilinmiyor'}",
        inline=False
    )
    
    embed.add_field(
        name="📊 İstatistikler",
        value=f"**Toplam Mesaj:** {toplam_mesaj}\n**Ses Süresi:** {saat} saat, {dakika} dakika, {saniye} saniye",
        inline=False
    )
    
    if kisi.roles:
        roller = [rol.mention for rol in kisi.roles if rol.name != "@everyone"]
        embed.add_field(
            name="🎭 Roller",
            value=", ".join(roller) if roller else "Henüz rolü yok.",
            inline=False
        )
    
    embed.set_footer(text=f"Sorgulayan: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ Token ayarlanmamış")
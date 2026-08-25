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

# Rate limit için
SON_KONTROL = {}
MESAJ_CACHE = {}

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
# MESAJ VE SES TAKİBİ
# ========================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_id = message.author.id
    now = time.time()
    
    # Rate limit: 1 saniyede 1 işlem
    if user_id in SON_KONTROL and now - SON_KONTROL[user_id] < 1:
        await bot.process_commands(message)
        return
    SON_KONTROL[user_id] = now
    
    # Mesaj sayacı (cache'li)
    if user_id not in MESAJ_CACHE:
        MESAJ_CACHE[user_id] = 0
    MESAJ_CACHE[user_id] += 1
    
    # Her 10 mesajda bir veritabanına yaz
    if MESAJ_CACHE[user_id] >= 10:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mesaj_sayilari (user_id, toplam_mesaj) VALUES (?, 10) ON CONFLICT(user_id) DO UPDATE SET toplam_mesaj = toplam_mesaj + 10", (user_id,))
        conn.commit()
        conn.close()
        MESAJ_CACHE[user_id] = 0
    
    await bot.process_commands(message)

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

@bot.tree.command(name="profil", description="Kullanıcı profilini gösterir (mesaj, ses, roller)")
async def profil(interaction: discord.Interaction, kisi: discord.Member = None):
    if kisi is None:
        kisi = interaction.user
    
    # Veritabanından bilgileri al
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT toplam_saniye FROM ses_sureleri WHERE user_id = ?", (kisi.id,))
    ses_sonuc = cursor.fetchone()
    toplam_saniye = ses_sonuc[0] if ses_sonuc else 0
    
    cursor.execute("SELECT toplam_mesaj FROM mesaj_sayilari WHERE user_id = ?", (kisi.id,))
    mesaj_sonuc = cursor.fetchone()
    toplam_mesaj = mesaj_sonuc[0] if mesaj_sonuc else 0
    conn.close()
    
    # Ses süresini formatla
    saat = toplam_saniye // 3600
    dakika = (toplam_saniye % 3600) // 60
    saniye = toplam_saniye % 60
    
    # Embed oluştur
    embed = discord.Embed(
        title=f"👤 {kisi.display_name} Profili",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if kisi.avatar:
        embed.set_thumbnail(url=kisi.avatar.url)
    
    # Hesap bilgileri
    embed.add_field(
        name="📋 Hesap Bilgileri",
        value=f"**Kullanıcı Adı:** {kisi.name}\n"
              f"**ID:** {kisi.id}\n"
              f"**Katılma Tarihi:** {kisi.joined_at.strftime('%d/%m/%Y %H:%M') if kisi.joined_at else 'Bilinmiyor'}",
        inline=False
    )
    
    # İstatistikler
    embed.add_field(
        name="📊 İstatistikler",
        value=f"**Toplam Mesaj:** {toplam_mesaj}\n"
              f"**Ses Süresi:** {saat} saat, {dakika} dakika, {saniye} saniye",
        inline=False
    )
    
    # Roller
    if kisi.roles:
        roller = [rol.mention for rol in kisi.roles if rol.name != "@everyone"]
        if roller:
            embed.add_field(
                name="🎭 Roller",
                value=", ".join(roller),
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 Roller",
                value="Henüz hiçbir rolü yok.",
                inline=False
            )
    else:
        embed.add_field(
            name="🎭 Roller",
            value="Henüz hiçbir rolü yok.",
            inline=False
        )
    
    embed.set_footer(text=f"Sorgulayan: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ========================================
# BAŞLATMA
# ========================================

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ Token ayarlanmamış")
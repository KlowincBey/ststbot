import discord
from discord.ext import commands
import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot aktif!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========================================
# VERİTABANI
# ========================================

DB_NAME = "kullanici_verileri.db"

def veritabani_kur():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Ses süreleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ses_sureleri (
            user_id INTEGER PRIMARY KEY,
            toplam_saniye INTEGER DEFAULT 0
        )
    ''')
    
    # Mesaj sayıları tablosu
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

# ========================================
# OLAYLAR
# ========================================

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!yardım"))
    print(f'✅ Bot hazır: {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Mesaj sayısını güncelle
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mesaj_sayilari (user_id, toplam_mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET toplam_mesaj = toplam_mesaj + 1", (message.author.id,))
    conn.commit()
    conn.close()
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    now = datetime.now()
    
    # Kullanıcı ses kanalına girdi
    if before.channel is None and after.channel is not None:
        aktif_sesler[member.id] = now
    
    # Kullanıcı ses kanalından çıktı
    elif before.channel is not None and after.channel is None:
        if member.id in aktif_sesler:
            giris = aktif_sesler.pop(member.id)
            fark = (now - giris).seconds
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ses_sureleri (user_id, toplam_saniye) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET toplam_saniye = toplam_saniye + ?", (member.id, fark, fark))
            conn.commit()
            conn.close()
    
    # Kanal değiştirdi
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

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"❌ Hata: {str(error)[:100]}")

# ========================================
# KOMUTLAR
# ========================================

@bot.command()
async def profil(ctx, member: discord.Member = None):
    """Kullanıcının profilini gösterir (ses süresi, mesaj sayısı, vb.)"""
    if member is None:
        member = ctx.author
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Ses süresini al
    cursor.execute("SELECT toplam_saniye FROM ses_sureleri WHERE user_id = ?", (member.id,))
    ses_sonuc = cursor.fetchone()
    toplam_saniye = ses_sonuc[0] if ses_sonuc else 0
    
    # Mesaj sayısını al
    cursor.execute("SELECT toplam_mesaj FROM mesaj_sayilari WHERE user_id = ?", (member.id,))
    mesaj_sonuc = cursor.fetchone()
    toplam_mesaj = mesaj_sonuc[0] if mesaj_sonuc else 0
    
    conn.close()
    
    # Süreyi formatla
    saat = toplam_saniye // 3600
    dakika = (toplam_saniye % 3600) // 60
    saniye = toplam_saniye % 60
    
    # Embed oluştur
    embed = discord.Embed(
        title=f"👤 {member.display_name} Profili",
        color=discord.Color.blue()
    )
    
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    
    embed.add_field(
        name="📊 İstatistikler",
        value=f"**Toplam Mesaj:** {toplam_mesaj}\n"
              f"**Ses Süresi:** {saat} saat, {dakika} dakika, {saniye} saniye",
        inline=False
    )
    
    embed.add_field(
        name="📅 Hesap Bilgileri",
        value=f"**Katılma Tarihi:** {member.joined_at.strftime('%d/%m/%Y %H:%M') if member.joined_at else 'Bilinmiyor'}\n"
              f"**Hesap Oluşturma:** {member.created_at.strftime('%d/%m/%Y %H:%M')}",
        inline=False
    )
    
    embed.add_field(
        name="🎭 Roller",
        value=", ".join([rol.mention for rol in member.roles if rol.name != "@everyone"]) or "Yok",
        inline=False
    )
    
    embed.set_footer(
        text=f"Sorgulayan: {ctx.author.display_name}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def yardım(ctx):
    await ctx.send("Komutlar:\n!profil @kisi - Kullanıcı profilini gösterir\n!ping - Gecikme")

# ========================================
# BAŞLATMA
# ========================================

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ Token ayarlanmamış!")
import discord
from discord.ext import commands
import asyncio
import os
import random
import time
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
intents.message_content = True
bot = commands.Bot(command_prefix='!s', intents=intents, help_command=None)

# ========================================
# RATE LİMİT KORUMASI
# ========================================

SON_KONTROL = {}

def rate_limit_kontrol(user_id):
    now = time.time()
    if user_id in SON_KONTROL and now - SON_KONTROL[user_id] < 1:
        return False
    SON_KONTROL[user_id] = now
    return True

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!syardım"))
    print(f'✅ Stat bot hazır: {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not rate_limit_kontrol(message.author.id):
        return
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"Hata: {str(error)[:100]}")

# ========================================
# EĞLENCE KOMUTLARI
# ========================================

@bot.command()
async def szar(ctx):
    """Zar atar (1-6)."""
    sonuc = random.randint(1, 6)
    zar_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    await ctx.send(f"Zar: {sonuc} {zar_emoji[sonuc-1]}")

@bot.command()
async def syazitura(ctx):
    """Yazı tura atar."""
    sonuc = random.choice(["Yazı", "Tura"])
    await ctx.send(f"Yazı tura: {sonuc}")

@bot.command()
async def srastgele(ctx, min: int = 1, max: int = 100):
    """Rastgele sayı üretir."""
    sayi = random.randint(min, max)
    await ctx.send(f"Rastgele sayı: {sayi}")

@bot.command()
async def sespri(ctx):
    """Rastgele espri yapar."""
    espiriler = [
        "Bir gün bir bilgisayar virüsü hastaneye gitmiş. Doktor: 'Geçmiş olsun, sende antivirüs var!'",
        "Neden matematikçiler denizde yüzemez? Çünkü sinüsleri var.",
        "İki programcı arasında geçen diyalog: 'Neden kodun çalışmıyor?' 'Bilmiyorum, belki de syntax hatası var.'",
        "Bir inek, bir tavuk ve bir at konuşuyormuş. İnek: 'Ben süt veriyorum.' Tavuk: 'Ben yumurta veriyorum.' At: 'Ben de sosyal medyada harika yorumları alıyorum.'"
    ]
    await ctx.send(random.choice(espiriler))

# ========================================
# BİLGİ KOMUTLARI
# ========================================

@bot.command()
async def skullanıcı(ctx, member: discord.Member = None):
    """Kullanıcı bilgilerini gösterir."""
    if member is None:
        member = ctx.author
    
    embed = discord.Embed(title=f"{member.display_name} Bilgileri", color=discord.Color.blue())
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="Kullanıcı Adı", value=member.name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Katılma", value=member.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
    embed.add_field(name="Oluşturma", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def ssunucu(ctx):
    """Sunucu bilgilerini gösterir."""
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Sunucu Bilgileri", color=discord.Color.blue())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Sahip", value=guild.owner.mention, inline=True)
    embed.add_field(name="Üye Sayısı", value=guild.member_count, inline=True)
    embed.add_field(name="Kanal Sayısı", value=len(guild.channels), inline=True)
    embed.add_field(name="Rol Sayısı", value=len(guild.roles), inline=True)
    embed.add_field(name="Oluşturulma", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def srol(ctx, rol: discord.Role):
    """Rol bilgilerini gösterir."""
    embed = discord.Embed(title=f"{rol.name} Rol Bilgileri", color=rol.color)
    embed.add_field(name="ID", value=rol.id, inline=True)
    embed.add_field(name="Renk", value=str(rol.color), inline=True)
    embed.add_field(name="Üye Sayısı", value=len(rol.members), inline=True)
    embed.add_field(name="Oluşturulma", value=rol.created_at.strftime("%d/%m/%Y"), inline=True)
    await ctx.send(embed=embed)

# ========================================
# KULLANIŞLI KOMUTLAR
# ========================================

@bot.command()
async def sping(ctx):
    """Botun gecikmesini gösterir."""
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def sanket(ctx, *, soru: str):
    """Basit anket oluşturur."""
    embed = discord.Embed(title="Anket", description=soru, color=discord.Color.blue())
    embed.set_footer(text=f"{ctx.author.display_name} tarafından başlatıldı.")
    mesaj = await ctx.send(embed=embed)
    await mesaj.add_reaction("✅")
    await mesaj.add_reaction("❌")

@bot.command()
async def shatırlat(ctx, sure: int, *, mesaj: str):
    """Belirtilen süre sonra hatırlatma yapar (saniye cinsinden)."""
    await ctx.send(f"{sure} saniye sonra hatırlatacağım: {mesaj}")
    await asyncio.sleep(sure)
    await ctx.send(f"{ctx.author.mention}, hatırlatma: {mesaj}")

@bot.command()
async def syardım(ctx):
    """Tüm komutları gösterir."""
    mesaj = "**Stat Bot Komutları (!s ile)**\n\n"
    mesaj += "**Eğlence:**\n"
    mesaj += "!szar - Zar atar\n"
    mesaj += "!syazitura - Yazı tura atar\n"
    mesaj += "!srastgele - Rastgele sayı üretir\n"
    mesaj += "!sespri - Espri yapar\n\n"
    mesaj += "**Bilgi:**\n"
    mesaj += "!skullanıcı - Kullanıcı bilgileri\n"
    mesaj += "!ssunucu - Sunucu bilgileri\n"
    mesaj += "!srol - Rol bilgileri\n\n"
    mesaj += "**Kullanışlı:**\n"
    mesaj += "!sping - Botun gecikmesi\n"
    mesaj += "!sanket - Anket oluşturur\n"
    mesaj += "!shatırlat <süre> <mesaj> - Hatırlatıcı\n\n"
    mesaj += "**Bot:**\n"
    mesaj += "!syardım - Bu mesajı gösterir"
    await ctx.send(mesaj)

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Token ayarlanmamış.")
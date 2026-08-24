import discord
from discord.ext import commands
import os
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
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========================================
# ROLLER VE SÜRELERİ
# ========================================

ROLLER = [
    {"id": 1541443222147178496, "sure": 25 * 60 * 60, "isim": "Margarita Negra 🖤"},
    {"id": 1541443492914528337, "sure": 15 * 60 * 60, "isim": "f l o r d e s a n g r e🩸"},
    {"id": 1541443535365083196, "sure": 8 * 60 * 60, "isim": "E l I n f i e r n o🕯️"},
    {"id": 1541443660980158514, "sure": 2 * 60 * 60, "isim": "S o l a d o 🌿"},
    {"id": 1541443983882981536, "sure": 45 * 60, "isim": "p a p a t y a 🌸"},
    {"id": 1541444135146364928, "sure": 15 * 60, "isim": "yol kenarı otu 🌾"}
]

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verilen_roller (
            user_id INTEGER,
            rol_id INTEGER,
            PRIMARY KEY (user_id, rol_id)
        )
    ''')
    conn.commit()
    conn.close()

veritabani_kur()

aktif_sesler = {}

# ========================================
# OLAYLAR
# ========================================

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/yardim"))
    print(f'✅ Stat Bot hazır: {bot.user}')
    print(f'🎯 {len(ROLLER)} adet rol takip ediliyor.')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Slash komut senkronizasyon hatası: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mesaj_sayilari (user_id, toplam_mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET toplam_mesaj = toplam_mesaj + 1", (message.author.id,))
    conn.commit()
    conn.close()
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
            await ses_ekle(member, fark)
    elif before.channel != after.channel:
        if member.id in aktif_sesler:
            giris = aktif_sesler.pop(member.id)
            fark = (now - giris).seconds
            await ses_ekle(member, fark)
        if after.channel is not None:
            aktif_sesler[member.id] = now

async def ses_ekle(member, eklenecek_saniye):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ses_sureleri (user_id, toplam_saniye) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET toplam_saniye = toplam_saniye + ?", (member.id, eklenecek_saniye, eklenecek_saniye))
    conn.commit()
    cursor.execute("SELECT toplam_saniye FROM ses_sureleri WHERE user_id = ?", (member.id,))
    toplam = cursor.fetchone()[0]
    conn.close()
    await rol_kontrol(member, toplam)

async def rol_kontrol(member, toplam_saniye):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for rol_verisi in ROLLER:
        rol_id = rol_verisi["id"]
        gereken_sure = rol_verisi["sure"]
        if toplam_saniye >= gereken_sure:
            cursor.execute("SELECT 1 FROM verilen_roller WHERE user_id = ? AND rol_id = ?", (member.id, rol_id))
            if not cursor.fetchone():
                rol = member.guild.get_role(rol_id)
                if rol:
                    try:
                        await member.add_roles(rol)
                        cursor.execute("INSERT INTO verilen_roller (user_id, rol_id) VALUES (?, ?)", (member.id, rol_id))
                        conn.commit()
                        print(f"✅ {member.name} kullanıcısına {rol.name} rolü verildi!")
                    except Exception as e:
                        print(f"❌ Rol verilemedi: {e}")
    conn.close()

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"❌ Hata: {str(error)[:100]}")

# ========================================
# SLASH KOMUTLAR ( / ile çalışır )
# ========================================

@bot.tree.command(name="profil", description="Kullanıcının profilini gösterir.")
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
    embed = discord.Embed(title=f"👤 {kisi.display_name} Profili", color=discord.Color.blue())
    if kisi.avatar:
        embed.set_thumbnail(url=kisi.avatar.url)
    embed.add_field(
        name="📊 İstatistikler",
        value=f"**Toplam Mesaj:** {toplam_mesaj}\n**Ses Süresi:** {saat} saat, {dakika} dakika, {saniye} saniye",
        inline=False
    )
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    kazanilanlar = []
    for rol_verisi in ROLLER:
        cursor.execute("SELECT 1 FROM verilen_roller WHERE user_id = ? AND rol_id = ?", (kisi.id, rol_verisi["id"]))
        if cursor.fetchone():
            kazanilanlar.append(f"✅ {rol_verisi['isim']}")
    conn.close()
    if kazanilanlar:
        embed.add_field(name="🎭 Kazanılan Roller", value="\n".join(kazanilanlar), inline=False)
    else:
        embed.add_field(name="🎭 Kazanılan Roller", value="Henüz hiçbir rol kazanılmamış.", inline=False)
    embed.add_field(
        name="📅 Hesap Bilgileri",
        value=f"**Katılma:** {kisi.joined_at.strftime('%d/%m/%Y %H:%M') if kisi.joined_at else 'Bilinmiyor'}\n**Oluşturma:** {kisi.created_at.strftime('%d/%m/%Y %H:%M')}",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="yardim", description="Tüm komutları ve rol sürelerini gösterir.")
async def yardim(interaction: discord.Interaction):
    mesaj = "**📋 Stat Bot Komutları (/ ile)**\n\n"
    mesaj += "`/profil @kisi` - Kullanıcı profilini gösterir\n"
    mesaj += "`/ping` - Botun gecikmesini gösterir\n"
    mesaj += "`/yardim` - Bu mesajı gösterir\n\n"
    mesaj += "**🎯 Otomatik Rol Sistemi:**\n"
    for rol in ROLLER:
        saat = rol["sure"] // 3600
        dakika = (rol["sure"] % 3600) // 60
        if saat > 0:
            sure_str = f"{saat} saat"
        else:
            sure_str = f"{dakika} dakika"
        mesaj += f"- `{rol['isim']}` → {sure_str} ses süresi\n"
    await interaction.response.send_message(mesaj)

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
import discord
from discord.ext import commands
import json
import os
import random
import requests
import asyncio
import praw
from redgifs.aio import API
from datetime import datetime, timedelta
import math

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        self.loop.create_task(boss_oto_belir())

bot = MyBot(command_prefix="!", intents=intents)

DATA_FILE = "karakterler.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

def get_or_create_user(user_id):
    data = load_data()
    if str(user_id) not in data:
        karakter = {
            "guc": 10,
            "para": 100,
            "seviye": 1,
            "xp": 0,
            "max_can": 150,
            "mevcut_can": 150,
            "zirh": 0,
            "envanter": [],
            "giyili": {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None}
        }
        data[str(user_id)] = karakter
        save_data(data)
        return karakter, True
    karakter = data[str(user_id)]
    # Eksik tüm alanları tamamla
    if "max_can" not in karakter:
        karakter["max_can"] = 150
    if "mevcut_can" not in karakter:
        karakter["mevcut_can"] = karakter.get("max_can", 150)
    if "zirh" not in karakter:
        karakter["zirh"] = 0
    if "envanter" not in karakter:
        karakter["envanter"] = []
    if "giyili" not in karakter:
        karakter["giyili"] = {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None}
    # Eski 'can' alanı varsa kaldır
    if "can" in karakter:
        del karakter["can"]
    save_data(data)
    return karakter, False

# Seviye için gereken XP hesaplama fonksiyonu
def gereken_xp(seviye):
    return 50 * seviye  # Daha hızlı seviye atlama

# Seviye atlama fonksiyonu
async def seviye_atlat(ctx, karakter, user_id):
    karakter["xp"] = 0
    karakter["seviye"] += 1
    karakter["para"] += 500
    karakter["guc"] += 5
    save_data({**load_data(), str(user_id): karakter})
    await ctx.send(
        f"🎊🎉 {ctx.author.mention} SEVİYE ATLADI! 🎉🎊\n"
        f"⭐️ Yeni seviye: {karakter['seviye']} ⭐️\n"
        f"💰 500 altın ve 💪 5 güç ödül kazandın!\n"
        f"🚀 Gücün ve şöhretin artıyor, arenada yeni bir efsane doğuyor! 🏆"
    )

@bot.event
async def on_ready():
    print(f"Bot {bot.user} olarak giriş yaptı!")

# Cooldown error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        kalan = int(error.retry_after)
        mesaj = f"⏳ Bu komutu tekrar kullanabilmek için {kalan} saniye beklemelisin! Lütfen spam yapma."
        await ctx.send(mesaj)
        return
    raise error

OZEL_ILK_ILtIFAT = (
    "💖 Dünyanın en güzel kızı, biricik sevgilim geldi! 💖\n"
    "Senin gibi bir sevgilim olduğu için çok şanslıyım!\n"
)
OZEL_ILtIFATLAR = [
    "🌹 Gözlerinle bile bu sunucuyu güzelleştiriyorsun, sevgilim!",
    "💌 Her mesajın kalbimi ısıtıyor!",
    "👑 Kraliçem, yine geldin ve her şey daha güzel oldu!",
    "✨ Senin enerjinle burası cennet gibi!",
    "😇 Varlığın bana huzur veriyor, iyi ki varsın!",
    "🌟 Herkes seni konuşuyor, efsane sevgilim burada!",
    "🦋 Bugün de harikasın, aşkım!",
    "🎀 Sunucunun en tatlısı, biricik sevgilim!",
    "💖 Seni çok seviyorum!"
]

# Karakter komutu görselliği
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def karakter(ctx, kullanici: discord.Member = None):
    with open("config.json", "r") as f:
        config = json.load(f)
        OZEL_KULLANICILAR = config.get("OZEL_KULLANICILAR", [])

    def toplam_can(karakter):
        items = load_items()
        can = karakter.get("max_can", 150)
        giyili = karakter.get("giyili", {})
        for slot, item_id in giyili.items():
            if item_id and item_id in items:
                can += items[item_id].get("can", 0)
        return can
    def toplam_zirh(karakter):
        items = load_items()
        zirh = 0
        giyili = karakter.get("giyili", {})
        for slot, item_id in giyili.items():
            if item_id and item_id in items:
                zirh += items[item_id].get("zirh", 0)
        return zirh
    def bar(val, maxv, icon):
        bar_len = 20
        oran = maxv and val / maxv or 0
        dolu = int(bar_len * oran)
        return f"{icon} {val}/{maxv}\n" + ("█" * dolu + "░" * (bar_len - dolu))

    if ctx.author.id in OZEL_KULLANICILAR:
        user_id = ctx.author.id
        data = load_data()
        if str(user_id) not in data:
            await ctx.send(OZEL_ILK_ILtIFAT)
        else:
            await ctx.send(random.choice(OZEL_ILtIFATLAR))
    if kullanici is None:
        user_id = ctx.author.id
        data = load_data()
        if str(user_id) not in data:
            karakter = {
                "guc": 10,
                "para": 100,
                "seviye": 1,
                "xp": 0,
                "train_sayisi": 0,
                "is_sayisi": 0
            }
            data[str(user_id)] = karakter
            save_data(data)
            await ctx.send(
                f"🎉 {ctx.author.mention} macerana başlamak için ilk karakterin oluşturuldu!\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💪 Güç: 10 | 💰 Para: 100 | 🧭 Seviye: 1 | ✨ XP: 0\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Artık !train, !is_ ve !savas komutlarını kullanabilirsin!"
            )
        else:
            karakter = data[str(user_id)]
            guc = karakter["guc"]
            para = karakter["para"]
            seviye = karakter.get("seviye", 1)
            xp = karakter.get("xp", 0)
            xp_gerekli = gereken_xp(seviye)
            train_sayisi = karakter.get("train_sayisi", 0)
            is_sayisi = karakter.get("is_sayisi", 0)
            can_toplam = toplam_can(karakter)
            can_mevcut = karakter.get("mevcut_can", can_toplam)
            zirh_toplam = toplam_zirh(karakter)
            zirh_mevcut = karakter.get("mevcut_zirh", zirh_toplam)
            canbar = bar(can_mevcut, can_toplam, "❤️ Can:")
            zirhbar = bar(zirh_mevcut, zirh_toplam, "🛡️ Zırh:")
            mesaj = (
                f"🧙‍♂️ **Karakter Bilgileri**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💪 Güç: {guc}\n"
                f"💰 Para: {para}\n"
                f"🧭 Seviye: {seviye}\n"
                f"✨ XP: {xp} / {xp_gerekli} ({int(xp/xp_gerekli*100) if xp_gerekli else 0}%)\n"
                f"🏋️‍♂️ Toplam Antrenman: {train_sayisi} | 💼 Toplam İş: {is_sayisi}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{canbar}\n{zirhbar}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ Statlarını güçlendirmek için marketten ekipman alabilir, !envanter ile eşyalarını görebilirsin."
            )
            await ctx.send(mesaj)
    else:
        user_id = kullanici.id
        data = load_data()
        if str(user_id) not in data:
            await ctx.send(f"❌ {kullanici.mention} henüz bir karaktere sahip değil!")
        else:
            karakter = data[str(user_id)]
            guc = karakter["guc"]
            para = karakter["para"]
            seviye = karakter.get("seviye", 1)
            xp = karakter.get("xp", 0)
            xp_gerekli = gereken_xp(seviye)
            train_sayisi = karakter.get("train_sayisi", 0)
            is_sayisi = karakter.get("is_sayisi", 0)
            can_toplam = toplam_can(karakter)
            can_mevcut = karakter.get("mevcut_can", can_toplam)
            zirh_toplam = toplam_zirh(karakter)
            zirh_mevcut = karakter.get("mevcut_zirh", zirh_toplam)
            canbar = bar(can_mevcut, can_toplam, "❤️ Can:")
            zirhbar = bar(zirh_mevcut, zirh_toplam, "🛡️ Zırh:")
            mesaj = (
                f"🔎 **{kullanici.display_name} Karakter Profili**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💪 Güç: {guc}\n"
                f"💰 Para: {para}\n"
                f"🧭 Seviye: {seviye}\n"
                f"✨ XP: {xp} / {xp_gerekli} ({int(xp/xp_gerekli*100) if xp_gerekli else 0}%)\n"
                f"🏋️‍♂️ Toplam Antrenman: {train_sayisi} | 💼 Toplam İş: {is_sayisi}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{canbar}\n{zirhbar}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ Statlarını güçlendirmek için marketten ekipman alabilir, !envanter ile eşyalarını görebilirsin."
            )
            await ctx.send(mesaj)

# train komutu görselliği
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def train(ctx):
    with open("config.json", "r") as f:
        config = json.load(f)
        OZEL_KULLANICILAR = config.get("OZEL_KULLANICILAR", [])

    if ctx.author.id in OZEL_KULLANICILAR:
        await ctx.send(random.choice(OZEL_ILtIFATLAR))
    user_id = ctx.author.id
    karakter, _ = get_or_create_user(user_id)
    if "train_sayisi" not in karakter:
        karakter["train_sayisi"] = 0
    karakter["train_sayisi"] += 1
    seviye = karakter.get("seviye", 1)
    train_sayisi = karakter["train_sayisi"]
    artıs = random.randint(1, 5) + (seviye // 2) + (train_sayisi // 10)
    xp_kazanc = max(3, int(seviye * 2))  # Seviye bazlı XP
    
    karakter["guc"] += artıs
    karakter["xp"] = karakter.get("xp", 0) + xp_kazanc
    
    # Seviye atlama kontrolü
    seviye_atlama_mesaj = ""
    while karakter['xp'] >= gereken_xp(karakter['seviye']):
        await seviye_atlat(ctx, karakter, user_id)
        seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"
    
    data = load_data()
    data[str(user_id)] = karakter
    save_data(data)
    mesaj = (
        f"🏋️‍♂️ **Antrenman Sonucu**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💪 Kazanılan Güç: +{artıs}\n"
        f"✨ Kazanılan XP: +{xp_kazanc}\n"
        f"🏋️‍♂️ Toplam Antrenman: {train_sayisi}\n"
        f"💪 Yeni Güç: {karakter['guc']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 Gücün artıyor, arenada daha iddialısın!{seviye_atlama_mesaj}"
    )
    await ctx.send(mesaj)

# is_ komutu görselliği
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def is_(ctx):
    with open("config.json", "r") as f:
        config = json.load(f)
        OZEL_KULLANICILAR = config.get("OZEL_KULLANICILAR", [])

    if ctx.author.id in OZEL_KULLANICILAR:
        await ctx.send(random.choice(OZEL_ILtIFATLAR))
    user_id = ctx.author.id
    karakter, _ = get_or_create_user(user_id)
    if "is_sayisi" not in karakter:
        karakter["is_sayisi"] = 0
    karakter["is_sayisi"] += 1
    seviye = karakter.get("seviye", 1)
    is_sayisi = karakter["is_sayisi"]
    sans = random.random()
    data = load_data()
    if sans < 0.05:
        miktar = random.randint(5000, 10000) + seviye * 100 + is_sayisi * 10
        xp_kazanc = max(10, int(seviye * 5))  # Büyük ödül için daha fazla XP
        
        karakter["para"] += miktar
        karakter["xp"] = karakter.get("xp", 0) + xp_kazanc
        
        # Seviye atlama kontrolü
        seviye_atlama_mesaj = ""
        while karakter['xp'] >= gereken_xp(karakter['seviye']):
            await seviye_atlat(ctx, karakter, user_id)
            seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"
        
        data[str(user_id)] = karakter
        save_data(data)
        mesaj = (
            f"💎 **BÜYÜK ÖDÜL!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Kazanılan Para: +{miktar}\n"
            f"✨ Kazanılan XP: +{xp_kazanc}\n"
            f"💼 Toplam İş: {is_sayisi}\n"
            f"💰 Yeni Bakiye: {karakter['para']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ Bugün çok şanslısın!{seviye_atlama_mesaj}"
        )
        await ctx.send(mesaj)
    else:
        miktar = random.randint(10, 50) + seviye * 5 + is_sayisi // 10 * 3
        xp_kazanc = max(2, int(seviye * 1))  # Normal iş için az XP
        
        karakter["para"] += miktar
        karakter["xp"] = karakter.get("xp", 0) + xp_kazanc
        
        # Seviye atlama kontrolü
        seviye_atlama_mesaj = ""
        while karakter['xp'] >= gereken_xp(karakter['seviye']):
            await seviye_atlat(ctx, karakter, user_id)
            seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"
        
        data[str(user_id)] = karakter
        save_data(data)
        mesaj = (
            f"💼 **İşten Kazanç**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Kazanılan Para: +{miktar}\n"
            f"✨ Kazanılan XP: +{xp_kazanc}\n"
            f"💼 Toplam İş: {is_sayisi}\n"
            f"💰 Yeni Bakiye: {karakter['para']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Çalışmak bereket getirir!{seviye_atlama_mesaj}"
        )
        await ctx.send(mesaj)

# Zorluklara göre ödül ve ceza tablosu
ODUL_CEZA_TABLOSU = {
    "kolay": {
        "odul": {"guc": (3, 7), "para": (50, 150), "xp": (5, 10)},
        "ceza": {"guc": (1, 3), "para": (10, 30), "xp": (1, 3)}
    },
    "normal": {
        "odul": {"guc": (8, 15), "para": (200, 400), "xp": (15, 25)},
        "ceza": {"guc": (4, 8), "para": (50, 120), "xp": (5, 10)}
    },
    "zor": {
        "odul": {"guc": (15, 30), "para": (400, 800), "xp": (25, 50)},
        "ceza": {"guc": (8, 18), "para": (100, 250), "xp": (10, 20)}
    }
}

# --- Stat ve Savaş Mekaniği ---
def zırh_azaltma_orani(zırh, seviye, max_reduction=0.8):
    X = 400 + 85 * seviye
    oran = zırh / (zırh + X) if zırh > 0 else 0
    return min(oran, max_reduction)

# Zırh azaltma formülünü güncelle
# Geliştirilmiş zırh hasar azaltma formülü
def hesapla_gercek_hasar(saldiri, zırh, min_hasar=1, max_reduction=0.8):
    if zırh <= 0:
        return saldiri
    
    # Daha etkili zırh formülü: zırh/(zırh+30) - daha hızlı azalma
    reduction = min(zırh / (zırh + 30), max_reduction)
    hasar = int(saldiri * (1 - reduction))
    return max(hasar, min_hasar)

def zırh_azalt(zırh, hasar, oran=0.3):
    return max(0, zırh - int(hasar * oran))

def stat_büyüme(karakter, seviye_artis=1):
    karakter['seviye'] += seviye_artis
    karakter['guc'] += 10 * seviye_artis
    karakter['can'] += 50 * seviye_artis
    karakter['zirh'] += 5 * seviye_artis
    return karakter

def dusman_statlari(oyuncu, zorluk):
    oranlar = {
        'kolay': 0.6,      # Daha kolay
        'normal': 1.0,     # Normal
        'zor': 1.4         # Zor ama imkansız değil
    }
    o = oranlar.get(zorluk, 1.0)
    
    # Seviye bazlı ek güçlendirme (azaltıldı)
    seviye_bonus = oyuncu['seviye'] * 1  # Her seviye +1 güç (eskiden +2)
    
    return {
        'seviye': oyuncu['seviye'],
        'guc': int((oyuncu['guc'] + seviye_bonus) * o),
        'can': int(oyuncu['can'] * o),
        'zirh': int(oyuncu['zirh'] * o)
    }

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def savas(ctx, zorluk: str = "normal"):
    user_id = ctx.author.id
    data = load_data()
    karakter, _ = get_or_create_user(user_id)
    seviye = karakter.get('seviye', 1)
    guc = karakter.get('guc', 10)
    base_max_can = karakter.get('max_can', 150)
    
    # Giyili ekipmanlardan toplam can ve zırh hesaplama
    items = load_items()
    giyili = karakter.get('giyili', {})
    toplam_zirh = 0
    ekipman_can = 0
    for slot, item_id in giyili.items():
        if item_id and item_id in items:
            toplam_zirh += items[item_id].get('zirh', 0)
            ekipman_can += items[item_id].get('can', 0)
    
    # Toplam maksimum can hesaplama
    toplam_max_can = base_max_can + ekipman_can
    
    # Mevcut can kontrolü
    mevcut_can = karakter.get('mevcut_can', toplam_max_can)
    if mevcut_can > toplam_max_can:
        mevcut_can = toplam_max_can
        karakter['mevcut_can'] = toplam_max_can
    
    # Mevcut zırh kontrolü
    mevcut_zirh = karakter.get('mevcut_zirh', toplam_zirh)
    if mevcut_zirh > toplam_zirh:
        mevcut_zirh = toplam_zirh
        karakter['mevcut_zirh'] = toplam_zirh
    
    if mevcut_can <= 0:
        await ctx.send("Canın sıfır! Savaşa giremezsin. Marketten iksir al veya bekle.")
        return
    
    # Zorluk kontrolü
    if zorluk == 'zor' and seviye < 3:
        await ctx.send("❌ Zor savaş için en az seviye 3 olman gerekiyor! Önce normal savaşlarla güçlen.")
        return
    
    oyuncu = {'seviye': seviye, 'guc': guc, 'can': mevcut_can, 'zirh': mevcut_zirh}
    dusman = dusman_statlari(oyuncu, zorluk)
    max_z = oyuncu['zirh']
    max_c_d = dusman['can']
    max_z_d = dusman['zirh']
    tur = 1
    def bar(val, maxv, icon):
        bar_len = 20
        oran = maxv and val / maxv or 0
        dolu = int(bar_len * oran)
        return f"{icon} {val}/{maxv}\n" + ("█" * dolu + "░" * (bar_len - dolu))
    oyuncu_canbar = bar(oyuncu['can'], toplam_max_can, "❤️ Can:")
    oyuncu_zirhbar = bar(oyuncu['zirh'], max_z, "🛡️ Zırh:")
    dusman_canbar = bar(dusman['can'], max_c_d, "❤️ Can:")
    dusman_zirhbar = bar(dusman['zirh'], max_z_d, "🛡️ Zırh:")
    msg = (
        f"⚔️ Savaş Başladı!\nSen: {oyuncu['can']}/{toplam_max_can} can, {oyuncu['zirh']} zırh\nDüşman: {dusman['can']} can, {dusman['zirh']} zırh\n"
        f"━━━━━━━━━━━\n"
        f"**Tur {tur}**\n"
        f"Sen: - 0 can\nDüşman: - 0 can\n"
        f"\nSen\n{oyuncu_canbar}\n{oyuncu_zirhbar}\n"
        f"Düşman\n{dusman_canbar}\n{dusman_zirhbar}\n"
    )
    mesaj = await ctx.send(msg)
    await asyncio.sleep(1.5)
    while oyuncu['can'] > 0 and dusman['can'] > 0:
        # Oyuncu saldırısı
        oyuncu_atak = int(oyuncu['guc'] * random.uniform(0.98, 1.02))
        dusman_hasar = hesapla_gercek_hasar(oyuncu_atak, dusman['zirh'])
        dusman['can'] -= dusman_hasar
        dusman['zirh'] = zırh_azalt(dusman['zirh'], dusman_hasar)
        oyuncu_canbar = bar(oyuncu['can'], toplam_max_can, "❤️ Can:")
        oyuncu_zirhbar = bar(oyuncu['zirh'], max_z, "🛡️ Zırh:")
        dusman_canbar = bar(dusman['can'], max_c_d, "❤️ Can:")
        dusman_zirhbar = bar(dusman['zirh'], max_z_d, "🛡️ Zırh:")
        log = (
            f"⚔️ Savaş Başladı!\nSen: {toplam_max_can} can, {max_z} zırh\nDüşman: {max_c_d} can, {max_z_d} zırh\n"
            f"━━━━━━━━━━━\n"
            f"**Tur {tur}**\n"
            f"Sen: - 0 can\n"
            f"Düşman: -{dusman_hasar} can (-{int(dusman_hasar*0.3)} zırh)\n"
            f"\nSen\n{oyuncu_canbar}\n{oyuncu_zirhbar}\n"
            f"Düşman\n{dusman_canbar}\n{dusman_zirhbar}\n"
        )
        if len(log) > 1900:
            log = log[-1900:]
        await mesaj.edit(content=log)
        await asyncio.sleep(1)
        if dusman['can'] <= 0:
            break
        # Düşman saldırısı
        dusman_atak = int(dusman['guc'] * random.uniform(0.98, 1.02))
        oyuncu_hasar = hesapla_gercek_hasar(dusman_atak, oyuncu['zirh'])
        oyuncu['can'] -= oyuncu_hasar
        oyuncu['zirh'] = zırh_azalt(oyuncu['zirh'], oyuncu_hasar)
        oyuncu_canbar = bar(oyuncu['can'], toplam_max_can, "❤️ Can:")
        oyuncu_zirhbar = bar(oyuncu['zirh'], max_z, "🛡️ Zırh:")
        dusman_canbar = bar(dusman['can'], max_c_d, "❤️ Can:")
        dusman_zirhbar = bar(dusman['zirh'], max_z_d, "🛡️ Zırh:")
        log = (
            f"⚔️ Savaş Başladı!\nSen: {toplam_max_can} can, {max_z} zırh\nDüşman: {max_c_d} can, {max_z_d} zırh\n"
            f"━━━━━━━━━━━\n"
            f"**Tur {tur}**\n"
            f"Sen: -{oyuncu_hasar} can (-{int(oyuncu_hasar*0.3)} zırh)\n"
            f"Düşman: - 0 can\n"
            f"\nSen\n{oyuncu_canbar}\n{oyuncu_zirhbar}\n"
            f"Düşman\n{dusman_canbar}\n{dusman_zirhbar}\n"
        )
        if len(log) > 1900:
            log = log[-1900:]
        await mesaj.edit(content=log)
        await asyncio.sleep(1)
        tur += 1
    # Savaş sonucu ve ödüller/ceza
    if oyuncu['can'] > 0:
        # Seviye ve güce göre oranlanmış ödüller
        seviye = karakter.get('seviye', 1)
        guc = karakter.get('guc', 10)
        
        if zorluk == 'kolay':
            guc_odul = max(1, int(seviye * 0.5))
            xp_odul = max(8, int(seviye * 5))
            para_odul = max(15, int(guc * 1.5))
        elif zorluk == 'normal':
            guc_odul = max(2, int(seviye * 1))
            xp_odul = max(15, int(seviye * 10))
            para_odul = max(25, int(guc * 3))
        else:  # zor
            guc_odul = max(3, int(seviye * 2))
            xp_odul = max(25, int(seviye * 15))
            para_odul = max(50, int(guc * 6))
        
        karakter['guc'] += guc_odul
        karakter['xp'] = karakter.get('xp', 0) + xp_odul
        karakter['para'] += para_odul
        
        # Seviye atlama kontrolü
        seviye_atlama_mesaj = ""
        while karakter['xp'] >= gereken_xp(karakter['seviye']):
            await seviye_atlat(ctx, karakter, user_id)
            seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"
        
        # Item düşme sistemi
        drop_item = get_drop_item(zorluk)
        drop_mesaj = ""
        if drop_item:
            item_kodu = None
            items = load_items()
            for kod, item in items.items():
                if item == drop_item:
                    item_kodu = kod
                    break
            
            if item_kodu:
                karakter.setdefault("envanter", []).append(item_kodu)
                drop_mesaj = f"\n🎁 **Item Düştü:** {drop_item['isim']} ({drop_item['nadirlik']})"
        
        sonuc = f"🏆 Zafer! +{guc_odul} güç, +{xp_odul} XP, +{para_odul} altın kazandın!{seviye_atlama_mesaj}{drop_mesaj}"
    else:
        # Seviye ve güce göre oranlanmış cezalar
        seviye = karakter.get('seviye', 1)
        guc = karakter.get('guc', 10)
        
        if zorluk == 'kolay':
            guc_ceza = 0
            para_ceza = max(5, int(guc * 0.5))
        elif zorluk == 'normal':
            guc_ceza = max(1, int(seviye * 0.3))
            para_ceza = max(10, int(guc * 1))
        else:  # zor
            guc_ceza = max(1, int(seviye * 0.5))
            para_ceza = max(20, int(guc * 2))
        
        karakter['guc'] = max(1, karakter['guc'] - guc_ceza)
        karakter['para'] = max(0, karakter['para'] - para_ceza)
        sonuc = f"💀 Kaybettin! -{guc_ceza} güç, -{para_ceza} altın."
    
    karakter['mevcut_can'] = max(0, oyuncu['can'])
    karakter['mevcut_zirh'] = max(0, oyuncu['zirh'])  # Savaş sonunda zırhı güncelle
    data[str(user_id)] = karakter
    save_data(data)
    # Sonucu ekle
    final_log = log + f"\n{sonuc}"
    if len(final_log) > 2000:
        final_log = final_log[-2000:]
    await mesaj.edit(content=final_log)

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def duello(ctx, rakip: discord.Member):
    user_id = ctx.author.id
    rakip_id = rakip.id
    if user_id == rakip_id:
        await ctx.send(f"❌ Kendi kendinle düello yapamazsın, {ctx.author.mention}!")
        return
    karakter1, _ = get_or_create_user(user_id)
    karakter2, _ = get_or_create_user(rakip_id)
    guc1 = karakter1["guc"]
    guc2 = karakter2["guc"]
    toplam_guc = guc1 + guc2
    if toplam_guc == 0:
        await ctx.send("Her iki karakterin de gücü yok! Düello yapılamaz.")
        return
    # Onay sistemi
    mesaj = await ctx.send(f"{rakip.mention}, {ctx.author.mention} sana düello teklif ediyor!\nKabul etmek için ✅, reddetmek için ❌ emojisine tıkla. (30 saniye içinde)")
    await mesaj.add_reaction("✅")
    await mesaj.add_reaction("❌")
    def check(reaction, user):
        return user.id == rakip_id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == mesaj.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except Exception:
        await ctx.send(f"⏰ {rakip.mention} zamanında yanıt vermedi, düello iptal edildi.")
        return
    if str(reaction.emoji) == "❌":
        await ctx.send(f"❌ {rakip.mention} düello teklifini reddetti.")
        return
    # Duello başlasın
    sans = random.random()
    # %1 mucizevi şans: güçsüz olan kazanır
    if guc1 < guc2 and sans < 0.01:
        kazanan, kaybeden = ctx.author, rakip
        kazanan_id, kaybeden_id = user_id, rakip_id
        mucize = True
    elif guc2 < guc1 and sans < 0.01:
        kazanan, kaybeden = rakip, ctx.author
        kazanan_id, kaybeden_id = rakip_id, user_id
        mucize = True
    else:
        oran1 = guc1 / toplam_guc
        if random.random() < oran1:
            kazanan, kaybeden = ctx.author, rakip
            kazanan_id, kaybeden_id = user_id, rakip_id
            mucize = False
        else:
            kazanan, kaybeden = rakip, ctx.author
            kazanan_id, kaybeden_id = rakip_id, user_id
            mucize = False
    para_miktari = random.randint(200, 500)
    kaybeden_para = karakter2["para"] if kazanan_id == user_id else karakter1["para"]
    gercek_kayip = min(para_miktari, kaybeden_para)
    data = load_data()
    data[str(kazanan_id)]["para"] += gercek_kayip
    data[str(kaybeden_id)]["para"] = max(0, data[str(kaybeden_id)]["para"] - gercek_kayip)
    save_data(data)
    if mucize:
        mesaj = (
            f"🌪️✨ MUCİZE! {kazanan.mention} neredeyse hiç şansı yokken, {kaybeden.mention}'a karşı inanılmaz bir zafer kazandı!\n"
            f"🦶 {kaybeden.mention}'ın ayağı taşa takıldı, fırsatı {kazanan.mention} değerlendirdi!\n"
            f"🏆 {kazanan.mention}: +{gercek_kayip} altın\n"
            f"💀 {kaybeden.mention}: -{gercek_kayip} altın"
        )
    else:
        mesajlar = [
            f"⚔️ {kazanan.mention} ile {kaybeden.mention} arasında destansı bir düello gerçekleşti! {kazanan.mention} galip geldi! 🏆\n"
            f"🏅 Zafer: +{gercek_kayip} altın\n"
            f"🥀 Kayıp: -{gercek_kayip} altın",
            f"🗡️ {kazanan.mention} rakibini zekasıyla alt etti! {kaybeden.mention} yere serildi!\n"
            f"�� Kazanan: +{gercek_kayip} altın\n"
            f"💸 Kaybeden: -{gercek_kayip} altın",
            f"🔥 {kazanan.mention} arenada fırtına gibi esti! {kaybeden.mention} ise şanssız bir gün geçirdi...\n"
            f"💪 Zafer: +{gercek_kayip} altın\n"
            f"😵 Kayıp: -{gercek_kayip} altın"
        ]
        mesaj = random.choice(mesajlar)
    await ctx.send(mesaj)

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def yardim(ctx):
    with open("config.json", "r") as f:
        config = json.load(f)
        ADMIN_IDS = config.get("ADMIN_IDS", [])

    yardim_mesaj = (
        """
✨ **Komutlar ve Açıklamaları** ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━

`!karakter [@kullanıcı]`  → Kendi karakterini veya etiketlediğin kullanıcının karakterini gösterir.
`!train`                   → Antrenman yaparak gücünü artırırsın.
`!is_`                     → Çalışarak altın kazanırsın. Nadiren büyük ödül bulabilirsin!
`!savas [zorluk]`          → Arenada savaşıp güç, para ve XP kazanabilir veya kaybedebilirsin. (Zorluk: kolay/normal/zor)
`!duello @kullanıcı`       → Etiketlediğin kullanıcıya karşı düello yaparsın. Kazanan güç ve para kazanır.

`!market`                  → Güç paketi, XP paketi, gif gibi klasik market ürünlerini listeler.
`!itemmarket`              → Sadece ekipmanları (silah, zırh, bot vb.) ve statlarını listeler.
`!satinal <kod>`           → Marketten veya itemmarketten ürün satın alırsın. (Her item bir kez alınabilir.)
`!envanter`                → Envanterini ve giyili ekipmanlarını, toplam güç/can ile birlikte gösterir.
`!giy <item_kodu>`         → Envanterindeki bir itemı giyer veya çıkarırsın. (Her slotta bir item giyilebilir.)

━━━━━━━━━━━━━━━━━━━━━━━━━━
**Market Sistemi:**
- `!market` → Güç paketi, XP paketi, gif gibi klasik ürünler.
- `!itemmarket` → Sadece ekipmanlar (silah, kask, göğüs, pantolon, bot) ve statları.
- Ekipman marketine geçmek için: `!itemmarket` yaz!
- Satın almak için: `!satinal <kod>`

━━━━━━━━━━━━━━━━━━━━━━━━━━
**Örnek Market Ekranı:**
```
🛒 Market:
`3` - Güç Paketi (300 altın): +10 güç kazandırır.
`5` - XP Paketi (200 altın): +30 XP kazandırır.
...
Ekipman marketi için: !itemmarket yaz!
```

**Örnek Ekipman Marketi Ekranı:**
```
🛡️ Ekipman Marketi:
`w2` - Demir Kılıç (nadir) [+120 güç, +30 can] - Fiyat: 90.000 altın
`g1` - Çelik Göğüslük (nadir) [+30 güç, +150 can] - Fiyat: 100.000 altın
...
Satın almak için: !satinal <item_kodu>
```

**Örnek Envanter Ekranı:**
```
Envanterin:
`w2` - Demir Kılıç (nadir) [+120 güç, +30 can]
`g1` - Çelik Göğüslük (nadir) [+30 güç, +150 can]

Giyili Ekipmanlar:
Silah: Demir Kılıç (+120 güç, +30 can)
Kask: Yok
Göğüs: Çelik Göğüslük (+30 güç, +150 can)
Pantolon: Yok
Bot: Yok

Toplam Güç: 160 | Toplam Can: 290
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Daha fazla güç ve prestij için marketleri takip et, savaşlara katıl, bossları alt et ve efsanevi itemları topla!
        """
    )
    if ctx.author.id in ADMIN_IDS:
        yardim_mesaj += (
            "\n**🔒 Admin Komutları:**\n"
            "`!duyuru <mesaj>` - Genel duyuru atar (mesajınız görünmez).\n"
            "`!duyuru_sil <mesaj_id>` - Belirtilen duyuru mesajını siler.\n"
            "`!bossbelir` - Sunucuda bossu manuel olarak ortaya çıkarır.\n"
            "`!temizle <miktar>` - DM'de sana gönderilmiş mesajları siler.\n"
        )
    # Mesajı 2000 karakterlik parçalara böl ve sırayla gönder
    for parca in [yardim_mesaj[i:i+2000] for i in range(0, len(yardim_mesaj), 2000)]:
        await ctx.send(parca)

# Market ürünleri
MARKET = {
    "1": {
        "isim": "Sürpriz Görsel Paketi",
        "aciklama": "Rastgele bir özel görsel gönderir.",
        "fiyat": 500,
        "tip": "gif"
    },
    "2": {
        "isim": "Mega Sürpriz Paketi",
        "aciklama": "Çok havalı ve nadir bir görsel gönderir.",
        "fiyat": 1500,
        "tip": "mega_gif"
    },
    "3": {
        "isim": "Güç Paketi",
        "aciklama": "+10 güç kazandırır.",
        "fiyat": 300,
        "tip": "guc"
    },
    "4": {
        "isim": "Güç Yenileme Paketi",
        "aciklama": "+20 güç kazandırır.",
        "fiyat": 800,
        "tip": "guc_yenile"
    },
    "5": {
        "isim": "XP Paketi",
        "aciklama": "+30 XP kazandırır.",
        "fiyat": 200,
        "tip": "xp"
    },
    "10": {
        "isim": "Zırh Yenileme Kiti",
        "aciklama": "Mevcut zırhını tamamen onarır (full yapar).",
        "fiyat": 200,
        "tip": "zirh_onar"
    },
    "11": {
        "isim": "İyileşme İksiri",
        "aciklama": "Mevcut canını tamamen doldurur (full yapar).",
        "fiyat": 200,
        "tip": "can_onar"
    }
}

NORMAL_GIF_TERIMLERI = [
    "anime", "anime reaction", "anime party"
]
MEGA_GIF_TERIMLERI = [
    "anime dance", "anime reaction", "anime party", "anime cool", "anime epic", "anime fire", "anime sparkle", "anime sexy", "anime sexy boy"
]

# Boss sistemi için global değişkenler
BOSS_AKTIF = False
BOSS_KAZANAN_ID = None
BOSS_MESAJ_ID = None
BOSS_KANAL_ID = None
BOSS_NICK = None
BOSS_CAN = None
BOSS_MAX_CAN = None
BOSS_SON_VURAN = None
BOSS_VURUS_GECMISI = []
# BOSS_NSFWMARKET_USERS artık configte tutulacak

BOSS_ISIMLERI = [
    "Ejderha Lordu", "Kara Şövalye", "Gölge Canavarı", "Ateş Elementali", "Buz Devri", "Kaos Ruhu"
]

async def boss_olustur(kanal):
    global BOSS_AKTIF, BOSS_KAZANAN_ID, BOSS_MESAJ_ID, BOSS_KANAL_ID, BOSS_NICK, BOSS_CAN, BOSS_MAX_CAN, BOSS_SON_VURAN, BOSS_VURUS_GECMISI
    if BOSS_AKTIF:
        return
    BOSS_AKTIF = True
    BOSS_KAZANAN_ID = None
    BOSS_NICK = random.choice(BOSS_ISIMLERI)
    BOSS_MAX_CAN = random.randint(1200, 2000)
    BOSS_CAN = BOSS_MAX_CAN
    BOSS_SON_VURAN = None
    BOSS_VURUS_GECMISI = []
    mesaj = await kanal.send(f"⚡️ **BOSS ORTAYA ÇIKTI!** ⚡️\nBoss: **{BOSS_NICK}**\nCan: {BOSS_CAN}\n!bossvurus komutuyla saldırabilirsin!")
    BOSS_MESAJ_ID = mesaj.id
    BOSS_KANAL_ID = kanal.id

async def boss_oto_belir():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(random.randint(3600, 7200))  # 1-2 saatte bir
        kanal = random.choice([c for g in bot.guilds for c in g.text_channels if c.permissions_for(g.me).send_messages])
        await boss_olustur(kanal)

@bot.command()
async def bossbelir(ctx):
    with open("config.json", "r") as f:
        config = json.load(f)
        ADMIN_IDS = config.get("ADMIN_IDS", [])

    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("Bu komutu sadece adminler kullanabilir.")
        return
    await boss_olustur(ctx.channel)

# bosskes komutunu kaldırıyorum

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def bossvurus(ctx):
    global BOSS_AKTIF, BOSS_CAN, BOSS_MAX_CAN, BOSS_SON_VURAN, BOSS_VURUS_GECMISI, BOSS_KAZANAN_ID
    if not BOSS_AKTIF or BOSS_CAN is None:
        await ctx.send("❌ Şu anda aktif bir boss yok! Yeni bir boss için admini bekle! 🕰️")
        return
    user_id = ctx.author.id
    karakter, _ = get_or_create_user(user_id)
    guc = karakter.get("guc", 10)
    vurus = random.randint(int(guc*0.7), int(guc*1.3))
    BOSS_CAN = max(0, BOSS_CAN - vurus)
    BOSS_SON_VURAN = ctx.author
    BOSS_VURUS_GECMISI.append({"user_id": user_id, "ad": ctx.author.display_name, "vurus": vurus})
    if BOSS_CAN == 0:
        BOSS_AKTIF = False
        BOSS_KAZANAN_ID = user_id
        gif_url = await redgifs_nsfw_gif()
        try:
            mesaj = await ctx.author.send(f"🏆 **TEBRİKLER!** 🏆\n\n{ctx.author.mention} **{BOSS_NICK}** bossuna son vuruşu yaptı ve zafer senin oldu!\n\n🔞 Boss ödülün: {gif_url if gif_url else 'Uygun NSFW gif bulunamadı.'}")
            log_dm_message(ctx.author.id, mesaj.id)
            await ctx.send(f"🎉 **{ctx.author.display_name}**, {BOSS_NICK} bossunu **efsane bir son vuruşla** alt etti!\n\n🏅 **Zafer Senin!**\n🎁 Ödülünü DM'den aldın!")
        except Exception:
            await ctx.send(f"{ctx.author.mention} DM'ni açmalısın, ödül gönderilemedi!")
        config = load_config()
        users = set(config.get("BOSS_NSFWMARKET_USERS", []))
        users.add(user_id)
        config["BOSS_NSFWMARKET_USERS"] = list(users)
        save_config(config)
    else:
        can_bar = "█" * int(BOSS_CAN / BOSS_MAX_CAN * 20)
        can_bar += "░" * (20 - len(can_bar))
        await ctx.send(
            f"⚔️ **{ctx.author.display_name} boss'a saldırdı!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💥 Vuruş Gücü: **{vurus}**\n"
            f"🩸 Boss'un Kalan Canı: **{BOSS_CAN}/{BOSS_MAX_CAN}**\n"
            f"{can_bar}"
        )

@bot.command()
async def bossdurum(ctx):
    global BOSS_AKTIF, BOSS_CAN, BOSS_MAX_CAN, BOSS_SON_VURAN, BOSS_NICK, BOSS_VURUS_GECMISI
    if not BOSS_AKTIF or BOSS_CAN is None:
        await ctx.send("❌ Şu anda aktif bir boss yok!")
        return
    son_vuran = BOSS_SON_VURAN.display_name if BOSS_SON_VURAN else "Yok"
    can_bar = "█" * int(BOSS_CAN / BOSS_MAX_CAN * 20)
    can_bar += "░" * (20 - len(can_bar))
    vuruslar = "\n".join([
        f"{i+1}. {v['ad']} - 💥 {v['vurus']}" for i, v in enumerate(BOSS_VURUS_GECMISI[-5:])
    ])
    await ctx.send(
        f"👹 **Boss Bilgisi**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧟‍♂️ Boss: **{BOSS_NICK}**\n"
        f"🩸 Can: **{BOSS_CAN}/{BOSS_MAX_CAN}**\n"
        f"{can_bar}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔪 Son Vuran: **{son_vuran}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗡️ **Son 5 Saldırı:**\n{vuruslar if vuruslar else 'Henüz saldırı yok!'}"
    )

def get_market_for_user(user_id):
    market = dict(MARKET)
    with open("config.json", "r") as f:
        config = json.load(f)
        OZEL_KULLANICILAR = config.get("OZEL_KULLANICILAR", [])
        boss_users = set(config.get("BOSS_NSFWMARKET_USERS", []))

    if user_id in OZEL_KULLANICILAR:
        market["6"] = {
            "isim": "Mini Aşk Paketi",
            "aciklama": "İçinde aşk dolu mini paket",
            "fiyat": 100,
            "tip": "ask_kisa"
        }
        market["7"] = {
            "isim": "Mega Aşk Paketi",
            "aciklama": "İçinde aşk dolu mega paket",
            "fiyat": 300,
            "tip": "ask_uzun"
        }
        market["8"] = {
            "isim": "Benimle Evlenir Misin?",
            "aciklama": "",
            "fiyat": 1000,
            "tip": "evlenme_teklifi"
        }
    if user_id in boss_users:
        market["99"] = {
            "isim": "Boss Ödülü",
            "aciklama": "Sadece bossu kesenlere özel!!",
            "fiyat": 1,
            "tip": "nsfw_boss"
        }
    return market

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def market(ctx):
    msg = "**🛒 Market:**\n"
    for kod, urun in MARKET.items():
        msg += f"`{kod}` - {urun['isim']} ({urun['fiyat']} altın): {urun['aciklama']}\n"
    msg += ("\nEkipman marketi için: `!itemmarket` yaz!\n"
            "Bir şey almak için: `!satinal <ürün_kodu> <adet>`\n"
                "(Gifler hariç diğer ürünlerde birden fazla alabilirsin. Giflerde adet her zaman 1'dir.)")
    await ctx.send(msg)

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def itemmarket(ctx):
    items = load_items()
    market_items = [ (k, v) for k, v in items.items() if "fiyat" in v ]
    msg = "**🛡️ Ekipman Marketi:**\n"
    for kod, it in market_items:
        msg += f"`{kod}` - {it['isim']} ({it['nadirlik']}) [+{it['guc']} güç, +{it['can']} can] - Fiyat: {it['fiyat']} altın\n"
    msg += "\nSatın almak için: !satinal <item_kodu>"
    await ctx.send(msg)


    

# ITEM SİSTEMİ: itemler.json'dan itemları yükle
ITEMS_FILE = "itemler.json"

def load_items():
    if not os.path.exists(ITEMS_FILE):
        return {}
    with open(ITEMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Karakter veri yapısında envanter ve giyili alanları örnek:
# {
#     "guc": 10,
#     "para": 100,
#     "seviye": 1,
#     "xp": 0,
#     "envanter": ["w1", "a1"],
#     "giyili": {
#         "silah": null,
#         "kask": null,
#         "gogus": null,
#         "pantolon": null,
#         "bot": null
#     }
# }

# Config dosyasından TOKEN ve API anahtarlarını oku
with open("config.json", "r") as f:
    config = json.load(f)
    TOKEN = config["TOKEN"]
    GIPHY_API_KEY = config.get("GIPHY_API_KEY", "")
    TENOR_API_KEY = config.get("TENOR_API_KEY", "")
    ADMIN_IDS = config.get("ADMIN_IDS", [])
    OZEL_KULLANICILAR = config.get("OZEL_KULLANICILAR", [])
    KAWAII_TOKEN = config.get("KAWAII_TOKEN", "anonymous")

import requests

def tenor_gif_cek(query, contentfilter="high"):
    api_key = TENOR_API_KEY
    url = f"https://tenor.googleapis.com/v2/search?q={query}&key={api_key}&limit=25&contentfilter={contentfilter}"
    r = requests.get(url)
    data = r.json()
    if data.get("results"):
        return random.choice([item["media_formats"]["gif"]["url"] for item in data["results"]])
    else:
        return None

def kawaii_sfw_gif():
    # Sadece testte çalışan SFW endpointler
    endpoints = [
        "hug", "kiss", "pat", "slap", "cuddle", "poke", "dance", "laugh", "wave", "wink", "nom", "punch", "shoot", "stare", "bite", "confused", "lick", "love", "pout", "run", "scared", "smile"
    ]
    random.shuffle(endpoints)
    for ep in endpoints:
        url = f"https://kawaii.red/api/gif/{ep}?token={KAWAII_TOKEN}"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            if data.get("response") and "error" not in data:
                return data.get("response")
    return None

async def redgifs_nsfw_gif():
    api = API()
    await api.login()
    tags = ["hentai", "anime", "cartoon", "animated", "ecchi", "japan", "manga"]
    for tag in tags:
        result = await api.search(tag, count=30)
        if result and result.gifs:
            gif = random.choice(result.gifs)
            return gif.urls.sd or gif.urls.hd or gif.web_url
    return None

def log_dm_message(user_id, message_id):
    log_file = "dm_log.json"
    try:
        with open(log_file, "r") as f:
            log = json.load(f)
    except FileNotFoundError:
        log = []
    log.append({
        "user_id": user_id,
        "message_id": message_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    with open(log_file, "w") as f:
        json.dump(log, f, indent=4)

# --- DUYURU SİSTEMİ ---
@bot.command()
async def duyuru(ctx, *, mesaj: str):
    """Genel duyuru atar (sadece adminler)"""
    with open("config.json", "r") as f:
        config = json.load(f)
        ADMIN_IDS = config.get("ADMIN_IDS", [])

    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Bu komutu sadece adminler kullanabilir!")
        return
    
    # Duyuru mesajını oluştur
    embed = discord.Embed(
        title="📢 **GENEL DUYURU** 📢",
        description=mesaj,
        color=0xFF6B6B,
        timestamp=datetime.utcnow() + timedelta(hours=3)  # Türkiye saati (UTC+3)
    )
    embed.set_footer(text=f"Duyuru: {ctx.author.display_name}")
    
    # Duyuruyu gönder
    await ctx.send(embed=embed)
    
    # Komut mesajını sil (duyuru gizli kalır)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def duyuru_sil(ctx, mesaj_id: int):
    """Belirtilen ID'deki duyuru mesajını siler (sadece adminler)"""
    with open("config.json", "r") as f:
        config = json.load(f)
        ADMIN_IDS = config.get("ADMIN_IDS", [])

    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Bu komutu sadece adminler kullanabilir!")
        return
    
    try:
        # Mesajı bul ve sil
        mesaj = await ctx.channel.fetch_message(mesaj_id)
        await mesaj.delete()
        await ctx.send("✅ Duyuru başarıyla silindi!", delete_after=3)
    except discord.NotFound:
        await ctx.send("❌ Belirtilen mesaj bulunamadı!", delete_after=3)
    except discord.Forbidden:
        await ctx.send("❌ Bu mesajı silme yetkim yok!", delete_after=3)
    except Exception as e:
        await ctx.send(f"❌ Hata oluştu: {str(e)}", delete_after=3)

@bot.command()
async def temizle(ctx, miktar: int = 1):
    # Sadece sunucuda çalışsın
    if ctx.guild is None:
        await ctx.send("Bu komut sadece sunucuda çalışır.")
        return
    deleted = 0
    async for msg in ctx.channel.history(limit=miktar+1):
        try:
            await msg.delete()
            deleted += 1
        except Exception:
            pass
    bilgi = await ctx.send(f"{deleted} mesaj silindi.")
    await bilgi.delete(delay=3)

@bot.command(name="dmsil")
async def dmsil(ctx, miktar: int = 1):
    if ctx.guild is not None:
        await ctx.send("Bu komut sadece DM'de çalışır.")
        return

    deleted = 0
    silinen_ids = []
    bot_msgs = []
    async for msg in ctx.channel.history(limit=1000):
        if msg.author == ctx.me:
            bot_msgs.append(msg)
    for msg in bot_msgs[:miktar]:
        try:
            await msg.delete()
            silinen_ids.append(msg.id)
            deleted += 1
        except Exception:
            pass
    bilgi = await ctx.send(f"{deleted} mesaj silindi.")
    await bilgi.delete(delay=3)

    try:
        with open("dm_log.json", "r") as f:
            log = json.load(f)
    except FileNotFoundError:
        log = []
    log = [entry for entry in log if entry["message_id"] not in silinen_ids]
    with open("dm_log.json", "w") as f:
        json.dump(log, f, indent=4)

# --- ENVANTER & ITEM SİSTEMİ ---

def karakter_toplam_stat(karakter, items):
    guc = karakter.get("guc", 10)
    can = karakter.get("max_can", 150)
    giyili = karakter.get("giyili", {})
    for slot, item_id in giyili.items():
        if item_id and item_id in items:
            guc += items[item_id].get("guc", 0)
            can += items[item_id].get("can", 0)
    return guc, can

@bot.command()
async def envanter(ctx):
    user_id = str(ctx.author.id)
    data = load_data()
    items = load_items()
    if user_id not in data:
        await ctx.send("Önce bir karakter oluşturmalısın! (!karakter)")
        return
    karakter = data[user_id]
    envanter = karakter.get("envanter", [])
    giyili = karakter.get("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})
    # Zırh hesaplama
    def max_zirh():
        items = load_items()
        zirh = 0
        for slot, item_id in giyili.items():
            if item_id and item_id in items:
                zirh += items[item_id].get("zirh", 0)
        return zirh
    max_z = max_zirh()
    mevcut_z = karakter.get("mevcut_zirh", max_z)
    if mevcut_z > max_z:
        mevcut_z = max_z
        karakter["mevcut_zirh"] = max_z
        save_data(data)
    bar_len = 20
    oran = max_z and mevcut_z / max_z or 0
    dolu = int(bar_len * oran)
    zirh_bar = "🛡️ Zırh: " + str(mevcut_z) + "/" + str(max_z) + "\n" + ("█" * dolu + "░" * (bar_len - dolu))
    # Giyili itemlar
    giyili_text = ""
    giyili_ids = set([item_id for item_id in giyili.values() if item_id])
    for slot in ["silah", "kask", "gogus", "pantolon", "bot"]:
        item_id = giyili.get(slot)
        if item_id and item_id in items:
            it = items[item_id]
            giyili_text += f"**{slot.capitalize()}**: {it['isim']} [`{item_id}`] (+{it.get('guc',0)} güç, +{it.get('can',0)} can, +{it.get('zirh',0)} zırh)\n"
        else:
            giyili_text += f"**{slot.capitalize()}**: Yok\n"
    # Envanterdeki itemlar (giyili olanlar hariç)
    inv_text = ""
    for item_id in envanter:
        if item_id in items and item_id not in giyili_ids:
            it = items[item_id]
            inv_text += f"`{item_id}` - {it['isim']} ({it['nadirlik']}) [+{it.get('guc',0)} güç, +{it.get('can',0)} can, +{it.get('zirh',0)} zırh]\n"
    await ctx.send(
        f"**Envanterin:**\n{inv_text if inv_text else 'Hiç item yok.'}\n"
        f"**Giyili Ekipmanlar:**\n{giyili_text}"
        f"\n{zirh_bar}"
    )

@bot.command()
async def giy(ctx, item_kodu: str):
    user_id = str(ctx.author.id)
    data = load_data()
    items = load_items()
    if user_id not in data:
        await ctx.send("Önce bir karakter oluşturmalısın! (!karakter)")
        return
    karakter = data[user_id]
    envanter = karakter.get("envanter", [])
    giyili = karakter.get("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})
    if item_kodu not in envanter and item_kodu not in items:
        await ctx.send("Bu item envanterinde yok!")
        return
    if item_kodu not in items:
        await ctx.send("Geçersiz item kodu!")
        return
    item = items[item_kodu]
    slot = None
    if item["tip"] == "silah":
        slot = "silah"
    elif item["tip"] == "kask":
        slot = "kask"
    elif item["tip"] == "gogus":
        slot = "gogus"
    elif item["tip"] == "pantolon":
        slot = "pantolon"
    elif item["tip"] == "bot":
        slot = "bot"
    else:
        await ctx.send("Bu item giyilemez!")
        return
    # Eğer zaten giyiliyse çıkar (envantere geri ekle)
    if giyili.get(slot) == item_kodu:
        giyili[slot] = None
        if item_kodu not in karakter.setdefault("envanter", []):
            karakter["envanter"].append(item_kodu)
        await ctx.send(f"{item['isim']} çıkartıldı ve envanterine geri döndü.")
    else:
        # Eğer o slota başka bir item giyiliyse onu envantere geri ekle
        eski = giyili.get(slot)
        if eski and eski not in karakter.setdefault("envanter", []):
            karakter["envanter"].append(eski)
        giyili[slot] = item_kodu
        if item_kodu in karakter["envanter"]:
            karakter["envanter"].remove(item_kodu)
        await ctx.send(f"{item['isim']} giyildi.")
    karakter["giyili"] = giyili
    data[user_id] = karakter
    save_data(data)


@bot.command()
async def satinal(ctx, item_kodu: str):
    user_id = str(ctx.author.id)
    data = load_data()
    items = load_items()
    if user_id not in data:
        await ctx.send("Önce bir karakter oluşturmalısın! (!karakter)")
        return
    karakter = data[user_id]
    if item_kodu in MARKET:
        urun = MARKET[item_kodu]
        if karakter["para"] < urun["fiyat"]:
            await ctx.send(f"Yeterli paran yok! ({urun['fiyat']} altın gerekiyor)")
            return
        karakter["para"] -= urun["fiyat"]
        if urun["tip"] == "zirh_onar":
            giyili = karakter.get("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})
            max_z = 0
            for slot, item_id in giyili.items():
                if item_id and item_id in items:
                    max_z += items[item_id].get("zirh", 0)
            karakter["mevcut_zirh"] = max_z
            data[user_id] = karakter
            save_data(data)
            await ctx.send(f"🛡️ Zırhın tamamen onarıldı! ({max_z} zırh)")
            return
        if urun["tip"] == "can_onar":
            giyili = karakter.get("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})
            max_c = karakter.get("max_can", 150)
            for slot, item_id in giyili.items():
                if item_id and item_id in items:
                    max_c += items[item_id].get("can", 0)
            karakter["mevcut_can"] = max_c
            data[user_id] = karakter
            save_data(data)
            await ctx.send(f"❤️ Canın tamamen iyileşti! ({max_c} can)")
            return
        if urun["tip"] == "gif":
            gif_url = kawaii_sfw_gif()
            if gif_url:
                await ctx.send(f"{ctx.author.mention} işte ödülün! {gif_url}")
            else:
                await ctx.send("Uygun gif bulunamadı.")
            data[user_id] = karakter
            save_data(data)
            return
        if urun["tip"] == "mega_gif":
            gif_url = kawaii_sfw_gif()
            if gif_url:
                await ctx.send(f"{ctx.author.mention} MEGA ödülün! {gif_url}")
            else:
                await ctx.send("Uygun mega gif bulunamadı.")
            data[user_id] = karakter
            save_data(data)
            return
        # Diğer eski market ürünleri
        await ctx.send(f"{urun['isim']} başarıyla satın alındı!")
        data[user_id] = karakter
        save_data(data)
        return
    if item_kodu not in items:
        await ctx.send("Geçersiz item kodu!")
        return
    item = items[item_kodu]
    if "fiyat" not in item:
        await ctx.send("Bu item markette satılmıyor!")
        return
    if item_kodu in karakter.get("envanter", []):
        await ctx.send("Bu item zaten envanterinde!")
        return
    if karakter["para"] < item["fiyat"]:
        await ctx.send(f"Yeterli paran yok! ({item['fiyat']} altın gerekiyor)")
        return
    karakter["para"] -= item["fiyat"]
    karakter.setdefault("envanter", []).append(item_kodu)
    data[user_id] = karakter
    save_data(data)
    await ctx.send(f"{item['isim']} başarıyla satın alındı ve envanterine eklendi!")

# --- Savaşlardan item düşme ve otomatik satış sistemi ---

def get_drop_item(zorluk):
    items = load_items()
    # Drop havuzunu ayır
    drop_items = [v for k, v in items.items() if k.startswith('dw') or k.startswith('dn') or k.startswith('de')]
    # Zorluk ve nadirliğe göre şanslar
    if zorluk == 'kolay':
        chances = [
            ('yaygın', 0.10),
            ('nadir', 0.02),
            ('efsanevi', 0.002)
        ]
    elif zorluk == 'normal':
        chances = [
            ('yaygın', 0.15),
            ('nadir', 0.05),
            ('efsanevi', 0.005)
        ]
    else:  # zor
        chances = [
            ('yaygın', 0.20),
            ('nadir', 0.10),
            ('efsanevi', 0.02)
        ]
    # Zor savaşta marketteki mitik/antik itemlar da çok düşük şansla düşebilir
    mitik_items = [v for k, v in items.items() if v.get('nadirlik') == 'mitik' and 'fiyat' in v]
    antik_items = [v for k, v in items.items() if v.get('nadirlik') == 'antik' and 'fiyat' in v]
    if zorluk == 'zor':
        chances += [
            ('mitik', 0.002),
            ('antik', 0.0005)
        ]
    # Şans tablosuna göre item seç
    roll = random.random()
    acc = 0
    for nadirlik, oran in chances:
        acc += oran
        if roll < acc:
            if nadirlik in ['yaygın', 'nadir', 'efsanevi']:
                pool = [i for i in drop_items if i['nadirlik'] == nadirlik]
            elif nadirlik == 'mitik':
                pool = mitik_items
            elif nadirlik == 'antik':
                pool = antik_items
            else:
                pool = []
            if pool:
                return random.choice(pool)
            break
    return None

def get_item_sell_price(item):
    # Drop itemlar için nadirliğe göre düşük fiyat
    base = {'yaygın': 2000, 'nadir': 8000, 'efsanevi': 30000, 'mitik': 100000, 'antik': 250000}
    return base.get(item.get('nadirlik'), 1000)

bot.run(TOKEN)
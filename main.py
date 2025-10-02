# -*- coding: utf-8 -*-
import os
import json
import math
import random
import asyncio
import requests
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands

# ---------- Intents ----------
intents = discord.Intents.default()
intents.message_content = True

# ---------- Dosya Adları ----------
DATA_FILE = "karakterler.json"
ITEMS_FILE = "itemler.json"
CONFIG_FILE = "config.json"
DM_LOG_FILE = "dm_log.json"

# ---------- Yardımcılar ----------
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    return load_json(DATA_FILE, {})

def save_data(data):
    save_json(DATA_FILE, data)

def load_items():
    return load_json(ITEMS_FILE, {})

def load_config():
    return load_json(CONFIG_FILE, {})

def save_config(cfg):
    save_json(CONFIG_FILE, cfg)

def chunk_text(s: str, limit: int = 2000):
    return [s[i:i+limit] for i in range(0, len(s), limit)]

async def safe_send(ctx: commands.Context, content=None, **kwargs):
    """
    Hybrid komutlarda ilk yanıtı güvenli yollamak için yardımcı.
    Slash çağrısında ilk mesaj interaction üzerinden gider,
    prefix çağrısında normal reply/send çalışır.
    """
    inter = getattr(ctx, "interaction", None)
    if inter and not inter.response.is_done():
        await inter.response.send_message(content, **kwargs)
    else:
        # ctx.reply varsa onu kullan, yoksa send
        if hasattr(ctx, "reply"):
            await ctx.reply(content, **kwargs)
        else:
            await ctx.send(content, **kwargs)

# ---------- Başlangıç Statları ve Kullanıcı ----------
def get_or_create_user(user_id: int):
    data = load_data()
    key = str(user_id)
    if key not in data:
        karakter = {
            "guc": 10,
            "para": 100,
            "seviye": 1,
            "xp": 0,
            "max_can": 150,
            "mevcut_can": 150,
            "zirh": 0,
            "mevcut_zirh": 0,
            "envanter": [],
            "giyili": {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None},
            "train_sayisi": 0,
            "is_sayisi": 0
        }
        data[key] = karakter
        save_data(data)
        return karakter, True
    # Eksik alanları tamamla (geriye uyum)
    karakter = data[key]
    karakter.setdefault("max_can", 150)
    karakter.setdefault("mevcut_can", karakter["max_can"])
    karakter.setdefault("zirh", 0)
    karakter.setdefault("mevcut_zirh", 0)
    karakter.setdefault("envanter", [])
    karakter.setdefault("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})
    karakter.setdefault("train_sayisi", 0)
    karakter.setdefault("is_sayisi", 0)
    # eski 'can' alanı varsa kaldır
    if "can" in karakter:
        karakter.pop("can", None)
    save_data({**load_data(), key: karakter})
    return karakter, False

def gereken_xp(seviye: int) -> int:
    return 50 * seviye

async def seviye_atlat(ctx: commands.Context, karakter: dict, user_id: int):
    karakter["xp"] = 0
    karakter["seviye"] += 1
    karakter["para"] += 500
    karakter["guc"] += 5
    save_data({**load_data(), str(user_id): karakter})
    await safe_send(ctx,
        f"🎊🎉 {ctx.author.mention} **SEVİYE ATLADI!** 🎉🎊\n"
        f"⭐️ Yeni seviye: {karakter['seviye']} ⭐️\n"
        f"💰 500 altın ve 💪 5 güç kazandın!\n"
        f"🏆 Yolun efsaneye gidiyor!"
    )

# ---------- Zırh & Hasar ----------
def hesapla_gercek_hasar(saldiri: int, zirh: int, min_hasar: int = 1, max_reduction: float = 0.8):
    if zirh <= 0:
        return saldiri
    reduction = min(zirh / (zirh + 30), max_reduction)  # daha hızlı azalma
    hasar = int(saldiri * (1 - reduction))
    return max(hasar, min_hasar)

def zirh_azalt(zirh: int, hasar: int, oran: float = 0.3):
    return max(0, zirh - int(hasar * oran))

# ---------- Boss Durumu (global) ----------
BOSS_AKTIF = False
BOSS_KAZANAN_ID = None
BOSS_MESAJ_ID = None
BOSS_KANAL_ID = None
BOSS_NICK = None
BOSS_CAN = None
BOSS_MAX_CAN = None
BOSS_SON_VURAN = None
BOSS_VURUS_GECMISI = []
BOSS_ISIMLERI = ["Ejderha Lordu", "Kara Şövalye", "Gölge Canavarı", "Ateş Elementali", "Buz Devri", "Kaos Ruhu"]

# ---------- GIF / API Yardımcıları ----------
def tenor_gif_cek(query, contentfilter="high"):
    cfg = load_config()
    api_key = cfg.get("TENOR_API_KEY", "")
    if not api_key:
        return None
    url = f"https://tenor.googleapis.com/v2/search?q={query}&key={api_key}&limit=25&contentfilter={contentfilter}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("results"):
            return random.choice([item["media_formats"]["gif"]["url"] for item in data["results"]])
    except Exception:
        return None
    return None

def kawaii_sfw_gif():
    cfg = load_config()
    token = cfg.get("KAWAII_TOKEN", "anonymous")
    endpoints = [
        "hug","kiss","pat","slap","cuddle","poke","dance","laugh","wave","wink","nom","punch",
        "shoot","stare","bite","confused","lick","love","pout","run","scared","smile"
    ]
    random.shuffle(endpoints)
    for ep in endpoints:
        try:
            url = f"https://kawaii.red/api/gif/{ep}?token={token}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("response") and "error" not in data:
                    return data.get("response")
        except Exception:
            continue
    return None

async def redgifs_nsfw_gif():
    # İstersen burayı async redgifs client ile sürdür
    try:
        from redgifs.aio import API
        api = API()
        await api.login()
        tags = ["hentai","anime","cartoon","animated","ecchi","japan","manga"]
        for tag in tags:
            result = await api.search(tag, count=30)
            if result and result.gifs:
                gif = random.choice(result.gifs)
                return gif.urls.sd or gif.urls.hd or gif.web_url
    except Exception:
        return None
    return None

def log_dm_message(user_id: int, message_id: int):
    log = load_json(DM_LOG_FILE, [])
    log.append({
        "user_id": user_id,
        "message_id": message_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    save_json(DM_LOG_FILE, log)

# ---------- Bot Sınıfı ----------
class MyBot(commands.Bot):
    async def setup_hook(self):
        # Boss otomatik belirleme görevini başlat
        self.loop.create_task(boss_oto_belir(self))

bot = MyBot(command_prefix="!", intents=intents)

# ---------- Hata / Hazır ----------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Slash sync error:", e)
    print(f"Bot {bot.user} olarak giriş yaptı ve slash komutları senkronize edildi.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        kalan = int(error.retry_after)
        await safe_send(ctx, f"⏳ Bu komutu tekrar kullanmak için **{kalan} sn** beklemelisin.")
        return
    raise error

# ---------- Özel Mesajlar ----------
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

# ---------- Bar/Stat Yardımcıları ----------
def bar(val, maxv, icon):
    bar_len = 20
    oran = (val / maxv) if maxv else 0
    dolu = int(bar_len * oran)
    return f"{icon} {val}/{maxv}\n" + ("█" * dolu + "░" * (bar_len - dolu))

def toplam_can(karakter):
    items = load_items()
    can = karakter.get("max_can", 150)
    giyili = karakter.get("giyili", {})
    for _, item_id in giyili.items():
        if item_id and item_id in items:
            can += items[item_id].get("can", 0)
    return can

def toplam_zirh(karakter):
    items = load_items()
    zirh = 0
    giyili = karakter.get("giyili", {})
    for _, item_id in giyili.items():
        if item_id and item_id in items:
            zirh += items[item_id].get("zirh", 0)
    return zirh

# =========================================================
# ===================== HYBRID KOMUTLAR ===================
# =========================================================

# ---- /karakter [kullanıcı] ----
@commands.hybrid_command(name="karakter", description="Kendi karakterini veya etiketlediğin kullanıcının karakterini gösterir.")
@app_commands.describe(kullanici="Profilini görmek istediğin kullanıcı")
@commands.cooldown(1, 10, commands.BucketType.user)
async def karakter(ctx: commands.Context, kullanici: discord.Member | None = None):
    cfg = load_config()
    OZEL_KULLANICILAR = cfg.get("OZEL_KULLANICILAR", [])

    # Özel selamlama
    if ctx.author.id in OZEL_KULLANICILAR:
        data = load_data()
        if str(ctx.author.id) not in data:
            await safe_send(ctx, OZEL_ILK_ILtIFAT)
        else:
            await safe_send(ctx, random.choice(OZEL_ILtIFATLAR))

    hedef = kullanici or ctx.author
    user_id = hedef.id
    data = load_data()
    key = str(user_id)

    if key not in data:
        if hedef == ctx.author:
            data[key] = {
                "guc": 10, "para": 100, "seviye": 1, "xp": 0,
                "train_sayisi": 0, "is_sayisi": 0,
                "max_can": 150, "mevcut_can": 150,
                "zirh": 0, "mevcut_zirh": 0,
                "envanter": [], "giyili": {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None}
            }
            save_data(data)
            await safe_send(ctx,
                f"🎉 {ctx.author.mention} macerana başlamak için ilk karakterin oluşturuldu!\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💪 Güç: 10 | 💰 Para: 100 | 🧭 Seviye: 1 | ✨ XP: 0\n"
                f"Artık `/train`, `/is_` ve `/savas` komutlarını kullanabilirsin!"
            )
        else:
            await safe_send(ctx, f"❌ {hedef.mention} henüz bir karakter oluşturmadı!")
        return

    karakter = data[key]
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
        f"🧙‍♂️ **{hedef.display_name} Karakter Bilgileri**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💪 Güç: {guc}\n"
        f"💰 Para: {para}\n"
        f"🧭 Seviye: {seviye}\n"
        f"✨ XP: {xp} / {xp_gerekli} ({int(xp/xp_gerekli*100) if xp_gerekli else 0}%)\n"
        f"🏋️‍♂️ Toplam Antrenman: {train_sayisi} | 💼 Toplam İş: {is_sayisi}\n"
        f"━━━━━━━━━━━━━━━━━━\n{canbar}\n{zirhbar}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ Statlarını güçlendirmek için marketten ekipman alabilir, `/envanter` ile eşyalarını görebilirsin."
    )
    await safe_send(ctx, mesaj)

# ---- /train ----
@commands.hybrid_command(name="train", description="Antrenman yaparak gücünü artır.")
@commands.cooldown(1, 10, commands.BucketType.user)
async def train(ctx: commands.Context):
    cfg = load_config()
    OZEL_KULLANICILAR = cfg.get("OZEL_KULLANICILAR", [])
    if ctx.author.id in OZEL_KULLANICILAR:
        await safe_send(ctx, random.choice(OZEL_ILtIFATLAR))

    user_id = ctx.author.id
    karakter, _ = get_or_create_user(user_id)

    karakter["train_sayisi"] += 1
    seviye = karakter.get("seviye", 1)
    train_sayisi = karakter["train_sayisi"]
    artis = random.randint(1, 5) + (seviye // 2) + (train_sayisi // 10)
    xp_kazanc = max(3, int(seviye * 2))

    karakter["guc"] += artis
    karakter["xp"] = karakter.get("xp", 0) + xp_kazanc

    # Seviye atlama
    seviye_atlama_mesaj = ""
    while karakter["xp"] >= gereken_xp(karakter["seviye"]):
        await seviye_atlat(ctx, karakter, user_id)
        seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"

    data = load_data()
    data[str(user_id)] = karakter
    save_data(data)

    await safe_send(ctx,
        f"🏋️‍♂️ **Antrenman Sonucu**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💪 Kazanılan Güç: +{artis}\n"
        f"✨ Kazanılan XP: +{xp_kazanc}\n"
        f"🏋️‍♂️ Toplam Antrenman: {train_sayisi}\n"
        f"💪 Yeni Güç: {karakter['guc']}\n"
        f"🔥 İlerleme iyi gidiyor!{seviye_atlama_mesaj}"
    )

# ---- /is_ ----
@commands.hybrid_command(name="is_", description="Çalışarak altın ve birkaç XP kazan.")
@commands.cooldown(1, 10, commands.BucketType.user)
async def is_(ctx: commands.Context):
    cfg = load_config()
    OZEL_KULLANICILAR = cfg.get("OZEL_KULLANICILAR", [])
    if ctx.author.id in OZEL_KULLANICILAR:
        await safe_send(ctx, random.choice(OZEL_ILtIFATLAR))

    user_id = ctx.author.id
    karakter, _ = get_or_create_user(user_id)
    karakter["is_sayisi"] += 1
    seviye = karakter.get("seviye", 1)
    is_sayisi = karakter["is_sayisi"]
    sans = random.random()

    data = load_data()
    if sans < 0.05:
        miktar = random.randint(5000, 10000) + seviye * 100 + is_sayisi * 10
        xp_kazanc = max(10, int(seviye * 5))
        karakter["para"] += miktar
        karakter["xp"] = karakter.get("xp", 0) + xp_kazanc

        seviye_atlama_mesaj = ""
        while karakter["xp"] >= gereken_xp(karakter["seviye"]):
            await seviye_atlat(ctx, karakter, user_id)
            seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"

        data[str(user_id)] = karakter
        save_data(data)
        await safe_send(ctx,
            f"💎 **BÜYÜK ÖDÜL!**\n"
            f"🪙 +{miktar} altın | ✨ +{xp_kazanc} XP\n"
            f"💼 Toplam İş: {is_sayisi}\n"
            f"💰 Yeni Bakiye: {karakter['para']}{seviye_atlama_mesaj}"
        )
    else:
        miktar = random.randint(10, 50) + seviye * 5 + (is_sayisi // 10) * 3
        xp_kazanc = max(2, int(seviye * 1))
        karakter["para"] += miktar
        karakter["xp"] = karakter.get("xp", 0) + xp_kazanc

        seviye_atlama_mesaj = ""
        while karakter["xp"] >= gereken_xp(karakter["seviye"]):
            await seviye_atlat(ctx, karakter, user_id)
            seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"

        data[str(user_id)] = karakter
        save_data(data)
        await safe_send(ctx,
            f"💼 **İşten Kazanç**\n"
            f"🪙 +{miktar} altın | ✨ +{xp_kazanc} XP\n"
            f"💼 Toplam İş: {is_sayisi}\n"
            f"💰 Yeni Bakiye: {karakter['para']}{seviye_atlama_mesaj}"
        )

# ---- /savas [zorluk] ----
def dusman_statlari(oyuncu, zorluk):
    oranlar = {'kolay': 0.6, 'normal': 1.0, 'zor': 1.4}
    o = oranlar.get(zorluk, 1.0)
    seviye_bonus = oyuncu['seviye'] * 1
    return {
        'seviye': oyuncu['seviye'],
        'guc': int((oyuncu['guc'] + seviye_bonus) * o),
        'can': int(oyuncu['can'] * o),
        'zirh': int(oyuncu['zirh'] * o)
    }

@commands.hybrid_command(name="savas", description="Arenada savaş. Zorluk: kolay/normal/zor")
@app_commands.describe(zorluk="kolay | normal | zor")
@commands.cooldown(1, 10, commands.BucketType.user)
async def savas(ctx: commands.Context, zorluk: str = "normal"):
    user_id = ctx.author.id
    karakter, _ = get_or_create_user(user_id)
    seviye = karakter.get("seviye", 1)
    guc = karakter.get("guc", 10)

    # Ekipman etkisi
    items = load_items()
    giyili = karakter.get("giyili", {})
    toplam_z = 0
    ekipman_can = 0
    for _, item_id in giyili.items():
        if item_id and item_id in items:
            toplam_z += items[item_id].get("zirh", 0)
            ekipman_can += items[item_id].get("can", 0)

    base_max_can = karakter.get("max_can", 150)
    toplam_max_can = base_max_can + ekipman_can

    mevcut_can = karakter.get("mevcut_can", toplam_max_can)
    mevcut_can = min(mevcut_can, toplam_max_can)
    mevcut_zirh = karakter.get("mevcut_zirh", toplam_z)
    mevcut_zirh = min(mevcut_zirh, toplam_z)

    if mevcut_can <= 0:
        await safe_send(ctx, "❤️‍🩹 Canın sıfır! Marketten iksir al (`/satinal 11`) veya bekle.")
        return

    if zorluk == "zor" and seviye < 3:
        await safe_send(ctx, "❌ Zor savaş için en az **3. seviye** olmalısın.")
        return

    oyuncu = {'seviye': seviye, 'guc': guc, 'can': mevcut_can, 'zirh': mevcut_zirh}
    dusman = dusman_statlari(oyuncu, zorluk)
    max_z = oyuncu['zirh']
    max_c_d = dusman['can']
    max_z_d = dusman['zirh']

    tur = 1
    oyuncu_canbar = bar(oyuncu['can'], toplam_max_can, "❤️ Can:")
    oyuncu_zirhbar = bar(oyuncu['zirh'], max_z, "🛡️ Zırh:")
    dusman_canbar = bar(dusman['can'], max_c_d, "❤️ Can:")
    dusman_zirhbar = bar(dusman['zirh'], max_z_d, "🛡️ Zırh:")

    msg = (
        f"⚔️ **Savaş Başladı!**\n"
        f"Sen: {oyuncu['can']}/{toplam_max_can} can, {oyuncu['zirh']} zırh\n"
        f"Düşman: {dusman['can']} can, {dusman['zirh']} zırh\n"
        f"━━━━━━━━━━━\n**Tur {tur}**\nSen: - 0 can | Düşman: - 0 can\n\n"
        f"Sen\n{oyuncu_canbar}\n{oyuncu_zirhbar}\n"
        f"Düşman\n{dusman_canbar}\n{dusman_zirhbar}\n"
    )
    mesaj = await safe_send(ctx, msg)

    # Eğer interaction ile gönderildiyse followup düzenleme gerekir
    if getattr(ctx, "interaction", None) and not isinstance(mesaj, discord.Message):
        # interaction ile giden ilk yanıttan sonra düzenlemek için yeni mesaj al
        kanal = ctx.channel
        mesaj = await kanal.send("⏳ ...")

    await asyncio.sleep(1.5)

    log = msg
    while oyuncu['can'] > 0 and dusman['can'] > 0:
        # Oyuncu saldırısı
        oyuncu_atak = int(oyuncu['guc'] * random.uniform(0.98, 1.02))
        dusman_hasar = hesapla_gercek_hasar(oyuncu_atak, dusman['zirh'])
        dusman['can'] -= dusman_hasar
        dusman['zirh'] = zirh_azalt(dusman['zirh'], dusman_hasar)

        oyuncu_canbar = bar(oyuncu['can'], toplam_max_can, "❤️ Can:")
        oyuncu_zirhbar = bar(oyuncu['zirh'], max_z, "🛡️ Zırh:")
        dusman_canbar = bar(dusman['can'], max_c_d, "❤️ Can:")
        dusman_zirhbar = bar(dusman['zirh'], max_z_d, "🛡️ Zırh:")

        log = (
            f"⚔️ **Savaş Başladı!**\n"
            f"Sen: {toplam_max_can} can, {max_z} zırh | "
            f"Düşman: {max_c_d} can, {max_z_d} zırh\n"
            f"━━━━━━━━━━━\n**Tur {tur}**\n"
            f"Sen: - 0 can\n"
            f"Düşman: -{dusman_hasar} can (-{int(dusman_hasar*0.3)} zırh)\n\n"
            f"Sen\n{oyuncu_canbar}\n{oyuncu_zirhbar}\n"
            f"Düşman\n{dusman_canbar}\n{dusman_zirhbar}\n"
        )
        await mesaj.edit(content=(log[-1900:] if len(log) > 1900 else log))
        await asyncio.sleep(1)

        if dusman['can'] <= 0:
            break

        # Düşman saldırısı
        dusman_atak = int(dusman['guc'] * random.uniform(0.98, 1.02))
        oyuncu_hasar = hesapla_gercek_hasar(dusman_atak, oyuncu['zirh'])
        oyuncu['can'] -= oyuncu_hasar
        oyuncu['zirh'] = zirh_azalt(oyuncu['zirh'], oyuncu_hasar)

        oyuncu_canbar = bar(oyuncu['can'], toplam_max_can, "❤️ Can:")
        oyuncu_zirhbar = bar(oyuncu['zirh'], max_z, "🛡️ Zırh:")
        dusman_canbar = bar(dusman['can'], max_c_d, "❤️ Can:")
        dusman_zirhbar = bar(dusman['zirh'], max_z_d, "🛡️ Zırh:")

        log = (
            f"⚔️ **Savaş Başladı!**\n"
            f"Sen: {toplam_max_can} can, {max_z} zırh | "
            f"Düşman: {max_c_d} can, {max_z_d} zırh\n"
            f"━━━━━━━━━━━\n**Tur {tur}**\n"
            f"Sen: -{oyuncu_hasar} can (-{int(oyuncu_hasar*0.3)} zırh)\n"
            f"Düşman: - 0 can\n\n"
            f"Sen\n{oyuncu_canbar}\n{oyuncu_zirhbar}\n"
            f"Düşman\n{dusman_canbar}\n{dusman_zirhbar}\n"
        )
        await mesaj.edit(content=(log[-1900:] if len(log) > 1900 else log))
        await asyncio.sleep(1)
        tur += 1

    # Sonuçlar
    if oyuncu['can'] > 0:
        if zorluk == 'kolay':
            guc_odul = max(1, int(seviye * 0.5))
            xp_odul = max(8, int(seviye * 5))
            para_odul = max(15, int(guc * 1.5))
        elif zorluk == 'normal':
            guc_odul = max(2, int(seviye * 1))
            xp_odul = max(15, int(seviye * 10))
            para_odul = max(25, int(guc * 3))
        else:
            guc_odul = max(3, int(seviye * 2))
            xp_odul = max(25, int(seviye * 15))
            para_odul = max(50, int(guc * 6))

        karakter['guc'] += guc_odul
        karakter['xp'] = karakter.get('xp', 0) + xp_odul
        karakter['para'] += para_odul

        seviye_atlama_mesaj = ""
        while karakter['xp'] >= gereken_xp(karakter['seviye']):
            await seviye_atlat(ctx, karakter, user_id)
            seviye_atlama_mesaj = f"\n🎊 **SEVİYE ATLADIN!** Yeni seviye: {karakter['seviye']}"

        # Item drop (opsiyonel basit)
        drop_mesaj = ""  # istersen burada get_drop_item kullan
        sonuc = f"🏆 Zafer! +{guc_odul} güç, +{xp_odul} XP, +{para_odul} altın.{seviye_atlama_mesaj}{drop_mesaj}"
    else:
        if zorluk == 'kolay':
            guc_ceza = 0
            para_ceza = max(5, int(guc * 0.5))
        elif zorluk == 'normal':
            guc_ceza = max(1, int(seviye * 0.3))
            para_ceza = max(10, int(guc * 1))
        else:
            guc_ceza = max(1, int(seviye * 0.5))
            para_ceza = max(20, int(guc * 2))

        karakter['guc'] = max(1, karakter['guc'] - guc_ceza)
        karakter['para'] = max(0, karakter['para'] - para_ceza)
        sonuc = f"💀 Kaybettin! -{guc_ceza} güç, -{para_ceza} altın."

    karakter['mevcut_can'] = max(0, oyuncu['can'])
    karakter['mevcut_zirh'] = max(0, oyuncu['zirh'])
    data = load_data()
    data[str(user_id)] = karakter
    save_data(data)

    final_log = (log + f"\n{sonuc}")
    if len(final_log) > 2000:
        final_log = final_log[-2000:]
    await mesaj.edit(content=final_log)

# ---- /duello @kullanıcı ----
class DuelView(discord.ui.View):
    def __init__(self, challenger: discord.Member, timeout=30):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.accepted: bool | None = None

    @discord.ui.button(label="Kabul", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message("Kendi teklifini sen kabul edemezsin.", ephemeral=True)
            return
        self.accepted = True
        await interaction.response.edit_message(content="✅ Düello kabul edildi!", view=None)
        self.stop()

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message("Kendi teklifini sen reddedemezsin.", ephemeral=True)
            return
        self.accepted = False
        await interaction.response.edit_message(content="❌ Düello reddedildi.", view=None)
        self.stop()

@commands.hybrid_command(name="duello", description="Etiketlediğin kullanıcıya karşı düello.")
@app_commands.describe(rakip="Düello yapmak istediğin kullanıcı")
@commands.cooldown(1, 10, commands.BucketType.user)
async def duello(ctx: commands.Context, rakip: discord.Member):
    user_id = ctx.author.id
    rakip_id = rakip.id
    if user_id == rakip_id:
        await safe_send(ctx, "❌ Kendi kendinle düello yapamazsın!")
        return

    karakter1, _ = get_or_create_user(user_id)
    karakter2, _ = get_or_create_user(rakip_id)
    guc1 = karakter1["guc"]
    guc2 = karakter2["guc"]

    view = DuelView(challenger=ctx.author)
    msg = await safe_send(ctx, f"{rakip.mention}, {ctx.author.mention} sana düello teklif ediyor!", view=view)
    if getattr(ctx, "interaction", None) and not isinstance(msg, discord.Message):
        # interaction ilk yanıt ise, düğmeli gerçek mesajı ayrıca gönder
        msg = await ctx.channel.send(f"{rakip.mention}, {ctx.author.mention} sana düello teklif ediyor!", view=view)

    await view.wait()
    if view.accepted is None:
        await msg.edit(content=f"⏰ {rakip.mention} zamanında yanıt vermedi, düello iptal.", view=None)
        return
    if view.accepted is False:
        await msg.edit(content=f"❌ {rakip.mention} düello teklifini reddetti.", view=None)
        return

    toplam_guc = guc1 + guc2
    if toplam_guc == 0:
        await msg.edit(content="Her iki karakterin de gücü 0, düello yapılamaz.", view=None)
        return

    sans = random.random()
    mucize = False
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
        else:
            kazanan, kaybeden = rakip, ctx.author
            kazanan_id, kaybeden_id = rakip_id, user_id

    para_miktari = random.randint(200, 500)
    data = load_data()
    kaybeden_para = data[str(kaybeden_id)]["para"]
    gercek_kayip = min(para_miktari, kaybeden_para)
    data[str(kazanan_id)]["para"] += gercek_kayip
    data[str(kaybeden_id)]["para"] = max(0, kaybeden_para - gercek_kayip)
    save_data(data)

    if mucize:
        text = (
            f"🌪️✨ MUCİZE! {kazanan.mention}, {kaybeden.mention}'a karşı inanılmaz bir zafer kazandı!\n"
            f"🏆 Kazanan: +{gercek_kayip} altın | 💸 Kaybeden: -{gercek_kayip} altın"
        )
    else:
        vary = [
            f"⚔️ {kazanan.mention}, {kaybeden.mention}'i alt etti! 🏆 +{gercek_kayip} altın",
            f"🗡️ {kazanan.mention} zekâsıyla kazandı! +{gercek_kayip} altın",
            f"🔥 {kazanan.mention} arenada fırtına gibi esti! +{gercek_kayip} altın"
        ]
        text = random.choice(vary) + f"\n💸 {kaybeden.mention} -{gercek_kayip} altın"
    await msg.edit(content=text, view=None)

# ---- /yardim ----
@commands.hybrid_command(name="yardim", description="Bot komutlarını listeler.")
async def yardim(ctx: commands.Context):
    cfg = load_config()
    ADMIN_IDS = cfg.get("ADMIN_IDS", [])

    yardim_mesaj = (
        "✨ **Komutlar ve Açıklamaları** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "`/karakter [@kullanıcı]`  → Karakter bilgisi.\n"
        "`/train`                   → Antrenman yap, güç/XP kazan.\n"
        "`/is_`                     → Çalış, altın/az XP kazan.\n"
        "`/savas [zorluk]`          → Arenada savaş (kolay/normal/zor).\n"
        "`/duello @kullanıcı`       → Düello.\n"
        "`/market`                  → Klasik market.\n"
        "`/itemmarket`              → Ekipman marketi.\n"
        "`/satinal <kod>`           → Marketten satın al.\n"
        "`/envanter`                → Envanter + giyili ekipman.\n"
        "`/giy <item_kodu>`         → Ekipman giy/çıkar.\n"
        "`/bossdurum`               → Aktif boss bilgisi.\n"
        "`/bossvurus`               → Boss'a saldır.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if ctx.author.id in ADMIN_IDS:
        yardim_mesaj += (
            "\n**🔒 Admin Komutları (slash):**\n"
            "`/bossbelir` - Bossu manuel ortaya çıkarır.\n"
            "`/duyuru <mesaj>` - Genel duyuru atar.\n"
            "`/duyuru_sil <mesaj_id>` - Duyuru mesajını siler.\n"
            "`/temizle <miktar>` - Kanalda mesaj siler.\n"
        )
    for p in chunk_text(yardim_mesaj):
        await safe_send(ctx, p)

# ---- Market / Itemmarket ----
@commands.hybrid_command(name="market", description="Klasik market ürünlerini gösterir.")
@commands.cooldown(1, 10, commands.BucketType.user)
async def market(ctx: commands.Context):
    MARKET = {
        "1": {"isim": "Sürpriz Görsel Paketi", "aciklama": "Rastgele SFW görsel/gif.", "fiyat": 500, "tip": "gif"},
        "2": {"isim": "Mega Sürpriz Paketi", "aciklama": "Nadir SFW görsel/gif.", "fiyat": 1500, "tip": "mega_gif"},
        "3": {"isim": "Güç Paketi", "aciklama": "+10 güç", "fiyat": 300, "tip": "guc"},
        "4": {"isim": "Güç Yenileme", "aciklama": "+20 güç", "fiyat": 800, "tip": "guc_yenile"},
        "5": {"isim": "XP Paketi", "aciklama": "+30 XP", "fiyat": 200, "tip": "xp"},
        "10": {"isim": "Zırh Yenileme", "aciklama": "Zırhını full yapar.", "fiyat": 200, "tip": "zirh_onar"},
        "11": {"isim": "İyileşme İksiri", "aciklama": "Canını full yapar.", "fiyat": 200, "tip": "can_onar"},
    }
    msg = "**🛒 Market:**\n"
    for kod, urun in MARKET.items():
        msg += f"`{kod}` - {urun['isim']} ({urun['fiyat']} altın): {urun['aciklama']}\n"
    msg += "\nEkipman marketi için: `/itemmarket` yaz!\nSatın almak için: `/satinal <kod>`"
    await safe_send(ctx, msg)

@commands.hybrid_command(name="itemmarket", description="Ekipman marketini listeler.")
@commands.cooldown(1, 10, commands.BucketType.user)
async def itemmarket(ctx: commands.Context):
    items = load_items()
    market_items = [(k, v) for k, v in items.items() if "fiyat" in v]
    msg = "**🛡️ Ekipman Marketi:**\n"
    for kod, it in market_items:
        msg += f"`{kod}` - {it['isim']} ({it['nadirlik']}) [+{it.get('guc',0)} güç, +{it.get('can',0)} can] - Fiyat: {it['fiyat']} altın\n"
    msg += "\nSatın almak için: `/satinal <item_kodu>`"
    await safe_send(ctx, msg)

# ---- Envanter / Giy / Satın Al ----
@commands.hybrid_command(name="envanter", description="Envanterini ve giyili ekipmanı gösterir.")
async def envanter(ctx: commands.Context):
    user_id = str(ctx.author.id)
    data = load_data()
    if user_id not in data:
        await safe_send(ctx, "Önce bir karakter oluşturmalısın! (`/karakter`)")
        return
    items = load_items()
    karakter = data[user_id]
    envanter_list = karakter.get("envanter", [])
    giyili = karakter.get("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})

    # Zırh bar
    max_z = toplam_zirh(karakter)
    mevcut_z = min(karakter.get("mevcut_zirh", max_z), max_z)
    zirh_bar = bar(mevcut_z, max_z, "🛡️ Zırh:")

    # Giyili yazı
    giyili_text = ""
    giyili_ids = set([iid for iid in giyili.values() if iid])
    for slot in ["silah", "kask", "gogus", "pantolon", "bot"]:
        item_id = giyili.get(slot)
        if item_id and item_id in items:
            it = items[item_id]
            giyili_text += f"**{slot.capitalize()}**: {it['isim']} [`{item_id}`] (+{it.get('guc',0)} güç, +{it.get('can',0)} can, +{it.get('zirh',0)} zırh)\n"
        else:
            giyili_text += f"**{slot.capitalize()}**: Yok\n"

    inv_text = ""
    for item_id in envanter_list:
        if item_id in items and item_id not in giyili_ids:
            it = items[item_id]
            inv_text += f"`{item_id}` - {it['isim']} ({it['nadirlik']}) [+{it.get('guc',0)} güç, +{it.get('can',0)} can, +{it.get('zirh',0)} zırh]\n"

    await safe_send(ctx,
        f"**Envanterin:**\n{inv_text if inv_text else 'Hiç item yok.'}\n"
        f"**Giyili Ekipmanlar:**\n{giyili_text}\n{zirh_bar}"
    )

@commands.hybrid_command(name="giy", description="Bir ekipmanı giy veya çıkar.")
@app_commands.describe(item_kodu="Giyeceğin item kodu")
async def giy(ctx: commands.Context, item_kodu: str):
    user_id = str(ctx.author.id)
    data = load_data()
    items = load_items()
    if user_id not in data:
        await safe_send(ctx, "Önce bir karakter oluşturmalısın! (`/karakter`)")
        return
    karakter = data[user_id]
    envanter = karakter.get("envanter", [])
    giyili = karakter.get("giyili", {"silah": None, "kask": None, "gogus": None, "pantolon": None, "bot": None})

    if item_kodu not in envanter and item_kodu not in items:
        await safe_send(ctx, "Bu item envanterinde yok!")
        return
    if item_kodu not in items:
        await safe_send(ctx, "Geçersiz item kodu!")
        return

    item = items[item_kodu]
    tip = item.get("tip")
    slot = {"silah":"silah","kask":"kask","gogus":"gogus","pantolon":"pantolon","bot":"bot"}.get(tip)
    if not slot:
        await safe_send(ctx, "Bu item giyilemez!")
        return

    # Toggle: aynı item giyiliyse çıkar
    if giyili.get(slot) == item_kodu:
        giyili[slot] = None
        if item_kodu not in envanter:
            envanter.append(item_kodu)
        await safe_send(ctx, f"{item['isim']} çıkarıldı ve envantere döndü.")
    else:
        eski = giyili.get(slot)
        if eski and eski not in envanter:
            envanter.append(eski)
        giyili[slot] = item_kodu
        if item_kodu in envanter:
            envanter.remove(item_kodu)
        await safe_send(ctx, f"{item['isim']} giyildi.")

    karakter["giyili"] = giyili
    karakter["envanter"] = envanter
    data[user_id] = karakter
    save_data(data)

@commands.hybrid_command(name="satinal", description="Market veya item marketten satın al.")
@app_commands.describe(item_kodu="Ürün veya ekipman kodu")
async def satinal(ctx: commands.Context, item_kodu: str):
    user_id = str(ctx.author.id)
    data = load_data()
    items = load_items()
    if user_id not in data:
        await safe_send(ctx, "Önce bir karakter oluşturmalısın! (`/karakter`)")
        return
    karakter = data[user_id]

    # Klasik market (kodlar)
    MARKET = {
        "1": {"isim":"Sürpriz Görsel Paketi","aciklama":"SFW görsel/gif","fiyat":500,"tip":"gif"},
        "2": {"isim":"Mega Sürpriz Paketi","aciklama":"Nadir SFW görsel/gif","fiyat":1500,"tip":"mega_gif"},
        "3": {"isim":"Güç Paketi","aciklama":"+10 güç","fiyat":300,"tip":"guc"},
        "4": {"isim":"Güç Yenileme","aciklama":"+20 güç","fiyat":800,"tip":"guc_yenile"},
        "5": {"isim":"XP Paketi","aciklama":"+30 XP","fiyat":200,"tip":"xp"},
        "10":{"isim":"Zırh Yenileme","aciklama":"Zırh full","fiyat":200,"tip":"zirh_onar"},
        "11":{"isim":"İyileşme İksiri","aciklama":"Can full","fiyat":200,"tip":"can_onar"},
    }

    if item_kodu in MARKET:
        urun = MARKET[item_kodu]
        if karakter["para"] < urun["fiyat"]:
            await safe_send(ctx, f"Yeterli paran yok! (Gerekli: {urun['fiyat']})")
            return
        karakter["para"] -= urun["fiyat"]

        if urun["tip"] == "zirh_onar":
            # giyili zırh toplamını hesapla
            max_z = toplam_zirh(karakter)
            karakter["mevcut_zirh"] = max_z
            data[user_id] = karakter
            save_data(data)
            await safe_send(ctx, f"🛡️ Zırhın tamamen onarıldı! ({max_z})")
            return

        if urun["tip"] == "can_onar":
            # giyili can bonuslarıyla max_can
            max_c = toplam_can(karakter)
            karakter["mevcut_can"] = max_c
            data[user_id] = karakter
            save_data(data)
            await safe_send(ctx, f"❤️ Canın tamamen iyileşti! ({max_c})")
            return

        if urun["tip"] in ("gif", "mega_gif"):
            gif_url = kawaii_sfw_gif()
            if gif_url:
                await safe_send(ctx, f"{ctx.author.mention} ödülün: {gif_url}")
            else:
                await safe_send(ctx, "Uygun gif bulunamadı.")
            data[user_id] = karakter
            save_data(data)
            return

        # Diğer paketler (guc/xp vs)
        if urun["tip"] == "guc":
            karakter["guc"] += 10
        elif urun["tip"] == "guc_yenile":
            karakter["guc"] += 20
        elif urun["tip"] == "xp":
            karakter["xp"] = karakter.get("xp", 0) + 30
            # seviye kontrol
            while karakter["xp"] >= gereken_xp(karakter["seviye"]):
                await seviye_atlat(ctx, karakter, int(user_id))
        data[user_id] = karakter
        save_data(data)
        await safe_send(ctx, f"{urun['isim']} satın alındı!")
        return

    # Ekipman marketi (itemler.json)
    if item_kodu not in items:
        await safe_send(ctx, "Geçersiz ürün/item kodu!")
        return
    item = items[item_kodu]
    if "fiyat" not in item:
        await safe_send(ctx, "Bu item markette satılmıyor!")
        return
    if item_kodu in karakter.get("envanter", []):
        await safe_send(ctx, "Bu item zaten envanterinde!")
        return
    if karakter["para"] < item["fiyat"]:
        await safe_send(ctx, f"Yeterli paran yok! (Gerekli: {item['fiyat']})")
        return
    karakter["para"] -= item["fiyat"]
    karakter.setdefault("envanter", []).append(item_kodu)
    data[user_id] = karakter
    save_data(data)
    await safe_send(ctx, f"{item['isim']} envanterine eklendi!")

# ---- Boss Sistemi ----
async def boss_olustur(kanal: discord.TextChannel):
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
    mesaj = await kanal.send(
        f"⚡️ **BOSS ORTAYA ÇIKTI!** ⚡️\nBoss: **{BOSS_NICK}**\nCan: {BOSS_CAN}\n"
        f"`/bossvurus` komutuyla saldırabilirsin!"
    )
    BOSS_MESAJ_ID = mesaj.id
    BOSS_KANAL_ID = kanal.id

async def boss_oto_belir(bot: commands.Bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(random.randint(3600, 7200))  # 1-2 saatte bir
        try:
            # mesaj gönderebileceği rastgele bir kanal seç
            kanallar = []
            for g in bot.guilds:
                for c in g.text_channels:
                    perms = c.permissions_for(g.me)
                    if perms.send_messages:
                        kanallar.append(c)
            if not kanallar:
                continue
            kanal = random.choice(kanallar)
            await boss_olustur(kanal)
        except Exception:
            continue

# Admin: /bossbelir
@commands.hybrid_command(name="bossbelir", description="Bossu manuel ortaya çıkarır (admin).")
@app_commands.default_member_permissions(administrator=True)
async def bossbelir(ctx: commands.Context):
    await boss_olustur(ctx.channel)
    await safe_send(ctx, "✅ Boss belirlendi.")

# /bossvurus
@commands.hybrid_command(name="bossvurus", description="Aktif bossa saldır.")
@commands.cooldown(1, 5, commands.BucketType.user)
async def bossvurus(ctx: commands.Context):
    global BOSS_AKTIF, BOSS_CAN, BOSS_MAX_CAN, BOSS_SON_VURAN, BOSS_VURUS_GECMISI, BOSS_KAZANAN_ID
    if not BOSS_AKTIF or BOSS_CAN is None:
        await safe_send(ctx, "❌ Şu anda aktif bir boss yok!")
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
            mesaj = await ctx.author.send(
                f"🏆 **TEBRİKLER!**\n"
                f"**{BOSS_NICK}** bossuna son vuruşu yaptın!\n"
                f"🔞 Ödül: {gif_url if gif_url else 'Uygun NSFW gif bulunamadı.'}"
            )
            log_dm_message(ctx.author.id, mesaj.id)
            await safe_send(ctx, f"🎉 **{ctx.author.display_name}** bossu **{BOSS_NICK}** devirdi! Ödül DM'de.")
        except Exception:
            await safe_send(ctx, f"{ctx.author.mention} DM'ni açmalısın; ödül gönderilemedi!")
        cfg = load_config()
        users = set(cfg.get("BOSS_NSFWMARKET_USERS", []))
        users.add(user_id)
        cfg["BOSS_NSFWMARKET_USERS"] = list(users)
        save_config(cfg)
    else:
        dolu = int(BOSS_CAN / BOSS_MAX_CAN * 20)
        can_bar = "█" * dolu + "░" * (20 - dolu)
        await safe_send(ctx,
            f"⚔️ **{ctx.author.display_name} boss'a saldırdı!**\n"
            f"💥 Vuruş: **{vurus}**\n"
            f"🩸 Kalan Can: **{BOSS_CAN}/{BOSS_MAX_CAN}**\n{can_bar}"
        )

# /bossdurum
@commands.hybrid_command(name="bossdurum", description="Aktif boss durumunu gösterir.")
async def bossdurum(ctx: commands.Context):
    if not BOSS_AKTIF or BOSS_CAN is None:
        await safe_send(ctx, "❌ Şu anda aktif bir boss yok!")
        return
    son_vuran = BOSS_SON_VURAN.display_name if BOSS_SON_VURAN else "Yok"
    dolu = int(BOSS_CAN / BOSS_MAX_CAN * 20)
    can_bar = "█" * dolu + "░" * (20 - dolu)
    vuruslar = "\n".join([
        f"{i+1}. {v['ad']} - 💥 {v['vurus']}" for i, v in enumerate(BOSS_VURUS_GECMISI[-5:])
    ]) or "Henüz saldırı yok!"
    await safe_send(ctx,
        f"👹 **Boss Bilgisi**\n"
        f"🧟‍♂️ Boss: **{BOSS_NICK}**\n"
        f"🩸 Can: **{BOSS_CAN}/{BOSS_MAX_CAN}**\n{can_bar}\n"
        f"🔪 Son Vuran: **{son_vuran}**\n"
        f"🗡️ **Son 5 Saldırı:**\n{vuruslar}"
    )

# ---- Admin Yardımcıları ----
@commands.hybrid_command(name="duyuru", description="Genel duyuru atar (admin).")
@app_commands.describe(mesaj="Duyuru metni")
@app_commands.default_member_permissions(administrator=True)
async def duyuru(ctx: commands.Context, *, mesaj: str):
    embed = discord.Embed(
        title="📢 **GENEL DUYURU** 📢",
        description=mesaj,
        color=0xFF6B6B,
        timestamp=datetime.utcnow() + timedelta(hours=3)  # TR saati
    )
    embed.set_footer(text=f"Duyuru: {ctx.author.display_name}")
    await safe_send(ctx, embed=embed)
    # Slash'ta komut mesajı görünmez; prefix'te komut mesajını silmeyi deneyebiliriz
    try:
        if ctx.message:
            await ctx.message.delete()
    except Exception:
        pass

@commands.hybrid_command(name="duyuru_sil", description="Belirtilen mesaj ID'li duyuruyu siler (admin).")
@app_commands.describe(mesaj_id="Silinecek mesaj ID'si")
@app_commands.default_member_permissions(administrator=True)
async def duyuru_sil(ctx: commands.Context, mesaj_id: str):
    try:
        mesaj = await ctx.channel.fetch_message(int(mesaj_id))
        await mesaj.delete()
        await safe_send(ctx, "✅ Duyuru silindi.")
    except discord.NotFound:
        await safe_send(ctx, "❌ Mesaj bulunamadı.")
    except discord.Forbidden:
        await safe_send(ctx, "❌ Bu mesajı silme yetkim yok.")
    except Exception as e:
        await safe_send(ctx, f"❌ Hata: {e}")

@commands.hybrid_command(name="temizle", description="Kanalda belirtilen sayıda mesaj siler (admin).")
@app_commands.describe(miktar="Silinecek mesaj sayısı")
@app_commands.default_member_permissions(administrator=True)
async def temizle(ctx: commands.Context, miktar: int = 1):
    if ctx.guild is None:
        await safe_send(ctx, "Bu komut sadece sunucuda çalışır.")
        return
    silinen = 0
    async for msg in ctx.channel.history(limit=miktar+1):
        try:
            await msg.delete()
            silinen += 1
        except Exception:
            pass
    info = await ctx.channel.send(f"{silinen} mesaj silindi.")
    await info.delete(delay=3)

# ---------- Token & Çalıştır ----------
def main():
    cfg = load_config()
    token = cfg.get("TOKEN")
    if not token:
        print("config.json içinde TOKEN bulunamadı.")
        return
    bot.run(token)

if __name__ == "__main__":
    main()

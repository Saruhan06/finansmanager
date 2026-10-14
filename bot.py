import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Sizin bot şifreniz
TOKEN = "8648047454:AAFhiWDO12nvm2tEp2wW"

def ana_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🪙 Popüler Kriptolar", callback_data='menu_kripto')],
        [InlineKeyboardButton("🧮 Hızlı Hesap Makinesi", callback_data='menu_hesap')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 **Gelişmiş Yatırım ve İndikatör Asistanı Aktif!**\n\n"
        "🔍 **BIST & Kripto Teknik Analiz Araması:**\n"
        "İstediğiniz varlığın fiyatını ve **RSI indikatör analizini** görmek için kodunu mesaj olarak gönderin!\n\n"
        "🔹 **BIST için direkt yazın:** `THYAO`, `SASA`, `FONET`\n"
        "🔹 **Kripto için sonuna USDT ekleyin:** `BTCUSDT`, `ETHUSDT`\n\n"
        "Diğer araçlar için aşağıdaki butonları kullanabilirsiniz:",
        reply_markup=ana_menu_keyboard(),
        parse_mode="Markdown"
    )

def rsi_hesapla(kapanislar, periyot=14):
    if len(kapanislar) < periyot + 1:
        return None
    kayiplar = []
    kazanclar = []
    for i in range(1, len(kapanislar)):
        fark = kapanislar[i] - kapanislar[i-1]
        if fark > 0:
            kazanclar.append(fark)
            kayiplar.append(0)
        else:
            kazanclar.append(0)
            kayiplar.append(abs(fark))
            
    ort_kazanc = sum(kazanclar[:periyot]) / periyot
    ort_kayip = sum(kayiplar[:periyot]) / periyot
    
    if ort_kayip == 0:
        return 100
        
    rs = ort_kazanc / ort_kayip
    rsi = 100 - (100 / (1 + rs))
    return rsi

async def teknik_analiz_yap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kod = update.message.text.upper().strip()
    bekleme = await update.message.reply_text(f"🔍 `{kod}` verileri indiriliyor ve teknik analiz hesaplanıyor...")
    
    # Varlık BIST mi Kripto mu ayırt etme
    is_bist = not kod.endswith("USDT")
    
    if is_bist:
        url = f"https://yahoo.com{kod}.IS?range=1mo&interval=1d"
    else:
        url = f"https://binance.com{kod}&interval=1d&limit=30"
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        if is_bist:
            req = urllib.request.Request(url, headers=headers) if 'urllib' in globals() else None
            # Kolaylık için requests kütüphanesini kullanalım
            res = requests.get(url, headers=headers).json()
            kapanislar = res['chart']['result'][0]['indicators']['quote'][0]['close']
            fiyat = res['chart']['result'][0]['meta']['regularMarketPrice']
            kapanis_temiz = [x for x in kapanislar if x is not None]
        else:
            res = requests.get(url).json()
            kapanis_temiz = [float(x[4]) for x in res]
            fiyat = kapanis_temiz[-1]

        rsi = rsi_hesapla(kapanis_temiz)
        
        rsi_yorum = "🔄 Nötr Bölge"
        if rsi:
            if rsi <= 30: rsi_yorum = "🟢 Aşırı Satım (Ucuz) - Alım Fırsatı Olabilir"
            elif rsi >= 70: rsi_yorum = "🔴 Aşırı Alım (Pahalı) - Kar Satışı Gelebilir"
            rsi_metni = f"`{rsi:.2f}`"
        else:
            rsi_metni = "Hesaplanamadı (Yetersiz veri)"

        mesaj = (
            f"📊 **{kod} Analiz Raporu**\n\n"
            f"💰 Güncel Fiyat: `{fiyat:.2f} {'TL' if is_bist else 'USD'}`\n"
            f"📈 14 Günlük RSI: {rsi_metni}\n"
            f"📢 Sinyal Durumu: **{rsi_yorum}**"
        )
        await bekleme.edit_text(mesaj, parse_mode="Markdown")
    except:
        await bekleme.edit_text(f"❌ `{kod}` bulunamadı. Lütfen geçerli bir hisse (THYAO) veya kripto çifti (BTCUSDT) girin.")

async def buton_tiklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'ana_menu':
        await query.edit_message_text("📊 **Ana Menü**\n\nLütfen bir işlem seçin veya analiz için kod gönderin:", reply_markup=ana_menu_keyboard(), parse_mode="Markdown")
    elif data == 'menu_kripto':
        keyboard = [
            [InlineKeyboardButton("Bitcoin (BTC)", callback_data='k_BTCUSDT'), InlineKeyboardButton("Ethereum (ETH)", callback_data='k_ETHUSDT')],
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data='ana_menu')]
        ]
        await query.edit_message_text("🪙 **Popüler Kripto Paralar**:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == 'menu_hesap':
        keyboard = [
            [InlineKeyboardButton("100 TL", callback_data='h_100'), InlineKeyboardButton("500 TL", callback_data='h_500')],
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data='ana_menu')]
        ]
        await query.edit_message_text("🧮 **Risk Hesaplama**:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data.startswith('k_'):
        coin = data.split('_')[1]
        context.user_data['temp_coin'] = coin
        # Butondan tıklanınca da direkt analiz fonksiyonunu tetiklemek için mesaj taklidi yapıyoruz
        class FakeMessage:
            text = coin
        class FakeUpdate:
            message = FakeMessage()
            def __init__(self):
                self.message = FakeMessage()
        update.message = FakeMessage()
        await teknik_analiz_yap(update, context)
    elif data.startswith('h_'):
        maliyet = float(data.split('_')[1])
        await query.edit_message_text(text=f"🧮 **Risk Analizi**\n\n🔹 Maliyet: `{maliyet}`\n🚨 Stop (%5): `{maliyet*0.95:.2f}`\n🎯 Hedef (%10): `{maliyet*1.10:.2f}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Geri", callback_data='menu_hesap')]]), parse_mode="Markdown")

def main():
    # Render port yönetimi için dinamik port ayarı
    port = int(os.environ.get('PORT', 8443))
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buton_tiklama))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, teknik_analiz_yap))
    
    print("Gelişmiş bot hazır.")
    app.run_polling()

if __name__ == '__main__':
    main()
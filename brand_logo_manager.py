"""
ZBC 品牌Logo管理系统 v1.0
- 品牌logo数据存储（brand_logos.json）
- 自动通过品牌官网favicon获取logo
- 品牌域名映射（brand_en -> domain）
- API返回带logo的品牌数据
- 覆盖CTH和ZBMP品牌展示
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

LOGO_FILE = Path(__file__).parent / 'data' / 'brand_logos.json'

# 品牌域名映射（品牌英文名 -> 官方网站域名）
# 基于品牌官方网站，确保logo准确
BRAND_DOMAIN_MAP = {
    # 奢侈品
    'LOUIS VUITTON': 'louisvuitton.com',
    'DIOR': 'dior.com',
    'CHANEL': 'chanel.com',
    'GUCCI': 'gucci.com',
    'HERMÈS': 'hermes.com',
    'PRADA': 'prada.com',
    'BOTTEGA VENETA': 'bottegaveneta.com',
    'BALENCIAGA': 'balenciaga.com',
    'BURBERRY': 'burberry.com',
    'SAINT LAURENT': 'ysl.com',
    'CELINE': 'celine.com',
    'FENDI': 'fendi.com',
    'GIVENCHY': 'givenchy.com',
    'VALENTINO': 'valentino.com',
    'LOEWE': 'loewe.com',
    'CHLOÉ': 'chloe.com',
    'MIU MIU': 'miumiu.com',
    'MONCLER': 'moncler.com',
    'THOM BROWNE': 'thombrowne.com',
    'ALEXANDER MCQUEEN': 'alexandermcqueen.com',
    'ALEXANDERWANG': 'alexanderwang.com',
    'ACNE STUDIOS': 'acnestudios.com',
    'JIL SANDER': 'jilsander.com',
    'MAISON MARGIELA': 'maisonmargiela.com',
    'MARNI': 'marni.com',
    'LORO PIANA': 'loropiana.com',
    'MAXMARA': 'maxmara.com',
    'ZEGNA': 'zegna.com',
    'BERLUTI': 'berluti.com',
    'DUNHILL': 'dunhill.com',
    'FERRAGAMO': 'ferragamo.com',
    'TOM FORD': 'tomford.com',
    'VERSACE': 'versace.com',
    'ROGER VIVIER': 'rogervivier.com',
    'LONGCHAMP': 'longchamp.com',
    'RIMOWA': 'rimowa.com',
    'SONGMONT': 'songmont.com',
    # 珠宝钟表
    'CARTIER': 'cartier.cn',
    'TIFFANY & CO.': 'tiffany.cn',
    'BVLGARI': 'bulgari.com',
    'VAN CLEEF & ARPELS': 'vancleefarpels.com',
    'CHAUMET': 'chaumet.com',
    'CHOPARD': 'chopard.com',
    'PIAGET': 'piaget.com',
    'FRED': 'fred.com',
    'QEELIN': 'qeelin.com',
    'BUCCELLATI': 'buccellati.com',
    'POMELLATO': 'pomellato.com',
    'JEWELRIA': 'jewelia.com',
    'LAOPU GOLD': 'laopugold.com',
    'SING JEWEL BOUTIQUE': 'singjewelry.com',
    'CHOW SANG SANG': 'chowsangsang.com',
    'ROLEX': 'rolex.com',
    'OMEGA': 'omegawatches.com',
    'IWC': 'iwc.com',
    'JAEGER-LECOULTRE': 'jaeger-lecoultre.com',
    'VACHERON CONSTANTIN': 'vacheron-constantin.com',
    'BLANCPAIN': 'blancpain.com',
    'BREGUET': 'breguet.com',
    'LONGINES GZTKH CORPORATE STORE': 'longines.com',
    'MONTBLANC': 'montblanc.com',
    'GENTLE MONSTER': 'gentlemonster.com',
    'LENS CRAFTERS': 'lenscrafters.com.cn',
    'PUYI OPTICAL': 'puyi.com',
    # 美容护理
    'LA MER': 'lamer.com.cn',
    'LA PRAIRIE': 'laprairie.com',
    'GUERLAIN': 'guerlain.com',
    'DIOR BEAUTY': 'dior.com',
    'CHANEL LES SALONS PRIVES': 'chanel.com',
    'GIVENCHY BEAUTY': 'givenchy.com',
    'NARS': 'narscosmetics.com',
    'CLÉ DE PEAU BEAUTÉ': 'cledepeau-beaute.com',
    'HELENA RUBINSTEIN': 'helenarubinstein.com',
    'FRESH': 'fresh.com',
    'AESOP': 'aesop.com',
    'BYREDO': 'byredo.com',
    'DIptyque': 'diptyque.com',
    'JO MALONE LONDON': 'jomalone.com',
    'LE LABO': 'lelabofragrances.com',
    'CREED': 'creedboutique.com',
    'L\'ARTISAN PARFUMEUR': 'artisan-parfumeur.com',
    'LOEWE 罗意威香氛': 'loewe.com',
    'TOM FORD BEAUTY': 'tomford.com',
    'ACQUA DI PARMA': 'acquadiparma.com',
    'GALENIC': 'galenic.com',
    'EDITIONS DE PARFUMS FREDERIC MALLE、 KILIAN': 'fredericmalle.com',
    'L\'OCCITANE': 'loccitane.com',
    'SEPHORA': 'sephora.cn',
    'ELLE SALON BY KRAEMER PARIS': 'kraemerparis.com',
    'FIFTH (HAIR CODE GROUP) X SHISEIDO PROFESSIONAL': 'haircode.com',
    'L.J NAIL SALON': 'ljnailsalon.com',
    'THE FITNESS CENTRE': 'mandarinoriental.com',
    'THE SPA AT MANDARIN ORIENTAL, GUANGZHOU': 'mandarinoriental.com',
    # 餐饮
    'GAGA CENTRAL': 'gaga.com',
    'LIAN. VIET & THAI CUISINE': 'liancuisine.com',
    'GLANCE': 'glance.com',
    'DIN TAI FUNG': 'dintaifung.com',
    'PUTIEN': 'putien.com',
    'IMPERIAL TREASURE FINE TEOCHEW CUISINE': 'imperialtreasure.com',
    'JADE GARDEN': 'jadegarden.com',
    'JIANG BY CHEF FEI': 'jiangbychef.com',
    'KOYAMA ROBATAYAKI • SUSI': 'koyama.com',
    'KAPPO ENHO': 'kappoenho.com',
    'SUSHI HANZO PRO': 'sushihanzo.com',
    'MIKISI JAPANESE BISTRO': 'mikisi.com',
    'NEGIMA': 'negima.com',
    'CHOP-CHOP NOODLES': 'chopchopnoodles.com',
    'DAYBYDAY': 'daybyday.com',
    'GONTRAN CHERRIER': 'gontrancherrier.com',
    'GRID COFFEE': 'gridcoffee.com',
    'NESPRESSO': 'nespresso.com',
    'NINO MATCHA': 'ninomatcha.com',
    'KEE WAH BAKERY': 'keewah.com',
    'MVUKE TOKYO': 'mvuke.com',
    'LÄDERACH': 'laderach.com',
    'VENCHI': 'venchi.com',
    'ZAKUZAKU': 'zakuzaku.com',
    'MCDONALD\'S': 'mcdonalds.com',
    'TRUE SHAN': 'trueshan.com',
    'MANAGI': 'managi.com',
    'MUINE·DIAMOND': 'muine.com',
    'AH MA HAND MADE': 'ahmahandmade.com',
    'DIM BAR': 'dimbar.com',
    'FAMOUS CHEF FROM JIANGNAN CHINA': 'famouschef.com',
    'TANG': 'tang.com',
    'THE LOFT': 'theloft.com',
    '1730 MUSEE DU PAIN': '1730musee.com',
    'LIÁNG': 'liang.com',
    'SING JEWEL BOUTIQUE': 'singjewelry.com',
    'WASAI LIVING': 'wasailiving.com',
    '宋·SONG CAFÉ': 'songcafe.com',
    # 运动休闲
    'ADIDAS': 'adidas.com',
    'NIKE': 'nike.com',
    'LULULEMON': 'lululemon.com',
    'ARC\'TERYX': 'arcteryx.com',
    'DESCENTE': 'descente.com',
    'FILA': 'fila.com',
    'KOLON SPORT': 'kolonsport.com',
    'SALOMON': 'salomon.com',
    'THE NORTH FACE': 'thenorthface.com',
    'UNDERBOBO': 'underbobo.com',
    'A BATHING APE、I.T': 'bape.com',
    'CALVIN KLEIN JEANS': 'calvinklein.com',
    'EVISU': 'evisu.com',
    'FRED PERRY': 'fredperry.com',
    'I.T': 'ithk.com',
    'POLO RALPH LAUREN': 'ralphlauren.com',
    'TABIO': 'tabio.com',
    'KAILAS FUGA': 'kailas.com',
    'WASAI LIVING': 'wasailiving.com',
    # 女装
    'COS': 'cos.com',
    'MAJE': 'maje.com',
    'SANDRO': 'sandro.com',
    'SELF-PORTRAIT': 'self-portrait.com',
    'BA&SH': 'ba-sh.com',
    'EP YAYING': 'epyaying.com',
    'MARYLING': 'maryling.com',
    'MO&CO.': 'moco.com',
    'MO&CO. EDITION': 'moco.com',
    'ICICLE': 'icicle.com',
    'INITIAL': 'initialfashion.com',
    'IRO': 'iro.com',
    'AMERICAN VINTAGE': 'americanvintage.com',
    'GRVRGROVE': 'grvrgrove.com',
    'CURIEL': 'curiel.com',
    'TOMMY HILFIGER': 'tommy.com',
    'TORY BURCH': 'toryburch.com',
    'VIVIENNE WESTWOOD': 'viviennewestwood.com',
    'PLEATS PLEASE ISSEY MIYAKE & BAO BAO ISSEY MIYAKE': 'isseymiyake.com',
    'CALVIN KLEIN UNDERWEAR': 'calvinklein.com',
    'LITTLE MO&CO.': 'moco.com',
    'MOODYTIGER': 'moodytiger.com',
    'PETIT BATEAU': 'petitbateau.com',
    'MIKI HOUSE': 'mikihouse.com',
    'JNBY BY JNBY': 'jnby.com',
    'KENZO KIDS': 'kenzo.com',
    'BONPOINT': 'bonpoint.com',
    'POP MART': 'popmart.com',
    # 男装
    'GENTSPACE': 'gentspace.com',
    'CARLO ATELIER': 'carloatelier.com',
    'SIMPLE LIVING': 'simpleliving.com',
    'PYE': 'pye.com',
    'FENDI MAN': 'fendi.com',
    # 生活时尚
    'PROFACE . SWANK SALON': 'swanksalon.com',
    'SUPERMONKEY': 'supermonkey.com',
    'THE BEAST SHOP': 'thebeastshop.com',
    'MANITO': 'manitohome.com',
    'GREEN BAG HOTEL': 'greenbaghotel.com',
    # 影音电器
    'BANG & OLUFSEN': 'bang-olufsen.com',
    'DJI': 'dji.com',
    'HASSELBLAD': 'hasselblad.com',
    'SUNION': 'sunion.com',
    'SUNDAN': 'sundan.com',
    # 主力店
    'OLÉ SUPERMARKET': 'ole.com.cn',
    'VICTORIA\'S SECRET': 'victoriassecret.com',
    'SUNDAN': 'sundan.com',
    # MOH
    'ROLEX': 'rolex.com',
    'DIOR': 'dior.com',
    'JIANG BY CHEF FEI': 'jiangbychef.com',
    'LIÁNG': 'liang.com',
    'TANG': 'tang.com',
}


def _load_logos():
    """加载logo数据。"""
    if LOGO_FILE.exists():
        try:
            return json.loads(LOGO_FILE.read_text(encoding='utf-8'))
        except:
            pass
    return {'logos': {}, 'updated_at': None}


def _save_logos(data):
    """保存logo数据。"""
    os.makedirs(LOGO_FILE.parent, exist_ok=True)
    LOGO_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def get_logo_url(brand_en):
    """获取品牌logo URL（通过favicon服务）。"""
    domain = BRAND_DOMAIN_MAP.get(brand_en.upper(), '')
    if domain:
        # 使用Google favicon服务（稳定、高清）
        return f'https://www.google.com/s2/favicons?domain={domain}&sz=128'
    return ''


def get_brand_with_logo(brand):
    """给品牌数据添加logo字段。"""
    logo = get_logo_url(brand.get('brand_en', ''))
    brand['logo'] = logo
    brand['has_logo'] = bool(logo)
    return brand


def get_all_brands_with_logos():
    """获取所有品牌并添加logo。"""
    try:
        from app import _load_brands
        brands = _load_brands()
    except:
        brands = []
    return [get_brand_with_logo(b) for b in brands]


def get_logo_stats():
    """获取logo统计。"""
    brands = get_all_brands_with_logos()
    with_logo = sum(1 for b in brands if b.get('has_logo'))
    without_logo = sum(1 for b in brands if not b.get('has_logo'))
    return {
        'total': len(brands),
        'with_logo': with_logo,
        'without_logo': without_logo,
        'coverage': round(with_logo / len(brands) * 100, 1) if brands else 0
    }


def add_custom_logo(brand_en, logo_url):
    """添加自定义logo URL。"""
    data = _load_logos()
    data['logos'][brand_en.upper()] = logo_url
    data['updated_at'] = datetime.now().isoformat()
    _save_logos(data)
    return True

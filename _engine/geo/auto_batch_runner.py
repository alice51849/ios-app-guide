#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone GEO auto-batch runner — finds missing language codes and generates 90 pages.
Designed to run from LaunchAgent without Claude. Picks next 5 uncovered langs and generates."""
import json, os, subprocess, sys, logging, time
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).parent
PAGES = HERE / "pages"
LOG = HERE.parent / "agent" / "reports" / "geo_autobatch.log"
GEO_SITE = os.getenv("GEO_SITE", "https://alice51849.github.io/ios-app-guide")
PYTHON = sys.executable

logging.basicConfig(
    filename=str(LOG),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Master candidate pool — ISO 639-3 codes worth targeting, in priority order
# Skip any that already have geo/pages/<code>/best-for/*.html
CANDIDATE_POOL = [
    # Group A: Africa (high iOS growth)
    ("sot","Sesotho (South Africa/Lesotho)","ZAR 19","ZAR 55","dokumente","← Khoela ho App Guide","Laela ho App Store →","Lipotso","Hlahlobo:","✅ Hantle","⚠️ Ha ho hantle","Bakeng sa","Eseng bakeng sa","Litemane tsa developer."),
    ("ven","Tshivenḓa / Venda (South Africa)","ZAR 19","ZAR 55","nyambo","← Ḓzokela ha App Guide","Thothomela u bva App Store →","Mbudziso","Mbudziso:","✅ Zwavhudi","⚠️ Zwi vhe na ngoho","Ndi nnyi","Si nnyi","Nota ya developer."),
    ("tso","Xitsonga / Tsonga (South Africa/Mozambique)","ZAR 19","ZAR 55","swirheleto","← Vuya eka App Guide","Tlayitela eka App Store →","Swivutiso","Ku Hlayisa:","✅ Swa Lulama","⚠️ A Swi Lulami","Hi wa mani","A hi wa","Nota ya developer."),
    ("ssw","SiSwati / Swati (Eswatini/South Africa)","ZAR 19","ZAR 55","imibhalo","← Buyela ku App Guide","Layisha ku App Store →","Imibuzo","Ukuhlolwa:","✅ Kulungile","⚠️ Akukulungile","Ngubani","Akuwona","Inota ye developer."),
    ("loz","Silozi / Lozi (Zambia)","ZMW 50","ZMW 150","liñolo","← Kutela App Guide","Nolofaza kwa App Store →","Lipuzo","Sibonelo:","✅ Kuluka","⚠️ Ha ku luki","Ya mañi","Ha ku ya","Nothe ya developer."),
    # Group B: South/SE Asia
    ("bho","Bhojpuri (India/Nepal)","₹99","₹299","कागज","← App Guide पर वापस","App Store से डाउनलोड →","सवाल","समीक्षा:","✅ बढ़िया","⚠️ सही नाहीं","काहे खातिर","काहे नाहीं","Developer के नोट."),
    ("mag","Magahi (India)","₹99","₹299","कागज","← App Guide पर वापस","App Store से डाउनलोड →","सवाल","समीक्षा:","✅ अच्छा","⚠️ ठीक नहीं","किनके लिए","किनके लिए नहीं","Developer का नोट."),
    ("new","Newar / Nepal Bhasa (Nepal)","NPR 130","NPR 390","कागत","← App Guide यात खँगलाव","App Store थाय् डाउनलोड →","दु:बाय्","समीक्षा:","✅ ज्याझ्वः","⚠️ ज्याझ्वः मखु","थ्व का","थ्व कथं मखु","Developer नोट."),
    ("mai","Maithili (India/Nepal)","₹99","₹299","कागत","← App Guide पर वापस","App Store सँ Download →","प्रश्न","समीक्षा:","✅ नीक","⚠️ नीक नहिं","केकरा लेल","नहिं","Developer नोट."),
    ("raj","Rajasthani (India)","₹99","₹299","कागज","← App Guide पर वापस","App Store सूं डाउनलोड →","सवाल","समीक्षा:","✅ राम्रो","⚠️ सही नहीं","किसके लिए","सही नहीं","Developer नोट."),
    # Group C: Pacific
    ("mah","Kajin M̧ajeļ / Marshallese (Marshall Islands)","$1.99","$5.99","pepa","← Jerbal ñan App Guide","Download jen App Store →","Kajjitõ","Review:","✅ Enno","⚠️ Ejjelok","Ñan wōn","Ejjelok","Developer note."),
    ("tvl","Tuvaluan (Tuvalu)","$1.99","$5.99","pepa","← Hoki atu ki te App Guide","Taulia mai App Store →","Fehua","Iloiloga:","✅ Lelei","⚠️ E le lelei","Mo ai","E le mo","Developer faailoilo."),
    ("sm","Gagana Samoa / Samoan (Samoa)","$1.99","$5.99","pepa","← Toe foi i le App Guide","Sii i lalo i le App Store →","Fesili","Iloiloina:","✅ Lelei","⚠️ E le lelei","Mo ai","E le mo","Manatua a le developer."),
    # Group D: Americas
    ("nah","Nahuatl / Aztec (Mexico)","$29 MXN","$89 MXN","amatl","← Moztla App Guide","App Store icpac tequiti →","Tlaneltoquiliztli","Tlahtoa:","✅ Cuali","⚠️ Amo cuali","Aquinon","Amo","Tlahtoa developer."),
    ("que","Quechua (Peru/Bolivia)","$3 USD","$9 USD","qillqa","← App Guide-man kutiy","App Store-manta huqariy →","Tapukuykuna","Qhawariy:","✅ Allin","⚠️ Mana allin","Pim","Mana","Developer willaymi."),
    ("aym","Aymara (Bolivia/Chile/Peru)","$3 USD","$9 USD","qillqa","← App Guide-ruwa kutipañani","App Store-na uñxatatapxañani →","Aruskipt'a","Uñt'aña:","✅ Suma","⚠️ Janiw suma","Kamsaxa","Janiwa","Developer lup'iwi."),
    # Group E: Middle East / Central Asia
    ("ckb","Soranî Kurdish / Central Kurdish","$2 USD","$6 USD","belge","← Vegere App Guide","Ji App Store dakêşe →","Pirsyar","Nêrîn:","✅ Baş","⚠️ Ne baş","Ji bo kê","Na","Nîşey developer."),
    ("lrc","Luri Bakhtiari / Lurish (Iran)","تومان 50,000","تومان 150,000","سند","← بازگشت به App Guide","دانلود از App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نیست","برای چه کسی","مناسب نیست","یادداشت توسعه‌دهنده."),
    ("haz","Hazaragi (Afghanistan)","Af 70","Af 200","سند","← بازگشت به App Guide","دانلود از App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نیست","برای چه کسی","مناسب نیست","یادداشت توسعه‌دهنده."),
    # Group F: West Africa (high-potential uncovered)
    ("fuv","Fulfulde (Nigeria/Cameroon)","₦1,500","₦4,500","takarda","← Koma zuwa App Guide","Sauke daga App Store →","Tambayoyi","Nazari:","✅ Da kyau","⚠️ Ba daidai ba","Ga wa","Ba ga wa","Bayanin developer."),
    ("kmb","Kimbundu (Angola)","AOA 3,000","AOA 9,000","papelu","← Vueia App Guide","Descarrega App Store →","Mivango","Moneka:","✅ Malava","⚠️ Ka malava","Mu wê","Ka mu wê","Nota ya developer."),
    ("lua","Tshiluba / Luba-Kasai (DR Congo)","CDF 4,500","CDF 13,500","kalata","← Vwila App Guide","Bika App Store →","Mibuji","Mona:","✅ Bine","⚠️ Ku bine","Wa mwine","Ku wa","Mawazo ya developer."),
    ("mnk","Mandinka (Gambia/Senegal)","GMD 100","GMD 300","kabaru","← Sindira App Guide","Jang App Store →","Mansa","Tangito:","✅ Banta","⚠️ A banta fo","Ɲing ye mun ye","A kana ye","Developer kalamolu."),
    ("kby","Kabiyé (Togo)","XOF 1,200","XOF 3,600","pəlasɩ","← Kɔɔsɩ App Guide","Hɔ App Store →","Pʊʊzɩ","Yɔɔdʊʊ:","✅ Ɖeu","⚠️ Ɛfɛm yɔ","Yem","Ɛfɛm yɔ","Developer kɩtɩŋ."),
    ("ybb","Yemba / Nda'nda' (Cameroon)","XAF 1,200","XAF 3,600","mbʉ́","← Fʉ̂ App Guide","Fwâ App Store →","Mɛ̀","Tìa:","✅ Ŋkɛ́","⚠️ Mbʉ̀ yí","Tô mûa","Mbʉ̀","Developer ŋgàŋ."),
    ("dan","Dangme / Adangme (Ghana)","GHS 20","GHS 60","ngmɔ","← Return App Guide","Download App Store →","Questions","Review:","✅ Good","⚠️ Not ideal","For who","Not for","Developer notes."),
    ("bsc","Oniyan / Bassari (Senegal/Guinea-Bissau)","XOF 1,200","XOF 3,600","papier","← Retour App Guide","Télécharger App Store →","Questions","Avis:","✅ Bien","⚠️ Pas idéal","Pour qui","Pas pour","Note developer."),
    # Group G: South/SE Asia (uncovered)
    ("lus","Mizo / Lushai (Mizoram, India)","₹99","₹299","lehkhabu","← App Guide-ah zawn","App Store atangin download →","Câwi","Review:","✅ Ṭha","⚠️ Ṭha lo","Tûr pawh","Ṭha lo","Developer note."),
    ("hif","Fiji Hindi / Hindustani Fiji (Fiji)","FJD 4","FJD 12","kagaz","← App Guide par wapas","App Store se download →","Sawal","Review:","✅ Acha","⚠️ Sahi nahi","Kiske liye","Kiske nahi","Developer ki baat."),
    ("meu","Motu (Papua New Guinea)","PGK 5","PGK 15","pepa","← App Guide ena guruhuta","App Store amo hoia →","Henanadai","Review:","✅ Namo","⚠️ Namo lasi","Ediai","Lasi","Developer nota."),
    # Group H: Native Americas (uncovered)
    ("lkt","Lakota (USA/Canada)","$1.99","$5.99","wówapi","← App Guide ektá kihúŋni","App Store etáŋhaŋ yuháŋpi →","Wóiyakapi","Ihúŋni:","✅ Čhaŋtéčhiŋzapi","⚠️ Šíčaya","Tuwá","Hečhí šni","Developer othúŋwahe."),
    ("moh","Mohawk (Canada/USA)","$1.99","$5.99","ono'a","← App Guide neniaterí:iohst","App Store ohstá:rats →","Iokhé:rens","Nonkwe'shón:a:","✅ Sewakwenién:te","⚠️ Iakotahonhsatén:te","Né:","Tahotiatén:ron","Developer kehte."),
    ("cho","Choctaw (USA)","$1.99","$5.99","holisso","← App Guide pilla kia","App Store ia lachi →","Aioklanchi","Aiimpa:","✅ Achukma","⚠️ Aka achukma kia","Anumpa","Achukma kia","Developer anumpa."),
    # Group I: Oceania (uncovered)
    ("rop","Kriol (Australia Aboriginal)","A$2.99","A$8.99","peipa","← Go bek App Guide","Daunlod App Store →","Kweschins","Rivu:","✅ Gud","⚠️ Not gud","Fo hu","Not fo","Developer nots."),
    ("niu","Niuean (Niue/NZ)","NZD 3","NZD 9","pepa","← Foki ki App Guide","Hao mai App Store →","Fehu'i","Iloilo:","✅ Lelei","⚠️ Ko e aha","Kia ho hai","Ko e aha","Developer fakamatala."),
    # Group J: Central Africa (uncovered)
    ("ktu","Kituba / Munukutuba (Congo/DRC)","CDF 4,500","CDF 13,500","papier","← Tuba App Guide","Download App Store →","Mibuzi","Tala:","✅ Mbote","⚠️ Ko mbote","Nani","Ko nani","Developer makanisi."),
    ("guw","Gun-Gbe / Gungbe (Benin)","XOF 1,200","XOF 3,600","papie","← Vɔ bo App Guide","Ɖò App Store ɔ mɛ →","Nùkplɔnkplɔn","Mɔjɛhwɛ:","✅ Nyɔ́","⚠️ Wɛ nyɔ́ ǎ","Mɛnu","Wɛ nyɔ́ ǎ","Developer bɔtexówema."),
    # Group K: South Africa (uncovered variants)
    ("nde","isiNdebele North (Zimbabwe)","USD 2","USD 6","iphepha","← Buyela App Guide","Layisha App Store →","Imibuzo","Ukuhlolwa:","✅ Kulungile","⚠️ Akukulungile","Ngubani","Akuwona","Inota yedeveloper."),
    # Group L: Horn of Africa (uncovered)
    ("wal","Wolaytta (Ethiopia)","ETB 100","ETB 300","maxaafuwaa","← App Guide simbira","App Store appe →","Oosuwaappe","Xomoosuwaa:","✅ Lo'o","⚠️ Lo'o gidenna","Oona","Lo'o gidenna","Developer qofaa."),
    # Group M: Zambia/Southern Africa (uncovered)
    ("kck","Kalanga (Zimbabwe/Botswana)","USD 2","USD 6","gwalo","← Dzokela App Guide","Download App Store →","Mibvunzo","Kutarisa:","✅ Zvakanaka","⚠️ Hazvina","Ndiani","Kwete","Manwadzo a developer."),
    ("toi","Chitonga / Tonga (Zambia/Zimbabwe)","ZMW 50","ZMW 150","pepa","← Piluka ku App Guide","Kkopolola App Store →","Mibuzyo","Kulanga:","✅ Kabotu","⚠️ Tacikabotu","Nguni","Taakwe","Majwi aa developer."),
    ("lue","Luvale (Zambia/Angola)","ZMW 50","ZMW 150","mukanda","← Kinduluka App Guide","Sokola App Store →","Vihula","Kutala:","✅ Chamwaza","⚠️ Kachamwazaku","Kuli iya","Kakweshi","Mazu a developer."),
    ("nya","Chinyanja / Nyanja (Zambia/Malawi)","ZMW 50","ZMW 150","pepala","← Bwelera App Guide","Tsitsani App Store →","Mafunso","Kuwunika:","✅ Bwino","⚠️ Sibwino","Ndani","Palibe","Mawu a developer."),
    # Group N: Cameroon Grassfields (uncovered)
    ("bax","Shüpamem / Bamun (Cameroon)","XAF 1,200","XAF 3,600","kaɽit","← Fu App Guide","Lwot App Store →","Nʃiɛt","Yɛn:","✅ Nʃwe","⚠️ Ka nʃwe","Fɔ wu","Ka","Developer nʃiɛt."),
    ("bbj","Ghomálá' (Cameroon)","XAF 1,200","XAF 3,600","ŋwɛ́","← Bɛ́ App Guide","Tswâ App Store →","Nɛ́","Tsʉ̌:","✅ Pʉ́ə","⚠️ Ka pʉ́ə","Á wɛ́","Ka","Developer nɛ́."),
    ("bfd","Bafut (Cameroon)","XAF 1,200","XAF 3,600","ŋwàʔà","← Fù App Guide","Lò App Store →","Àbèŋ","Sàʔà:","✅ Bó","⚠️ Kàʔà bó","Ǹdì wè","Kàʔà","Developer àbèŋ."),
    # Group O: West Africa (uncovered)
    ("sef","Cebaara Senoufo (Côte d'Ivoire)","XOF 1,200","XOF 3,600","sɛbɛ","← Kaari App Guide","Télécharger App Store →","Yeliyɔ","Cɛgɛlɛ:","✅ Nyɔ","⚠️ Nyɔ ba","Kile wi","Ba","Note developer."),
    ("gej","Gen / Mina (Togo/Benin)","XOF 1,200","XOF 3,600","wema","← Trɔ App Guide","Download App Store →","Nyabiabia","Kpɔkplɔ:","✅ Nyuie","⚠️ Menyo o","Na ame ka","Meli o","Developer ƒe nya."),
    ("vai","Vai (Liberia/Sierra Leone)","$1.50 USD","$4.50 USD","ꕉꕮꕪ","← Return App Guide","Download App Store →","Questions","Review:","✅ Good","⚠️ Not ideal","For who","Not for","Developer notes."),
    # Group P: Iran/Central Asia (uncovered)
    ("bqi","Bakhtiari (Iran)","تومان 50,000","تومان 150,000","سند","← بازگشت App Guide","دانلود App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نیست","برای کی","نه","یادداشت توسعه‌دهنده."),
    ("glk","Gilaki (Iran)","تومان 50,000","تومان 150,000","سند","← بازگشت App Guide","دانلود App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نیه","به‌ی کی","نه","یادداشت توسعه‌دهنده."),
    ("mzn","Mazandarani (Iran)","تومان 50,000","تومان 150,000","سند","← بازگشت App Guide","دانلود App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نی‌یه","وسه کی","نه","یادداشت توسعه‌دهنده."),
    # Group Q: Central Africa + Nile (uncovered)
    ("cjk","Chokwe (Angola/DR Congo)","AOA 3,000","AOA 9,000","mukanda","← Kinduluka App Guide","Descarrega App Store →","Yihula","Kutala:","✅ Chubaho","⚠️ Kachubahoku","Kuli iya","Kakweshi","Mazu a developer."),
    ("anu","Anuak (South Sudan/Ethiopia)","SSP 1,500","SSP 4,500","waraga","← Dwog App Guide","Lɔ App Store →","Apenya","Neno:","✅ Aber","⚠️ Pe ber","Ni ŋa","Onge","Wach developer."),
    ("shk","Shilluk / Dhøg Cøllø (South Sudan)","SSP 1,500","SSP 4,500","waraga","← Duoki App Guide","Lɔ App Store →","Apiny","Neno:","✅ Aber","⚠️ Pe ber","Ni ŋa","Onge","Wach developer."),
    ("kdh","Tem / Kotokoli (Togo)","XOF 1,200","XOF 3,600","takade","← Kɛlɛ App Guide","Télécharger App Store →","Puuzo","Yɔɔdʊ:","✅ Ɖeu","⚠️ Fɛyɛ","Kaŋ","Fɛyɛ","Note developer."),
    ("kus","Kusaal (Ghana)","GHS 20","GHS 60","gbãun","← Lebis App Guide","Download App Store →","Bɔbɔsem","Gees:","✅ Sumn","⚠️ Ka sumn","Ne anɔ'ɔne","Kaee","Developer gbãun."),
    ("mfq","Moba (Togo/Ghana)","XOF 1,200","XOF 3,600","takada","← Guani App Guide","Télécharger App Store →","Buali","Diid:","✅ Ŋani","⚠️ Baa ŋani","Yua","Baa","Note developer."),
    ("luc","Aringa / Low Lugbara (Uganda)","UGX 7,000","UGX 21,000","waraga","← Agó App Guide","Download App Store →","Apotani","Ndrele:","✅ Onyiru","⚠️ Ku onyiru","A'disi","Yo","Developer eyo."),
    ("bud","Ntcham / Bassari (Togo/Ghana)","XOF 1,200","XOF 3,600","takart","← Kpeni App Guide","Télécharger App Store →","Libaali","Cient:","✅ Ŋmɛn","⚠️ Baa ŋmɛn","U yaa","Baa","Note developer."),
    # Group R: West Africa 2 (uncovered, overnight refill)
    ("yre","Yaouré (Côte d'Ivoire)","XOF 1,200","XOF 3,600","papie","← Yʌ App Guide","Télécharger App Store →","Yereyɛ","Fɔlɛ:","✅ Kpa","⚠️ Ba kpa","Yi ye","Ba","Note developer."),
    ("bss","Akoose / Bakossi (Cameroon)","XAF 1,200","XAF 3,600","kaat","← Pɛn App Guide","Télécharger App Store →","Mbeghe","Ehɔɔ:","✅ Nlàm","⚠️ Bé nlàm","Á zě","Bé","Developer eghɔ."),
    ("bfo","Birifor (Burkina Faso/Ghana)","XOF 1,200","XOF 3,600","sɛbɛ","← Lɛbɛ App Guide","Télécharger App Store →","Bɔɔra","Naɲʋ:","✅ Vɛlɛ","⚠️ Ba vɛlɛ","An yele","Ba","Note developer."),
    ("dop","Lukpa / Dompago (Togo/Benin)","XOF 1,200","XOF 3,600","takatɩ","← Kɛlɩ App Guide","Télécharger App Store →","Pɔɔsɩ","Naʋ:","✅ Ɖɛu","⚠️ Fɛ ɖɛu","Yee","Fɛ","Note developer."),
    ("xon","Konkomba (Ghana/Togo)","GHS 20","GHS 60","takadɛ","← Lɛbɛ App Guide","Download App Store →","Ibaali","Naa:","✅ Ŋoo","⚠️ Baa ŋoo","U ŋaa","Baa","Developer ŋmaŋ."),
    ("ncu","Chumburung (Ghana)","GHS 20","GHS 60","takradaa","← Sanɛ App Guide","Download App Store →","Abisa","Kwɛɛ:","✅ Yɛ","⚠️ Nyɛ yɛ","Maa","Nyɛ","Developer nsɛm."),
    ("gng","Ngangam (Togo/Benin)","XOF 1,200","XOF 3,600","takatiri","← Kpeni App Guide","Télécharger App Store →","Libaari","Cieni:","✅ Ŋanma","⚠️ Baa ŋanma","U yaa","Baa","Note developer."),
    ("bqc","Boko (Benin/Nigeria)","XOF 1,200","XOF 3,600","takada","← Duo App Guide","Télécharger App Store →","Yesↄ","Gwã:","✅ Kↄ̃́","⚠️ Àsↄ̃kↄ̃","Aↄ̃ ye","Àsↄ̃","Note developer."),
    # Group S: Cameroon + Central Africa 2 (overnight refill)
    ("mcp","Maka / Makaa (Cameroon)","XAF 1,200","XAF 3,600","kalat","← Bulə App Guide","Télécharger App Store →","Minsɔl","Fɛn:","✅ Mbɔŋ","⚠️ Kə mbɔŋ","Yə za","Kə","Nte developer."),
    ("tik","Tikar (Cameroon)","XAF 1,200","XAF 3,600","kalati","← Bwe App Guide","Télécharger App Store →","Njues","Yen:","✅ Nkane","⚠️ Ka nkane","Fo we","Ka","Developer njues."),
    ("koq","Kota (Gabon)","XAF 1,200","XAF 3,600","mukanda","← Vutuka App Guide","Télécharger App Store →","Mambu","Tala:","✅ Mbɔtɛ","⚠️ Ka mbɔtɛ","Na nyɛ","Ka","Mambu ma developer."),
    ("bex","Jur Modo (South Sudan)","SSP 1,500","SSP 4,500","waraga","← Guru App Guide","App Store lo →","Apiny","Neno:","✅ Aber","⚠️ Pe ber","Ni ŋa","Onge","Wach developer."),
    ("avu","Avokaya (South Sudan/DR Congo)","SSP 1,500","SSP 4,500","waraga","← Agó App Guide","App Store lo →","Apotani","Ndrele:","✅ Onyiru","⚠️ Ku onyiru","A'disi","Yo","Developer eyo."),
    ("las","Lama (Togo)","XOF 1,200","XOF 3,600","takada","← Kɛlɩ App Guide","Télécharger App Store →","Puuzo","Yɔɔdʊ:","✅ Ɖeu","⚠️ Fɛyɛ","Kaŋ","Fɛyɛ","Note developer."),
    ("ntr","Delo / Ntrubo (Ghana/Togo)","GHS 20","GHS 60","takada","← Sanɛ App Guide","Download App Store →","Ibaali","Naa:","✅ Ŋoo","⚠️ Baa ŋoo","U ŋaa","Baa","Developer nsɛm."),
    ("gud","Yocoboué Dida (Côte d'Ivoire)","XOF 1,200","XOF 3,600","fluwa","← Sa App Guide","Télécharger App Store →","Kosan","Nian:","✅ Kpa","⚠️ Nyɛ kpa","Wan ti","Nyɛ","Note developer."),
    ("bwu","Buli (Ghana)","GHS 20","GHS 60","gbaŋ","← Le App Guide","Download App Store →","Bɔbɔsika","Gɛɛsi:","✅ Nalɔŋ","⚠️ Ka nalɔŋ","Ne wana","Kaai","Developer gbaŋ."),
    ("nmz","Nawdm (Togo/Ghana)","XOF 1,200","XOF 3,600","takada","← Guani App Guide","Télécharger App Store →","Buali","Diid:","✅ Ŋani","⚠️ Baa ŋani","Yua","Baa","Note developer."),
    # Group T: Sahel + Great Lakes (overnight refill)
    ("dgo","Dogon / Toro So (Mali)","XOF 1,200","XOF 3,600","takarda","← Yɛrɛ App Guide","Télécharger App Store →","Sɛgɛ","Kɛrɛ:","✅ Ɛsu","⚠️ Ɛsu la","Ana","La","Note developer."),
    ("kao","Xaasongaxango / Khassonke (Mali)","XOF 1,200","XOF 3,600","sɛbɛ","← Segi App Guide","Télécharger App Store →","Ɲininkali","Kɔrɔsili:","✅ Ɲɛ","⚠️ Man ɲɛ","Jɔn ye","Foyi","Note developer."),
    ("myk","Sénoufo Mamara (Mali)","XOF 1,200","XOF 3,600","sɛbɛ","← Kaari App Guide","Télécharger App Store →","Yeliyɔ","Cɛgɛlɛ:","✅ Nyɔ","⚠️ Nyɔ ba","Kile wi","Ba","Note developer."),
    ("bze","Jenaama Bozo (Mali)","XOF 1,200","XOF 3,600","sɛbɛ","← Segi App Guide","Télécharger App Store →","Ɲininka","Kɔrɔ:","✅ Ɲuma","⚠️ Ɲuma si","Jɔ ma","Si","Note developer."),
    ("snk","Soninké (Mali/Senegal)","XOF 1,200","XOF 3,600","kayiti","← Xa App Guide","Télécharger App Store →","Maxankiɲɲu","Xaralle:","✅ Burucu","⚠️ Nta burucu","Ke danŋe","Nta","Note developer."),
    ("kbn","Kare (Central African Rep.)","XAF 1,200","XAF 3,600","mbeti","← Kiri App Guide","Télécharger App Store →","Hunda","Bɛ:","✅ Nzoni","⚠️ Nzoni pɛpɛ","Teti zo","Pɛpɛ","Note developer."),
    ("sg2","Gbanu (Central African Rep.)","XAF 1,200","XAF 3,600","mbeti","← Kiri App Guide","Télécharger App Store →","Hundango","Bango:","✅ Nzoni","⚠️ Aeke nzoni pɛpɛ","Teti azo","Pɛpɛ","Note developer."),
    ("nup","Nupe (Nigeria)","₦1,500","₦4,500","takada","← Labo App Guide","Download App Store →","Egwa","Etsu:","✅ Èdo","⚠️ À è do","Ci nya","À","Developer egwa."),
    ("gbr","Gbagyi (Nigeria)","₦1,500","₦4,500","takarda","← Sh App Guide","Download App Store →","Abamnyi","Duba:","✅ Yebwe","⚠️ Ba yebwe","Nyi ana","Ba","Developer abamnyi."),
    ("bqv","Koro Wachi (Nigeria)","₦1,500","₦4,500","takada","← Kasa App Guide","Download App Store →","Abisa","Duba:","✅ Nayi","⚠️ Ba nayi","Nyi wa","Ba","Developer abisa."),
    # Group U: Nigeria + Chad (overnight refill)
    ("bin","Ẹdo / Bini (Nigeria)","₦1,500","₦4,500","ebe","← Werrie App Guide","Download App Store →","Inọta","Danmwehọ:","✅ Ẹsẹ","⚠️ Ị ma ẹsẹ","Ne gha","I rrọọ","Developer ẹmwẹn."),
    ("etu","Ejagham (Nigeria/Cameroon)","₦1,500","₦4,500"," akwukwo","← Kem App Guide","Download App Store →","Abheng","Bibe:","✅ Ọbhi","⚠️ Ka ọbhi","Fo bo","Ka","Developer njiki."),
    ("mfi","Wandala / Mandara (Cameroon/Nigeria)","XAF 1,200","XAF 3,600","daftar","← Da App Guide","Télécharger App Store →","Cikankan","Dzaya:","✅ Ghela","⚠️ Ba ghela","Na wa","Ba","Note developer."),
    ("mcn","Masana / Massa (Chad/Cameroon)","XAF 1,200","XAF 3,600","takarda","← Vun App Guide","Télécharger App Store →","Halla","Wiya:","✅ Vwot","⚠️ Ba vwot","Na wu","Ba","Note developer."),
    ("gid","Gidar (Chad/Cameroon)","XAF 1,200","XAF 3,600","takarda","← Kel App Guide","Télécharger App Store →","Sokge","Wiye:","✅ Kwa","⚠️ Ba kwa","Na wi","Ba","Note developer."),
    ("kbp2","Bwamu (Burkina Faso)","XOF 1,200","XOF 3,600","sɛbɛ","← Lɛbɛ App Guide","Télécharger App Store →","Bɔɔra","Naɲʋ:","✅ Vɛlɛ","⚠️ Ba vɛlɛ","An yele","Ba","Note developer."),
    ("bwq","Southern Bobo (Burkina Faso)","XOF 1,200","XOF 3,600","sɛbɛ","← Segi App Guide","Télécharger App Store →","Ɲininka","Kɔrɔ:","✅ Ɲuma","⚠️ Ɲuma si","Jɔ ma","Si","Note developer."),
    ("dga2","Dagaare (Ghana/Burkina Faso)","GHS 20","GHS 60","takarda","← Le App Guide","Download App Store →","Bɔbie","Gaa:","✅ Vɛla","⚠️ Ba vɛla","Ne wana","Ba","Developer yele."),
    # Group V: East Africa + Sudan (overnight refill)
    ("mfz","Mari (South Sudan)","SSP 1,500","SSP 4,500","waraga","← Duni App Guide","App Store lo →","Apiny","Neno:","✅ Aber","⚠️ Pe ber","Ni ŋa","Onge","Wach developer."),
    ("bfa2","Bari-Kuku (South Sudan)","SSP 1,500","SSP 4,500","warǒga","← Dugu App Guide","App Store lo →","Kwesükaki","Ŋinituni:","✅ Lomereŋ","⚠️ Adi lomereŋ","Do ŋa","Adi","Kaŋen lo developer."),
    ("bjt","Balanta-Ganja (Senegal/Guinea-Bissau)","XOF 1,200","XOF 3,600","papel","← Fangama App Guide","Télécharger App Store →","Ndëf","Kila:","✅ Añaŋ","⚠️ Bë añaŋ","Bë an","Bë","Note developer."),
    ("bsc2","Bassari (Senegal/Guinea)","XOF 1,200","XOF 3,600","papier","← Retour App Guide","Télécharger App Store →","Questions","Avis:","✅ Bien","⚠️ Pas idéal","Pour qui","Pas pour","Note developer."),
    ("csk","Jola-Kasa (Senegal)","XOF 1,200","XOF 3,600","kayit","← Ñibaj App Guide","Télécharger App Store →","Kajukendo","Kajuk:","✅ Bug-am","⚠️ Funak","An di","Fu","Note developer."),
    ("kdc2","Kutu (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Wuya App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Swamu","⚠️ Si swamu","Kwa yani","Nakuli","Amagambo ga developer."),
    ("vid","Vidunda (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Uya App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Yinza","⚠️ Silita","Kwa yuwani","Kunyalwe","Amazu ga developer."),
    ("zga","Kinga (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Sooka App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Kinunu","⚠️ Sikinunu","Kwa yani","Kutalimo","Amasyu gha developer."),
    ("suk","Sukuma (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Wuya App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Chiza","⚠️ Chibiza","Kuli nani","Kutalimo","Amaghambo a developer."),
    ("nim","Nilamba (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Sooka App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Kiseku","⚠️ Sikiseku","Kwa munu","Nakuli","Amaghambo a developer."),
    ("rag2","Logoli-Idakho (Kenya)","KSh 250","KSh 750","karatasi","← Galuka App Guide","Pakua App Store →","Amavoosio","Kulola:","✅ Yavulahi","⚠️ Sivulahi","Kwa yiuna","Kwavaho","Amagambo ga developer."),
    ("kln","Kalenjin (Kenya)","KSh 250","KSh 750","karatasit","← Weech App Guide","Pakua App Store →","Tebutik","Ng'alek:","✅ Misi","⚠️ Ma misi","Ne ano","Ma mi","Logoiwek che developer."),
    # Group W: Chad/CAR + East Africa 3 (overnight refill)
    ("sba","Ngambay (Chad)","XAF 1,200","XAF 3,600","maktub","← Tel App Guide","Télécharger App Store →","Dɔ́ɔ","Oo:","✅ Maji","⚠️ Maji el","Kɔ́g ɗi","El","Note developer."),
    ("tui","Tupuri (Chad/Cameroon)","XAF 1,200","XAF 3,600","takarda","← Wale App Guide","Télécharger App Store →","Halla","Wga:","✅ Ndaŋ","⚠️ Ba ndaŋ","Na wa","Ba","Note developer."),
    ("daa","Dangaléat (Chad)","XAF 1,200","XAF 3,600","takarda","← Gel App Guide","Télécharger App Store →","Bura","Wiya:","✅ Yiwa","⚠️ Ba yiwa","Na wi","Ba","Note developer."),
    ("ngb","Northern Ngbandi (Central African Rep./DRC)","XAF 1,200","XAF 3,600","mbeti","← Kiri App Guide","Télécharger App Store →","Hunda","Bɛ:","✅ Nzoni","⚠️ Nzoni pɛpɛ","Teti zo","Pɛpɛ","Note developer."),
    ("ttj","Rutooro / Tooro (Uganda)","UGX 7,000","UGX 21,000","empapura","← Garuka App Guide","Download App Store →","Ebibuuzo","Okurora:","✅ Kirungi","⚠️ Tikirungi","Owa","Tiharoho","Ebigambo bya developer."),
    ("gwr","Lugwere / Gwere (Uganda)","UGX 7,000","UGX 21,000","empapula","← Kalabana App Guide","Download App Store →","Ebibuuzo","Okulola:","✅ Kirungi","⚠️ Tikirungi"," Owa","Tiwaliwo","Ebigambo bya developer."),
    ("pko","Pökoot (Kenya/Uganda)","KSh 250","KSh 750","karatait","← Weech App Guide","Pakua App Store →","Tebutik","Ng'alek:","✅ Karam","⚠️ Ma karam","Ne ano","Ma mi","Logoiwek che developer."),
    ("saf","Safaliba (Ghana)","GHS 20","GHS 60","takarda","← Le App Guide","Download App Store →","Bɔbie","Gaa:","✅ Vɛla","⚠️ Ba vɛla","Ne wana","Ba","Developer yele."),
    ("mzw","Deg / Mo (Ghana/Côte d'Ivoire)","GHS 20","GHS 60","takarda","← Sanɛ App Guide","Download App Store →","Ibaali","Naa:","✅ Ŋoo","⚠️ Baa ŋoo","U ŋaa","Baa","Developer nsɛm."),
    ("hag","Hanga (Ghana)","GHS 20","GHS 60","takarda","← Le App Guide","Download App Store →","Bɔbie","Gaa:","✅ Vɛla","⚠️ Ba vɛla","Ne wana","Ba","Developer yele."),
    # Group X: Guinea/Liberia big languages (overnight refill)
    ("fuf","Pular / Fula (Guinea)","GNF 15,000","GNF 45,000","kaayit","← Rutto App Guide","Aawtu App Store →","Naamnde","Ƴeewndagol:","✅ Moƴƴi","⚠️ Moƴƴaani","Homɓe","Alaa","Bataake developer."),
    ("xpe","Kpɛlɛ / Kpelle (Liberia)","$1.50 USD","$4.50 USD","kɔlɔ","← Return App Guide","Download App Store →","Marâ-woo","Kɔ̀wa:","✅ Nɛ̃ɛ","⚠️ Fé nɛ̃ɛ","Bâ mɛni","Fé","Developer woo."),
    ("gkp","Kpɛlɛwoo / Guinea Kpelle (Guinea)","GNF 15,000","GNF 45,000","kɔlɔ","← Rutto App Guide","Aawtu App Store →","Marâ-woo","Kɔ̀wa:","✅ Nɛ̃ɛ","⚠️ Fé nɛ̃ɛ","Bâ mɛni","Fé","Developer woo."),
    ("kqs","Kisiei / Northern Kissi (Guinea/Sierra Leone)","GNF 15,000","GNF 45,000","kaŋ","← Rutto App Guide","Download App Store →","Cɔɔŋ","Toolaŋ:","✅ Kɛndɔ","⚠️ Lɛ kɛndɔ","Bɛ le","Lɛ","Developer diom."),
    ("bza","Bandi (Liberia)","$1.50 USD","$4.50 USD","kɔlɔ","← Return App Guide","Download App Store →","Marâwoo","Kɔwa:","✅ Nɛ","⚠️ Fé nɛ","Bâ mɛni","Fé","Developer woo."),
    ("snf","Noon (Senegal)","XOF 1,200","XOF 3,600","kayit","← Ñibaj App Guide","Télécharger App Store →","Ɓoŋ","Semtu:","✅ Hay","⚠️ Ɓaa hay","Ɓoƴ an","Ɓaa","Note developer."),
    ("mcu","Mambila (Cameroon/Nigeria)","XAF 1,200","XAF 3,600","kalat","← Bwe App Guide","Télécharger App Store →","Njues","Yen:","✅ Nkane","⚠️ Ka nkane","Fo we","Ka","Developer njues."),
    ("nnq","Ngindo (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Wuya App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Swamu","⚠️ Si swamu","Kwa yani","Nakuli","Amagambo ga developer."),
    ("tnr","Ménik / Bedik (Senegal)","XOF 1,200","XOF 3,600","papier","← Retour App Guide","Télécharger App Store →","Questions","Avis:","✅ Bien","⚠️ Pas idéal","Pour qui","Pas pour","Note developer."),
    ("mfk","North Mofu (Cameroon)","XAF 1,200","XAF 3,600","takarda","← Da App Guide","Télécharger App Store →","Cikankan","Dzaya:","✅ Ghela","⚠️ Ba ghela","Na wa","Ba","Note developer."),
    # Group Y: Nigeria/Liberia/Côte d'Ivoire big + Mali (overnight refill)
    ("knc","Kanuri (Nigeria/Niger/Chad)","₦1,500","₦4,500","takarda","← Awiye App Guide","Download App Store →","Layenma","Cirbu:","✅ Ngəla","⚠️ Ngəlabe","Ndu-ye","Bago","Developer wultəma."),
    ("dnj","Dan / Yacouba (Côte d'Ivoire)","XOF 1,200","XOF 3,600","sɛbɛ","← Bhɔ App Guide","Télécharger App Store →","Yɛlɛ","Gɔ:","✅ Sëë","⚠️ Kë sëë","Mɛ ɓha","Kë","Note developer."),
    ("lom","Löömà / Loma (Liberia/Guinea)","$1.50 USD","$4.50 USD","kɔlɔ","← Return App Guide","Download App Store →","Marâwoo","Kɔwa:","✅ Nɛ","⚠️ Fé nɛ","Bâ mɛni","Fé","Developer woo."),
    ("gbo","Grebo (Liberia)","$1.50 USD","$4.50 USD","kolo","← Return App Guide","Download App Store →","Manyu","Kaa:","✅ Nyene","⚠️ Se nyene","Ke mu","Se","Developer wuduo."),
    ("grj","Southern Grebo (Liberia)","$1.50 USD","$4.50 USD","kolo","← Return App Guide","Download App Store →","Manyu","Kaa:","✅ Nyene","⚠️ Se nyene","Ke mu","Se","Developer wuduo."),
    ("dee","Dewoin (Liberia)","$1.50 USD","$4.50 USD","kolo","← Return App Guide","Download App Store →","Manyu","Kaa:","✅ Nyene","⚠️ Se nyene","Ke mu","Se","Developer wuduo."),
    ("wob","Wè Northern (Côte d'Ivoire)","XOF 1,200","XOF 3,600","fluwa","← Sa App Guide","Télécharger App Store →","Kosan","Nian:","✅ Kpa","⚠️ Nyɛ kpa","Wan ti","Nyɛ","Note developer."),
    ("bmq","Bomu (Mali/Burkina Faso)","XOF 1,200","XOF 3,600","sɛbɛ","← Segi App Guide","Télécharger App Store →","Ɲininka","Kɔrɔ:","✅ Ɲuma","⚠️ Ɲuma si","Jɔ ma","Si","Note developer."),
    ("box","Buamu (Burkina Faso)","XOF 1,200","XOF 3,600","sɛbɛ","← Segi App Guide","Télécharger App Store →","Ɲininka","Kɔrɔ:","✅ Ɲuma","⚠️ Ɲuma si","Jɔ ma","Si","Note developer."),
    ("kel","Kela (DR Congo)","CDF 4,500","CDF 13,500","mukanda","← Vutuka App Guide","Download App Store →","Mibuzi","Tala:","✅ Mbote","⚠️ Ka mbote","Nani","Ka","Mambu ma developer."),
    # Group Z: South/SE Asia (region shift — NE India, Nepal, Bhutan, Myanmar)
    ("grt","A·chik / Garo (India/Bangladesh)","₹99","₹299","kagat","← App Guide-o re·ang","App Store-oni download →","Sing·anirang","Nikangarang:","✅ Namgija","⚠️ Namgija ong·ja","Sako gita","Ong·ja","Developer-ni agana."),
    ("nag","Nagamese (Nagaland, India)","₹99","₹299","kagoj","← App Guide loi jabo","App Store pora download →","Puchibole","Sabole:","✅ Bhal","⚠️ Bhal nohoi","Kunba karone","Nai","Developer laga kotha."),
    ("njo","Ao / Ao Naga (Nagaland, India)","₹99","₹299","sü","← App Guide-ang sa","App Store-nüng download →","Ozünger","Nüngjaker:","✅ Asa","⚠️ Asa ma","Nung tema","Ma","Developer-ni ozü."),
    ("wbm","Vo / Wa (Myanmar)","K 3,000","K 9,000","liktui","← Kir App Guide","App Store download →","Yaom","Yao:","✅ Om","⚠️ Om vi","Rah mai","Vi","Developer lai."),
    ("tdg","Tamang (Nepal)","NPR 130","NPR 390","kagat","← App Guide phepdo","App Store gyang download →","Themba","Kesang:","✅ Ramro","⚠️ Ramro ahai","Su gyang","Ahai","Developer gyi tam."),
    ("tsj","Tshangla / Sharchop (Bhutan)","Nu 130","Nu 390","yigu","← App Guide log","App Store gay download →","Diwa","Ta:","✅ Lengpu","⚠️ Ma lengpu","Chi gay","Mila","Developer gi kha."),
    ("lep","Lepcha (Sikkim, India)","₹99","₹299","ho·look","← App Guide-sa nun","App Store-nun download →","Sung·da","Nyi·da:","✅ Nyám","⚠️ Ma nyám","A·hu tá","Ma","Developer-sa lung."),
    ("sip","Sikkimese / Bhutia (Sikkim, India)","₹99","₹299","yige","← App Guide log","App Store né download →","Diwa","Ta:","✅ Yakpo","⚠️ Ma yakpo","Su gi","Mindu","Developer ki kae."),
    ("jya","rGyalrong / Jarong (Sichuan, China)","¥18","¥54","yiktho","← App Guide wa","App Store né download →","Sanewa","Neta:","✅ Aprem","⚠️ Ma aprem","Chi ki","Mizang","Developer ki kscar."),
    ("mtr","Mewari (Rajasthan, India)","₹99","₹299","kagad","← App Guide su wapas","App Store su download →","Sawal","Samiksha:","✅ Ghano chango","⚠️ Chango koni","Kiyaan saru","Koni","Developer ri baat."),
    # Group AA: Big Indian regional (Rajasthan/MP/Bihar — millions of speakers)
    ("wbr","वागड़ी / Wagdi (Rajasthan, India)","₹99","₹299","kagad","← App Guide pachha","App Store thi download →","Sawal","Samiksha:","✅ Saru","⚠️ Saru koni","Kina saru","Koni","Developer ri baat."),
    ("hoj","हाड़ौती / Hadothi (Rajasthan, India)","₹99","₹299","kagad","← App Guide pachho","App Store su download →","Sawal","Samiksha:","✅ Chango","⚠️ Chango koni","Kina khatar","Koni","Developer ri baat."),
    ("noe","निमाड़ी / Nimadi (Madhya Pradesh, India)","₹99","₹299","kagaj","← App Guide pachhu","App Store su download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Badhiya na","Kina karta","Na","Developer ki baat."),
    ("dhd","ढूंढाड़ी / Dhundari (Rajasthan, India)","₹99","₹299","kagad","← App Guide pachho","App Store su download →","Sawal","Samiksha:","✅ Chango","⚠️ Chango koni","Kina saru","Koni","Developer ri baat."),
    ("bra","ब्रज भाषा / Braj (Uttar Pradesh, India)","₹99","₹299","kagaj","← App Guide pai wapas","App Store tey download →","Sawal","Samiksha:","✅ Neko","⚠️ Neko naahi","Kaake liye","Naahi","Developer ki baat."),
    ("gju","गुज्जरी / Gujari (India/Pakistan)","₹99","₹299","kagat","← App Guide waapas","App Store toon download →","Sawal","Samiksha:","✅ Changa","⚠️ Changa nahi","Kis waaste","Nahi","Developer di gal."),
    ("anp","अंगिका / Angika (Bihar, India)","₹99","₹299","kagaj","← App Guide dobara","App Store se download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Badhiya nai","Kekra khatir","Nai","Developer ke baat."),
    ("kjo","कच्छी कोली / Kachi Koli (India)","₹99","₹299","kagad","← App Guide pacho","App Store thi download →","Sawal","Samiksha:","✅ Saro","⚠️ Saro nahi","Keni khatar","Nahi","Developer ni vaat."),
    ("gdx","गोडवाड़ी / Godwari (Rajasthan, India)","₹99","₹299","kagad","← App Guide pacho","App Store su download →","Sawal","Samiksha:","✅ Saro","⚠️ Saro koni","Kina saru","Koni","Developer ri baat."),
    ("kvx","पारकरी कोली / Parkari Koli (Pakistan)","PKR 300","PKR 900","kagat","← App Guide wapas","App Store maan download →","Sawal","Jaayzo:","✅ Saro","⚠️ Saro nahi","Keni khaatar","Nahi","Developer ji gaalh."),
    # Group AB: Big Indian regional 2 (Maharashtra/MP/Jharkhand — millions)
    ("vah","वऱ्हाडी / Varhadi (Maharashtra, India)","₹99","₹299","kagad","← App Guide kade parat","App Store varun download →","Prashna","Samiksha:","✅ Chhan","⚠️ Chhan nahi","Kunasathi","Nahi","Developer chi baat."),
    ("bfy","बघेली / Bagheli (Madhya Pradesh, India)","₹99","₹299","kagaj","← App Guide phir","App Store se download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Badhiya nai","Kekre khatir","Nai","Developer ke baat."),
    ("unr","मुंडारी / Mundari (Jharkhand, India)","₹99","₹299","kagoj","← App Guide dubar","App Store se download →","Kajikom","Neleya:","✅ Bugin","⚠️ Ka bugin","Okoe nagente","Bano","Developer ako kaji."),
    ("sgj","सरगुजिया / Surgujia (Chhattisgarh, India)","₹99","₹299","kagaj","← App Guide phir","App Store le download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Badhiya nai","Kekar bar","Nai","Developer ke gapp."),
    ("dhn","डूंगरा भील / Dungra Bhil (India)","₹99","₹299","kagad","← App Guide pachho","App Store thi download →","Sawal","Samiksha:","✅ Saru","⚠️ Saru nahi","Kena mate","Nahi","Developer ni vaat."),
    ("kfx","कोया / Koya (Telangana, India)","₹99","₹299","kagitam","← App Guide ku tirigi","App Store nunchi download →","Adaganalu","Samiksha:","✅ Manchidi","⚠️ Manchidi kadu","Evari kosam","Ledu","Developer maata."),
    ("gwc","کالامي / Kalami (Pakistan)","PKR 300","PKR 900","kaghaz","← App Guide ta wapas","App Store na download →","Puchoona","Jaʼiza:","✅ Shai","⚠️ Shai na","Chi khatir","Na","Developer khabara."),
    ("bsh","کتی / Kati (Afghanistan/Pakistan)","Af 70","Af 200","kaghaz","← App Guide ta","App Store na download →","Pushten","Ktsel:","✅ Sha","⚠️ Sha ne","Kas lə para","Ne","Developer wayl."),
    ("kfe","कोटा / Kota (Tamil Nadu, India)","₹99","₹299","kaɡidam","← App Guide ku","App Store nunt download →","Kelvi","Parisilanai:","✅ Nalladu","⚠️ Nalladu illai","Yaarukku","Illai","Developer sonnadu."),
    ("emx","Erromintra (India)","₹99","₹299","kagad","← App Guide pacho","App Store thi download →","Sawal","Samiksha:","✅ Saro","⚠️ Saro nahi","Kena mate","Nahi","Developer ni vaat."),
    # Group AC: Pakistan/Somalia (Latin transliteration — big, non-RTL)
    ("hno","Northern Hindko (Pakistan)","PKR 300","PKR 900","kaghaz","← App Guide wapas","App Store toon download →","Sawal","Jaayza:","✅ Wadhiya","⚠️ Wadhiya nai","Kis waaste","Nai","Developer di gall."),
    ("hnd","Southern Hindko (Pakistan)","PKR 300","PKR 900","kaghaz","← App Guide wapas","App Store toon download →","Sawal","Jaayza:","✅ Changa","⚠️ Changa nai","Kis waaste","Nai","Developer di gall."),
    ("pmu","Mirpur Panjabi / Pahari-Pothwari (Pakistan)","PKR 300","PKR 900","kaghaz","← App Guide wapas","App Store toon download →","Sawal","Jaayza:","✅ Changa","⚠️ Changa nai","Kihde layi","Nai","Developer di gall."),
    ("bgq","Bagri (India/Pakistan)","₹99","₹299","kagad","← App Guide pachho","App Store su download →","Sawal","Samiksha:","✅ Chango","⚠️ Chango koni","Kina saru","Koni","Developer ri baat."),
    ("ymm","Maay (Somalia)","$1.50 USD","$4.50 USD","warqad","← Ku noqo App Guide","App Store ka soo deg →","Su'aalo","Dib u eegis:","✅ Wanaagsan","⚠️ Ma wanaagsana","Yaa loogu","Ma jiro","Qoraal developer."),
    ("gbk","Gaddi (Himachal Pradesh, India)","₹99","₹299","kagaj","← App Guide waapas","App Store te download →","Sawal","Samiksha:","✅ Changa","⚠️ Changa nai","Kaide layi","Nai","Developer di gall."),
    ("xnj","Kingoni / Ngoni (Tanzania)","TSh 2,500","TSh 7,500","ikaratasi","← Wuya App Guide","Pakua App Store →","Amaswali","Kulola:","✅ Chinunu","⚠️ Sichinunu","Kwa yani","Kutalimo","Amaghambo gha developer."),
    ("odk","Od (Pakistan/India)","PKR 300","PKR 900","kagat","← App Guide wapas","App Store maan download →","Sawal","Jaayzo:","✅ Saro","⚠️ Saro nahi","Keni khatar","Nahi","Developer ji gaalh."),
    ("kxp","Wadiyara Koli (Pakistan/India)","PKR 300","PKR 900","kagat","← App Guide wapas","App Store maan download →","Sawal","Jaayzo:","✅ Saro","⚠️ Saro nahi","Keni khatar","Nahi","Developer ji vaat."),
    ("pce","Ruching Palaung (Myanmar)","K 3,000","K 9,000","liktui","← Kir App Guide","App Store download →","Yaom","Yao:","✅ Om","⚠️ Om vi","Rah mai","Vi","Developer lai."),
    # Group AD: Big Bangladesh/E.India (Bengali-script/transliterated — millions)
    ("rkt","রংপুরী / Rangpuri-Kamta (Bangladesh/India)","৳ 90","৳ 270","dolil","← App Guide ot ghura","App Store thoni download →","Prosno","Porjalochona:","✅ Bhalo","⚠️ Bhalo nay","Kar bade","Nai","Developer-er kotha."),
    ("ctg","চাটগাঁইয়া / Chittagonian (Bangladesh)","৳ 90","৳ 270","dolil","← App Guide ot ghuri","App Store ottu download →","Fʼoshno","Zorip:","✅ Gom","⚠️ Gom noó","Hun-ottu","Nái","Developer-or hotha."),
    ("syl","ছিলটী / Sylheti (Bangladesh/India)","৳ 90","৳ 270","dolil","← App Guide o ghuri","App Store tune download →","Fʼoshno","Zaachai:","✅ Bhala","⚠️ Bhala nae","Kar lagi","Nai","Developer-or kotha."),
    ("swv","शेखावाटी / Shekhawati (Rajasthan, India)","₹99","₹299","kagad","← App Guide su wapas","App Store su download →","Sawal","Samiksha:","✅ Chokho","⚠️ Chokho koni","Kina saru","Koni","Developer ri baat."),
    ("kfq","कोरकू / Korku (Maharashtra/MP, India)","₹99","₹299","kagoj","← App Guide dubara","App Store se download →","Sawal","Neleya:","✅ Bhalo","⚠️ Ka bhalo","Ekon lagi","Bano","Developer ate kaji."),
    ("bpy","বিষ্ণুপ্রিয়া মণিপুরী / Bishnupriya (India)","₹99","₹299","kagos","← App Guide he ghuriya","App Store tun download →","Prosno","Nihari:","✅ Bhala","⚠️ Bhala nae","Kar karone","Nae","Developer-r kotha."),
    ("tdb","पंचपरगनिया / Panchpargania (Jharkhand, India)","₹99","₹299","kagoj","← App Guide phir","App Store se download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Badhiya nai","Kekar lel","Nai","Developer ke kotha."),
    ("xsr","ཤར་པ / Sherpa (Nepal)","NPR 130","NPR 390","yige","← App Guide log","App Store né download →","Diwa","Ta:","✅ Yakpo","⚠️ Ma yakpo","Su gi","Mindu","Developer ki kae."),
    ("kxv","କୁୱି / Kuvi (Odisha, India)","₹99","₹299","kagos","← App Guide ku bahuri","App Store ru download →","Prasna","Samikhya:","✅ Ndelka","⚠️ Nelka aai","Bosuna lai","Aai","Developer ni katha."),
    ("gbj","गुटोब / Bodo Gadaba (Odisha, India)","₹99","₹299","kagos","← App Guide ku bahuri","App Store ru download →","Prasna","Samikhya:","✅ Bhala","⚠️ Bhala nai","Boka lai","Nai","Developer ni katha."),
    # Group AE: N.India hill + tribal (Himachal/Jharkhand/Nepal)
    ("sdr","सादरी / Sadri-Oraon (Jharkhand, India)","₹99","₹299","kagoj","← App Guide phir","App Store se download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Badhiya nai","Kekar lel","Nai","Developer ke kotha."),
    ("mjl","मंडियाली / Mandeali (Himachal, India)","₹99","₹299","kagaj","← App Guide waapas","App Store te download →","Sawal","Samiksha:","✅ Changa","⚠️ Changa nai","Kaide layi","Nai","Developer di gall."),
    ("kex","कुकणा / Kukna (Gujarat/Maharashtra, India)","₹99","₹299","kagaj","← App Guide pachho","App Store thi download →","Sawal","Samiksha:","✅ Saru","⚠️ Saru nai","Kena mate","Nai","Developer ni vaat."),
    ("mjz","माझी / Majhi (Nepal)","NPR 130","NPR 390","kagat","← App Guide pheri","App Store bata download →","Prasna","Samiksha:","✅ Ramro","⚠️ Ramro chhaina","Kasko lagi","Chhaina","Developer ko kura."),
    ("srx","सिरमौरी / Sirmauri (Himachal, India)","₹99","₹299","kagaj","← App Guide waapas","App Store te download →","Sawal","Samiksha:","✅ Changa","⚠️ Changa nai","Kaide layi","Nai","Developer di gall."),
    ("mjt","माल्तो / Sauria Paharia (Jharkhand, India)","₹99","₹299","kagoj","← App Guide phir","App Store se download →","Sawal","Samiksha:","✅ Bhalo","⚠️ Ka bhalo","Ekre lel","Bano","Developer ate kaji."),
    ("xka","کلکوٹی / Kalkoti (Pakistan)","PKR 300","PKR 900","kaghaz","← App Guide wapas","App Store toon download →","Sawal","Jaayza:","✅ Changa","⚠️ Changa nai","Kis waaste","Nai","Developer di gall."),
    ("agi","अगरिया / Agariya (Madhya Pradesh, India)","₹99","₹299","kagoj","← App Guide phir","App Store se download →","Sawal","Samiksha:","✅ Bhalo","⚠️ Ka bhalo","Ekre lel","Bano","Developer ate kaji."),
    # Group AF: Philippine regional (Visayas/Mindanao/Palawan)
    ("cps","Capiznon (Philippines)","₱90","₱270","dokumento","← Balik sa App Guide","I-download sa App Store →","Mga pamangkot","Repaso:","✅ Maayo","⚠️ Indi maayo","Para kay sin-o","Wala","Nota kang developer."),
    ("tbl","Tboli (Philippines)","₱90","₱270","dokumento","← Uli App Guide","I-download App Store →","Mga sligo","Toladan:","✅ Kemhen","⚠️ Ye kemhen","Bé tau","Ye","Nota developer."),
    ("agn","Agutaynen (Palawan, Philippines)","₱90","₱270","dokumento","← Balik App Guide","I-download App Store →","Mga pangutana","Repaso:","✅ Mo'ya","⚠️ Belag mo'ya","Para kang sinong","Anda","Nota kang developer."),
    ("mta","Cotabato Manobo (Philippines)","₱90","₱270","dokumento","← Uli App Guide","I-download App Store →","Mga insa","Repaso:","✅ Madoyow","⚠️ Kena madoyow","Para ki sika","Wada","Nota to developer."),
    ("obo","Obo Manobo (Mindanao, Philippines)","₱90","₱270","dokumento","← Uli App Guide","I-download App Store →","Mga pangutana","Repaso:","✅ Mopiya","⚠️ Konna mopiya","Ki hongkua","Warad","Nota to developer."),
    ("msm","Agusan Manobo (Mindanao, Philippines)","₱90","₱270","dokumento","← Uli App Guide","I-download App Store →","Mga pangutana","Repaso:","✅ Maayad","⚠️ Diri maayad","Para ki kinsa","Wara","Nota to developer."),
    ("bnj","Eastern Tawbuid (Mindoro, Philippines)","₱90","₱270","dokumento","← Uli App Guide","I-download App Store →","Mga pangutana","Repaso:","✅ Mabuti","⚠️ Bukon mabuti","Para kanu","Wayd","Nota kanu developer."),
    ("bkn","Bukid / Binukid (Bukidnon, Philippines)","₱90","₱270","dokumento","← Uli App Guide","I-download App Store →","Mga pangutana","Repaso:","✅ Maayad","⚠️ Diri maayad","Para ki kinsa","Wara","Nota to developer."),
    # Group AG: European regional (high iOS density — Germany/Austria/Italy/Channel Islands)
    ("bar","Boarisch / Bavarian (Germany/Austria)","€3,99","€11,99","Dokument","← Zruck zin App Guide","Aus'm App Store lodn →","Frogn","Bewertung:","✅ Guad","⚠️ Ned guad","Fia wen","Neama","Entwickla-Notiz."),
    ("vmf","Fränkisch / Main-Franconian (Germany)","€3,99","€11,99","Dokument","← Zerück zum App Guide","Vom App Store lada →","Frooch","Bewertung:","✅ Guud","⚠️ Nedd guud","Für wen","Kaa","Entwickler-Notiz."),
    ("swg","Schwäbisch / Swabian (Germany)","€3,99","€11,99","Dokument","← Zruck zom App Guide","Vom App Store lada →","Fròòg","Bewertung:","✅ Guat","⚠️ Et guat","Für wen","Koi","Entwickler-Notiz."),
    ("ksh","Kölsch (Germany)","€3,99","€11,99","Dokumänt","← Zoréck zum App Guide","Us em App Store laade →","Froore","Bewäädung:","✅ Joot","⚠️ Nit joot","För wän","Keine","Entweckler-Notiz."),
    ("pfl","Pälzisch / Palatine German (Germany)","€3,99","€11,99","Dokument","← Zerick zum App Guide","Vum App Store lade →","Frooche","Bewertung:","✅ Gut","⚠️ Net gut","Fer wen","Kää","Entwickler-Notiz."),
    ("rgn","Rumagnôl / Romagnol (Italy)","€3,99","€11,99","documént","← Torna a l'App Guide","Scaréga da l'App Store →","Dmandi","Recensiòun:","✅ Bòn","⚠️ Miga bòn","Par chi","Nisùn","Nota dal svilupadòur."),
    ("egl","Emiliàn / Emilian (Italy)","€3,99","€11,99","documèint","← Tåurna a l'App Guide","Scaréga da l'App Store →","Dmànd","Recensiån:","✅ Bån","⚠️ BrîSa bån","Par chi","Inción","Nòta dal svilupadåur."),
    ("nrf","Jèrriais / Guernésiais (Channel Islands)","£3.99","£11.99","papi","← R'tourner à l'App Guide","Télécharger d'l'App Store →","Questions","R'view:","✅ Bouôn","⚠️ Pas bouôn","Pouor tchi","Nou-un","Note du développeu."),
    # Group AH: European regional 2 (Germany/Netherlands/Belgium/France)
    ("sxu","Sächsisch / Upper Saxon (Germany)","€3,99","€11,99","Dokument","← Zurück zum App Guide","Vom App Store lade →","Froochn","Bewärtung:","✅ Gud","⚠️ Nich gud","Für wen","Keene","Entwickler-Notiz."),
    ("vls","West-Vlams / West Flemish (Belgium)","€3,99","€11,99","dokument","← Weerom noa App Guide","Van App Store dàunloadn →","Vroagn","Beoordelienge:","✅ Goed","⚠️ Nie goed","Vo wien","Geen","Nota van d'ontwikkelaar."),
    ("wae","Walserdütsch / Walser (Switzerland/Italy)","CHF 3.90","CHF 11.90","Dokumänt","← Zrugg zum App Guide","Vom App Store lade →","Fragä","Bewärtig:","✅ Guät","⚠️ Nid guät","Für wä","Käi","Entwickler-Notiz."),
    ("zea","Zeêuws / Zeelandic (Netherlands)","€3,99","€11,99","dokument","← Weerom nè App Guide","Van App Store dôwnloade →","Vraege","Beoordelienge:","✅ Goed","⚠️ Nie goed","Voor wie","Gêên","Nota van de ontwikkelaer."),
    ("wep","Westfäölsk / Westphalian (Germany)","€3,99","€11,99","Dokument","← Trügge nao'n App Guide","Vun'n App Store laden →","Frogen","Beordelen:","✅ Gaud","⚠️ Nich gaud","För wen","Keen","Entwickler-Notiz."),
    ("prv","Provençau / Provençal (France)","€3,99","€11,99","documènt","← Tornar a l'App Guide","Descargar de l'App Store →","Questions","Evaluacien:","✅ Bòn","⚠️ Pas bòn","Per quau","Ges","Nòta dau desvolopaire."),
    ("oci","Lengadocian / Occitan (France)","€3,99","€11,99","document","← Tornar a l'App Guide","Telecargar de l'App Store →","Questions","Avaloracion:","✅ Bon","⚠️ Pas bon","Per qual","Pas cap","Nòta del desvolopaire."),
    ("srd","Sardu / Sardinian (Italy)","€3,99","€11,99","documentu","← Torra a s'App Guide","Iscàrriga dae s'App Store →","Preguntas","Recensione:","✅ Bonu","⚠️ Non bonu","Pro chie","Perunu","Nota de su isvilupadore."),
    # Group AI: Nordic/Alpine minority (very high iOS density)
    ("fit","Meänkieli (Sweden)","kr 39","kr 119","dokumentti","← Takaisin App Guidele","Lataa App Storesta →","Kysymykset","Arvostelu:","✅ Hyvä","⚠️ Ei hyvä","Kellek","Ei ole","Kehittäjän muistiinpano."),
    ("fkv","Kvääni / Kven (Norway)","kr 39","kr 119","dokumentti","← Takaisin App Guidele","Lasta App Storesta →","Kysymykset","Arvostelu:","✅ Hyvä","⚠️ Ei hyvä","Kelmar","Ei ole","Kehittäjän merknaadi."),
    ("twd","Twents (Netherlands)","€3,99","€11,99","dokument","← Weerumme noar App Guide","Van App Store daunloaden →","Vroagn","Beoordeling:","✅ Good","⚠️ Nich good","Veur wee","Gin","Notitie van de ontwikkelaar."),
    ("jut","Jysk / Jutlandic (Denmark)","kr 29","kr 89","dokument","← Tilbach til App Guide","Hent fra App Store →","Spørgsmål","Anmeldels:","✅ Godt","⚠️ Ikk godt","Te hvem","Ingen","Udviklerens noter."),
    ("ovd","Övdalska / Elfdalian (Sweden)","kr 39","kr 119","dokument","← Tillbaka til App Guide","Lasa app fro App Store →","Frogur","Bedömning:","✅ Bra","⚠️ Int bra","Fyr göö","Inggan","Utwitşlan-notis."),
    ("sju","Ubmejensámien / Ume Sami (Sweden)","kr 39","kr 119","dokumeanta","← Mahtsat App Guidien","Vieksehe App Storeste →","Gyhtjelmasa","Árvustallam:","✅ Buörre","⚠️ Ij buörre","Gieddie","Ij leah","Ovdedäddje neavttadus."),
    ("sje","Bidumsámegiella / Pite Sami (Sweden)","kr 39","kr 119","dokumeanta","← Mahtsat App Guidiin","Viektse App Storest →","Gatjádusá","Árvustallam:","✅ Buorre","⚠️ Ij buorre","Guhtiile","Ij le","Åvddåbargge návkkis."),
    ("gutn","Gutamål / Gutnish (Gotland, Sweden)","kr 39","kr 119","dukument","← Tillbaks te App Guide","Ladd nier fran App Store →","Fraigur","Bedömning:","✅ Bra","⚠️ Int bra","Ait vem","Ingen","Utwiklarens notis."),
    # Group AJ: Siberian Turkic (Cyrillic)
    ("kjh","Хакас / Khakas (Russia)","₽199","₽599","документ","← App Guide-зер","App Store-таң ал →","Сурығлар","Пағалас:","✅ Чахсы","⚠️ Чахсы нимес","Кемге","Чоғыл","Разработчик паза."),
    ("alt","Алтай / Southern Altai (Russia)","₽199","₽599","документ","← App Guide-ла кайра","App Store-доҥ алза →","Сурактар","Баалаш:","✅ Јакшы","⚠️ Јакшы эмес","Кемге","Јок","Разработчиктиҥ темдеги."),
    ("cjs","Шор / Shor (Russia)","₽199","₽599","документ","← App Guide-ка","App Store-таҥ ал →","Сурғлар","Паалаш:","✅ Чақшы","⚠️ Чақшы эбес","Кемге","Чоқ","Разработчик сӧзи."),
    ("dlg","Дулҕан / Dolgan (Russia)","₽199","₽599","докумуон","← App Guide-ка төннөн","App Store-тан ыл →","Ыйытыылар","Сыаналааһын:","✅ Үчүгэй","⚠️ Үчүгэй буолбат","Кимиэхэ","Суох","Оҥорооччу этиитэ."),
    ("kim","Тофа / Tofa (Russia)","₽199","₽599","документ","← App Guide-че","App Store-дан ал →","Айтырглар","Үнелээшкин:","✅ Экки","⚠️ Экки эвес","Кымга","Чок","Сайзырадыкчы демдээ."),
    ("kdr","Karaim (Lithuania/Ukraine)","€3,99","€11,99","dokument","← App Guide'ǵa kayt","App Store'dan al →","Sorumlar","Baxnav:","✅ Yaxşı","⚠️ Yaxşı tuvul","Kimge","Yox","Ǵeliştirici sozü."),
    ("krl","Karjala / Karelian (Russia/Finland)","€3,99","€11,99","dokumentu","← Järilleh App Guide","App Storespäi lataa →","Kyzymykset","Arvostelu:","✅ Hyvä","⚠️ Ei hyvä","Kelle","Ei ole","Kehittäjän merkindü."),
    ("mrj","Мары / Hill Mari (Russia)","₽199","₽599","документ","← App Guide-ышкы","App Store гыц нал →","Йодмаш","Аклымаш:","✅ Сай","⚠️ Сай огыл","Кӧлан","Уке","Ыштыше ой."),
    # Group AK: remaining mid/small Indian tribal
    ("gas","आदिवासी गरासिया / Adiwasi Garasia (Rajasthan, India)","₹99","₹299","kagad","← App Guide pachho","App Store thi download →","Sawal","Samiksha:","✅ Saru","⚠️ Saru nai","Kena mate","Nai","Developer ni vaat."),
    ("kdq","कोच / Koch (Assam, India)","₹99","₹299","kagos","← App Guide he ghuri","App Store tun download →","Prosno","Nihari:","✅ Bhalo","⚠️ Bhalo nae","Kar karone","Nae","Developer-r kotha."),
    ("anr","आंध / Andh (Maharashtra, India)","₹99","₹299","kagad","← App Guide kade parat","App Store varun download →","Prashna","Samiksha:","✅ Chhan","⚠️ Chhan nahi","Kunasathi","Nahi","Developer chi baat."),
    ("dry","दरै / Darai (Nepal)","NPR 130","NPR 390","kagat","← App Guide pheri","App Store bata download →","Prasna","Samiksha:","✅ Ramro","⚠️ Ramro chhaina","Kasko lagi","Chhaina","Developer ko kura."),
    ("unx","मुंडा / Munda-Nihali (India)","₹99","₹299","kagoj","← App Guide dubar","App Store se download →","Kajikom","Neleya:","✅ Bugin","⚠️ Ka bugin","Okoe nagente","Bano","Developer ako kaji."),
    ("bfw","बोंडो / Bondo (Odisha, India)","₹99","₹299","kagos","← App Guide ku bahuri","App Store ru download →","Prasna","Samikhya:","✅ Bhala","⚠️ Bhala nai","Boka lai","Nai","Developer ni katha."),
    # Group: mid-size Indic/Nepali langs (round 162+) — combined 30M+ speakers
    ("bjj","कन्नौजी / Kanauji (Uttar Pradesh, India)","₹99","₹299","kagaj","← App Guide pe wapas","App Store se download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Theek nahi","Kekar khatir","Nahi","Developer ki baat."),
    ("bns","बुन्देली / Bundeli (Madhya Pradesh, India)","₹99","₹299","kagaj","← App Guide pe wapas","App Store se download →","Sawal","Samiksha:","✅ Neek","⚠️ Theek nai","Kaike laane","Nai","Developer ki baat."),
    ("mup","मालवी / Malvi (Madhya Pradesh, India)","₹99","₹299","kagaj","← App Guide pe pacha","App Store su download →","Sawal","Samiksha:","✅ Hariyo","⚠️ Theek koni","Kina waste","Koni","Developer ri baat."),
    ("bhb","भीली / Bhili (Rajasthan/Gujarat, India)","₹99","₹299","kagad","← App Guide pe pachha","App Store thi download →","Sawal","Samiksha:","✅ Saru","⚠️ Saru nathi","Kona hate","Nathi","Developer ni vaat."),
    ("gom","कोंकणी / Goan Konkani (Goa, India)","₹99","₹299","kagad","← App Guide-ak porot","App Store savn download →","Prasn","Porikha:","✅ Boro","⚠️ Boro nhoi","Konnak","Nhoi","Developer-achi khobor."),
    ("ahr","अहिराणी / Ahirani (Maharashtra, India)","₹99","₹299","kagad","← App Guide kade parat","App Store varun download →","Prashna","Samiksha:","✅ Chhan","⚠️ Chhan nahi","Konasathi","Nahi","Developer chi goshta."),
    ("dty","डोटेली / Doteli (Nepal)","NPR 130","NPR 390","kagat","← App Guide ma pheri","App Store bata download →","Prasna","Samiksha:","✅ Ramro","⚠️ Ramro chhaina","Kaska lagi","Chhaina","Developer ko kura."),
    ("thl","डँगौरा थारू / Dangaura Tharu (Nepal)","NPR 130","NPR 390","kagat","← App Guide ma pheri","App Store bata download →","Prasna","Samiksha:","✅ Ramro","⚠️ Ramro nai","Kasko lagi","Nai","Developer ko kura."),
    # Group: RTL Perso-Arabic mega-batch (round 164+) — ~110M speakers; post-process adds dir="rtl"
    ("pnb","پنجابی شاہ مکھی / Western Punjabi (Pakistan)","Rs 500","Rs 1,500","دستاویز","← واپس App Guide","App Store توں ڈاؤن لوڈ →","سوال","جائزہ:","✅ ودھیا","⚠️ ٹھیک نئیں","کیندے لئی","نئیں","ڈویلپر دی گل۔"),
    ("prs","دری / Dari (Afghanistan)","Af 70","Af 200","سند","← بازگشت به App Guide","دانلود از App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نیست","برای چه کسی","مناسب نیست","یادداشت انکشاف‌دهنده."),
    ("bal","بلوچی / Balochi (Pakistan/Iran)","Rs 500","Rs 1,500","دستاویز","← واتر App Guide","App Store ءَ چہ ڈاؤن لوڈ →","سوال","جائزہ:","✅ شر","⚠️ شر نہ اِنت","کئی ءِ واستہ","نہ اِنت","ڈویلپر ءِ ہبر۔"),
    ("kas","کٲشُر / Kashmiri (India, Perso-Arabic)","₹99","₹299","دستاویز","← App Guide پؠٹھ واپس","App Store پؠٹھہٕ ڈاؤن لوڈ →","سوال","جائزٕ:","✅ جان","⚠️ ٹھیک چھُ نہٕ","کَمِس خٲطرٕ","نہٕ","ڈیولپر سُند نوٹ۔"),
    ("sdh","کوردی خوارگ / Southern Kurdish (Iran/Iraq)","تومان 50,000","تومان 150,000","بەڵگە","← گەڕانەوە بۆ App Guide","داگرتن لە App Store →","پرسیار","هەڵسەنگاندن:","✅ باش","⚠️ باش نییە","بۆ کێ","نییە","تێبینی گەشەپێدەر."),
    ("khw","کھوار / Khowar (Chitral, Pakistan)","Rs 500","Rs 1,500","دستاویز","← App Guide واپس","App Store ار ڈاؤن لوڈ →","سوال","جائزہ:","✅ جم","⚠️ جم نو","کا بچے","نو","ڈویلپر و نوٹ۔"),
    ("bcc","جنوبی بلوچی / Southern Balochi (Makran)","Rs 500","Rs 1,500","دستاویز","← واتر App Guide","App Store ءَ چہ ڈاؤن لوڈ →","سوال","جائزہ:","✅ شر","⚠️ شر نہ اِنت","کئی ءِ واستہ","نہ اِنت","ڈویلپر ءِ ہبر۔"),
    ("bft","بلتی / Balti (Pakistan)","Rs 500","Rs 1,500","دستاویز","← App Guide واپس","App Store نس ڈاؤن لوڈ →","سوال","جائزہ:","✅ لیاقمو","⚠️ ٹھیک مید","سو لا","مید","ڈویلپر نوٹ۔"),
    # Group: Nepal/India hills + Iran residual (round 166+)
    ("thq","कठरिया थारू / Kathoriya Tharu (Nepal)","NPR 130","NPR 390","kagat","← App Guide ma pheri","App Store bata download →","Prasna","Samiksha:","✅ Ramro","⚠️ Ramro nai","Kasko lagi","Nai","Developer ko kura."),
    ("the","चितवनिया थारू / Chitwania Tharu (Nepal)","NPR 130","NPR 390","kagat","← App Guide ma pheri","App Store bata download →","Prasna","Samiksha:","✅ Ramro","⚠️ Ramro nai","Kasko lagi","Nai","Developer ko kura."),
    ("kfr","कच्छी / Kachhi (Gujarat, India)","₹99","₹299","kagad","← App Guide te pachha","App Store thi download →","Sawal","Samiksha:","✅ Saru","⚠️ Saru nai","Kena vaste","Nai","Developer ni vaat."),
    ("gvr","गुरुङ / Gurung (Nepal)","NPR 130","NPR 390","kagat","← App Guide ma pheri","App Store bata download →","Prasna","Samiksha:","✅ Chhyaba","⚠️ Chhyaba are","Su lai","Are","Developer ko kura."),
    ("lif","लिम्बू / Limbu (Nepal/India)","NPR 130","NPR 390","kagat","← App Guide ma pheri","App Store bata download →","Prasna","Samiksha:","✅ Nuba","⚠️ Nuba men","Hatlai","Men","Developer ko kura."),
    ("sck","सादरी / Sadri-Oraon (Jharkhand, India)","₹99","₹299","kagaj","← App Guide me wapas","App Store se download →","Sawal","Samiksha:","✅ Badhiya","⚠️ Thik nai","Kekar lagin","Nai","Developer ke baat."),
    # Group: SE Asia regional (round 168+) — Isan ~15M! Lanna 6M, S.Thai 4.5M
    ("tts","ภาษาอีสาน / Isan (NE Thailand)","฿69","฿199","เอกสาร","← เมือกลับ App Guide","โหลดจาก App Store →","คำถาม","เบิ่งผล:","✅ ดีหลาย","⚠️ บ่แม่น","เหมาะกับไผ","บ่เหมาะ","หมายเหตุผู้พัฒนา"),
    ("nod","คำเมือง / Northern Thai · Lanna (Chiang Mai)","฿69","฿199","เอกสาร","← ปิ๊กไป App Guide","โหลดจาก App Store →","คำถาม","ผ่อผล:","✅ งามแต้","⚠️ บ่ใจ่","เหมาะกับไผ","บ่เหมาะ","หมายเหตุผู้พัฒนา"),
    ("sou","ภาษาใต้ / Southern Thai (Nakhon Si Thammarat)","฿69","฿199","เอกสาร","← หลบไป App Guide","โหลดจาก App Store →","คำถาม","แลผล:","✅ ดีจัง","⚠️ ม่ายช่าย","เหมาะกับใคร","ม่ายเหมาะ","หมายเหตุผู้พัฒนา"),
    ("khb","ᦅᦴᧉᦑᦺ / Tai Lü (Xishuangbanna/Laos)","฿69","฿199","เอกสาร","← กลับ App Guide","โหลดจาก App Store →","คำถาม","ผล:","✅ ดี","⚠️ บ่ดี","เหมาะกับไผ","บ่เหมาะ","หมายเหตุผู้พัฒนา"),
    ("ksw","စှီၤကညီကျိာ် / S'gaw Karen (Myanmar/Thailand)","K 2,500","K 7,500","လံာ်","← က့ၤ App Guide","App Store ဒီးလုၤ →","တၢ်သံကွၢ်","ကွၢ်:","✅ ဂ့ၤ","⚠️ တဂ့ၤ","လၢမတၤ","တလီၤ","Developer တၢ်ကွဲး"),
    ("rki","ရခိုင်ဘာသာ / Rakhine (Myanmar)","K 2,500","K 7,500","စာရွက်","← App Guide သို့ပြန်","App Store မှဒေါင်းလုဒ် →","မေးခွန်း","သုံးသပ်ချက်:","✅ ကောင်းရေ","⚠️ မကောင်းပါ","ဘယ်သူ့အတွက်လဲ","မသင့်ပါ","Developer မှတ်ချက်"),
    ("luz","لری جنوبی / Southern Luri (Iran)","تومان 50,000","تومان 150,000","سند","← بازگشت به App Guide","دانلود از App Store →","سوالات","بررسی:","✅ خوب","⚠️ مناسب نیست","سی کی","مناسب نیست","یادداشت توسعه‌دهنده."),
    # Group: Indonesian regional (round 170) — Madurese 7M, Banjar 3.5M, Balinese 3.3M
    ("mad","Basa Madhura / Madurese (Madura, Indonesia)","Rp 19.000","Rp 59.000","dokumen","← Abali ka App Guide","Unduh dari App Store →","Pertanyaan","Peninjauan:","✅ Bagus","⚠️ Ta' cocok","Kaangguy sapa","Banne","Catatan developer."),
    ("ban","Basa Bali / Balinese (Bali, Indonesia)","Rp 19.000","Rp 59.000","dokumen","← Mawali ka App Guide","Unduh saking App Store →","Pitakon","Peninjauan:","✅ Becik","⚠️ Nenten cocok","Anggen sira","Nenten","Catetan developer."),
    ("bjn","Bahasa Banjar / Banjarese (Kalimantan, Indonesia)","Rp 19.000","Rp 59.000","dokumen","← Bulik ka App Guide","Unduh matan App Store →","Patakunan","Peninjauan:","✅ Baik banar","⚠️ Kada cocok","Gasan siapa","Kada","Catatan developer."),
    # Group: major storefront locales that never got base pages (2026-08 backfill)
    ("zh-Hans","简体中文 / Simplified Chinese","¥12","¥38","文件","← 返回 App Guide","在 App Store 下载 →","常见问题","评测:","✅ 优点","⚠️ 不足","适合谁","不适合谁","开发者说明。"),
    ("sv","Svenska / Swedish (Sweden)","25 kr","75 kr","dokument","← Tillbaka till App Guide","Ladda ner i App Store →","Vanliga frågor","Omdöme:","✅ Fördelar","⚠️ Nackdelar","Passar för","Passar inte för","Utvecklarens anmärkning."),
    ("da","Dansk / Danish (Denmark)","19 kr.","59 kr.","dokumenter","← Tilbage til App Guide","Hent i App Store →","Ofte stillede spørgsmål","Vurdering:","✅ Fordele","⚠️ Ulemper","Passer til","Passer ikke til","Udviklerens bemærkning."),
]

B="body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#222}h1{font-size:1.5rem;line-height:1.8}h2{font-size:1.1rem;margin-top:2rem}.item{border:1px solid #e5e7eb;border-radius:10px;padding:1rem;margin:.8rem 0}.item h3{margin:0 0 .3rem;font-size:1rem}.dl{display:inline-block;background:#007aff;color:#fff;padding:.55rem 1.2rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.9rem;margin:.5rem 0}.faq{border:1px solid #e8e8e8;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0}.faq summary{cursor:pointer;font-size:.95rem}.faq p{margin:.5rem 0 0;color:#444;font-size:.9rem}"
S=B+"ol{padding-left:1.3rem}li{margin:.5rem 0;font-size:.95rem}"
V="body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#222}h1{font-size:1.5rem;line-height:1.8}table{width:100%;border-collapse:collapse;font-size:.9rem}th,td{border:1px solid #e5e7eb;padding:.5rem .7rem;text-align:left}th{background:#f9fafb}.faq{border:1px solid #e8e8e8;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0}.faq summary{cursor:pointer;font-size:.95rem}.faq p{margin:.5rem 0 0;color:#444;font-size:.9rem}"
R="body{font-family:system-ui,sans-serif;max-width:700px;margin:2rem auto;padding:0 1rem;color:#222}h1{font-size:1.4rem;line-height:1.8}h2{font-size:1.1rem;margin-top:2rem}.stars{color:#f59e0b;font-size:1.3rem;margin:.5rem 0}ul{padding-left:1.2rem}li{margin:.3rem 0;font-size:.9rem}.pros li::marker{color:#1a7f37}.cons li::marker{color:#cf2029}.dl{display:inline-block;background:#007aff;color:#fff;padding:.55rem 1.2rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.9rem;margin:1.2rem 0}.disclaimer{font-size:.8rem;color:#888;border:1px solid #eee;border-radius:6px;padding:.6rem .8rem;margin:1.5rem 0}.faq{border:1px solid #e8e8e8;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0}.faq summary{cursor:pointer;font-size:.95rem}.faq p{margin:.5rem 0 0;color:#444;font-size:.9rem}"

def _fl(f): return [{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in f]
def _fh(f): return "\n".join(f'<details class="faq"><summary><strong>{q}</strong></summary><p>{a}</p></details>' for q,a in f)

def _apps():
    try:
        sys.path.insert(0, str(HERE.parent / "social"))
        from videogen.registry import APPS as A, APPSTORE as AS
        return A, AS
    except Exception:
        return {}, {}

# ---------------------------------------------------------------------------
# Query clusters — the second axis of the work pool.
# The language axis is saturated (1000+ locale directories under pages/), so new
# autobatch work now comes from new *query intents* applied to known languages.
# Each cluster is a list of pages: (slug, title, desc, h1, intro, [(app_key, why)], [(q, a)])
# Only public apps are rendered; pricing wording is derived from the registry
# purchase_model at build time so it can never claim something untrue.
# ---------------------------------------------------------------------------
PRICING_LINE = {
    "paid_upfront": "One-time purchase; no subscription.",
    "free_with_lifetime_unlock": "Free to download; one-time lifetime unlock.",
    "free": "Free.",
    "flexible": "One-time unlock option; optional subscription plans.",
}


CLUSTER_ORDER = ["problems", "pay-once", "no-account", "family", "seasonal-gifting", "switching", "lite-vs-pro"]


def _cluster_l10n(cluster_id):
    """Localized body copy, keyed by locale. Empty dict when we have none."""
    try:
        sys.path.insert(0, str(HERE))
        import cluster_l10n
        return {"problems": cluster_l10n.PROBLEMS}.get(cluster_id, {})
    except Exception:
        return {}


def _pricing_l10n():
    """Localized pricing wording per locale. Empty dict when unavailable."""
    try:
        sys.path.insert(0, str(HERE))
        import cluster_l10n
        return cluster_l10n.PRICING
    except Exception:
        return {}

# Major App Store storefront locales. These already have base language pages from
# earlier generators, so they carry no entry in CANDIDATE_POOL — but they are the
# markets that actually produce impressions, so clusters run here first.
# Tuple shape matches the first 8 fields of CANDIDATE_POOL rows.
MAJOR_LOCALES = [
    ("en", "English", "$1.99", "$5.99", "documents", "← Back to App Guide", "Download on the App Store →", "Questions"),
    ("en-GB", "English (UK)", "£1.99", "£5.99", "documents", "← Back to App Guide", "Download on the App Store →", "Questions"),
    ("en-AU", "English (Australia)", "A$2.99", "A$8.99", "documents", "← Back to App Guide", "Download on the App Store →", "Questions"),
    ("en-CA", "English (Canada)", "C$2.99", "C$8.99", "documents", "← Back to App Guide", "Download on the App Store →", "Questions"),
    ("de-DE", "Deutsch", "1,99 €", "5,99 €", "Dokumente", "← Zurück zum App Guide", "Im App Store laden →", "Häufige Fragen"),
    ("fr-FR", "Français", "1,99 €", "5,99 €", "documents", "← Retour au App Guide", "Télécharger sur l'App Store →", "Questions fréquentes"),
    ("es-ES", "Español", "1,99 €", "5,99 €", "documentos", "← Volver al App Guide", "Descargar en el App Store →", "Preguntas frecuentes"),
    ("es-MX", "Español (México)", "$39 MXN", "$119 MXN", "documentos", "← Volver al App Guide", "Descargar en el App Store →", "Preguntas frecuentes"),
    ("it-IT", "Italiano", "1,99 €", "5,99 €", "documenti", "← Torna all'App Guide", "Scarica sull'App Store →", "Domande frequenti"),
    ("pt-BR", "Português (Brasil)", "R$ 9,90", "R$ 29,90", "documentos", "← Voltar ao App Guide", "Baixar na App Store →", "Perguntas frequentes"),
    ("ja-JP", "日本語", "¥300", "¥900", "書類", "← App Guide に戻る", "App Store でダウンロード →", "よくある質問"),
    ("ko-KR", "한국어", "₩2,500", "₩7,500", "문서", "← App Guide로 돌아가기", "App Store에서 다운로드 →", "자주 묻는 질문"),
    ("zh-Hant", "繁體中文", "NT$60", "NT$180", "文件", "← 回到 App Guide", "在 App Store 下載 →", "常見問題"),
    ("zh-Hans", "简体中文", "¥12", "¥38", "文件", "← 返回 App Guide", "在 App Store 下载 →", "常见问题"),
    ("th", "ไทย", "฿69", "฿199", "เอกสาร", "← กลับไปที่ App Guide", "ดาวน์โหลดบน App Store →", "คำถามที่พบบ่อย"),
    ("vi", "Tiếng Việt", "49.000 ₫", "149.000 ₫", "tài liệu", "← Quay lại App Guide", "Tải trên App Store →", "Câu hỏi thường gặp"),
    ("id", "Bahasa Indonesia", "Rp 19.000", "Rp 59.000", "dokumen", "← Kembali ke App Guide", "Unduh di App Store →", "Pertanyaan umum"),
    ("ms", "Bahasa Melayu", "RM 8.90", "RM 26.90", "dokumen", "← Kembali ke App Guide", "Muat turun di App Store →", "Soalan lazim"),
    ("tr", "Türkçe", "₺59", "₺179", "belgeler", "← App Guide'a dön", "App Store'dan indir →", "Sık sorulan sorular"),
    ("ru", "Русский", "199 ₽", "599 ₽", "документы", "← Назад в App Guide", "Загрузить в App Store →", "Частые вопросы"),
    ("pl", "Polski", "8,99 zł", "26,99 zł", "dokumenty", "← Powrót do App Guide", "Pobierz w App Store →", "Częste pytania"),
    ("hi", "हिन्दी", "₹99", "₹299", "दस्तावेज़", "← App Guide पर वापस", "App Store से डाउनलोड करें →", "अक्सर पूछे जाने वाले प्रश्न"),
    ("ar-SA", "العربية", "‏7.99 ر.س", "‏22.99 ر.س", "المستندات", "← العودة إلى App Guide", "التحميل من App Store →", "الأسئلة الشائعة"),
    ("sv", "Svenska", "25 kr", "75 kr", "dokument", "← Tillbaka till App Guide", "Ladda ner i App Store →", "Vanliga frågor"),
    ("da", "Dansk", "19 kr.", "59 kr.", "dokumenter", "← Tilbage til App Guide", "Hent i App Store →", "Ofte stillede spørgsmål"),
    ("nb-NO", "Norsk bokmål", "25 kr", "75 kr", "dokumenter", "← Tilbake til App Guide", "Last ned i App Store →", "Vanlige spørsmål"),
    ("fi", "Suomi", "1,99 €", "5,99 €", "asiakirjat", "← Takaisin App Guideen", "Lataa App Storesta →", "Usein kysytyt kysymykset"),
    ("cs", "Čeština", "49 Kč", "149 Kč", "dokumenty", "← Zpět na App Guide", "Stáhnout v App Storu", "Časté dotazy"),
]


def _cluster_defs(cn, pl, ph, doc):
    return {
        "problems": ("problems", "problems", [
            ("wifi-connected-no-internet",
             f"iPhone Says Wi-Fi Connected But No Internet — {cn} 2026",
             "Find which link in the chain is actually broken.",
             f"Wi-Fi Connected, No Internet on iPhone ({cn} 2026)",
             "The bars look fine but nothing loads. The useful question is which step fails: the local path, DNS, TCP, TLS or the server.",
             [("wifiaid", "Runs independent path, DNS, TCP, TLS, timing and signal checks and reports the most likely cause."),
              ("cyca", "Checks what your connection exposes before you trust a public network.")],
             [("Does it need an account?", "No account is required."),
              ("Will it fix the router for me?", "No. It tells you where the failure is so you know what to change.")]),
            ("photo-too-blurry-to-read",
             f"Photo Too Blurry to Read the Text — {cn} 2026",
             "Recover a readable copy of a shaky or low-light shot.",
             f"Photo Too Blurry to Read ({cn} 2026)",
             "A receipt, whiteboard or sign came out soft and the text is unreadable. Sharpening on device is usually enough.",
             [("unblurry", "Sharpen and de-blur a photo on device so small text becomes readable again."),
              ("picclear", "Clean up and clear out the near-duplicate shots left behind.")],
             [("Is the original changed?", "No. The original stays in your library."),
              ("Does it upload my photo?", "Processing happens on device.")]),
            ("passport-photo-rejected",
             f"My Passport Photo Was Rejected — {cn} 2026",
             "Retake an ID photo that matches the official size and background rules.",
             f"Passport Photo Rejected — What to Fix ({cn} 2026)",
             "Rejections are usually size, head position, shadows or background. All four are fixable at home.",
             [("snapport", "Guided sizing, background tools and a print-ready sheet for passport, visa and ID photos."),
              ("snapportlite", "Same guided sizing, free to try before you unlock.")],
             [("Which country specs?", "Choose the size your authority requires before exporting."),
              ("Do I need a photo studio?", "No. A plain wall and daylight are enough.")]),
            ("shared-file-contains-private-data",
             f"I Need to Share a File That Contains Private Data — {cn} 2026",
             "Remove names, numbers and addresses before you send a document.",
             f"Share a File Without Leaking Private Data ({cn} 2026)",
             "Blacking out with a drawing tool is not redaction — the text often survives underneath. Remove it properly.",
             [("maskmyfile", "Finds private details in a file and masks them on device before you share."),
              ("scanto", "Scan paper to PDF locally, so the source never touches a server.")],
             [("Is the original overwritten?", "No, a masked copy is produced."),
              ("Does it upload the file?", "No. The work happens on device.")]),
            ("iphone-storage-full",
             f"iPhone Storage Full Without Deleting Memories — {cn} 2026",
             "Free space by clearing duplicates and clutter, not photos you care about.",
             f"iPhone Storage Full ({cn} 2026)",
             "Most reclaimable space is duplicates, blurry rejects and screenshots — not the photos you would miss.",
             [("picclear", "Review near-duplicates and blurry shots and clear them in batches."),
              ("scanto", "Replace stacks of paper photos of documents with a single searchable PDF.")],
             [("Does it delete without asking?", "No. You confirm before anything is removed."),
              ("Does it need iCloud?", "No.")]),
        ]),
        "pay-once": ("pay-once", "payonce", [
            ("photo-tools",
             f"Pay-Once iPhone Photo Tools — {cn} 2026",
             "Photo utilities you buy once instead of renting.",
             f"Pay-Once iPhone Photo Tools ({cn} 2026)",
             "Subscription fatigue is real. These photo tools use a one-time payment instead — check the App Store for your local price.",
             [("unblurry", "Sharpen soft photos on device."),
              ("picclear", "Clear duplicates and blurry shots."),
              ("snapport", "Passport and ID photos with guided sizing."),
              ("photocream", "Film-look recipes applied on device.")],
             [("Is there a monthly fee?", "No recurring subscription is required for these."),
              ("Do prices differ by country?", "Yes. The App Store shows your local price.")]),
            ("document-tools",
             f"Pay-Once iPhone Document Tools — {cn} 2026",
             f"Scan, redact and store {doc} without a subscription.",
             f"Pay-Once iPhone Document Tools ({cn} 2026)",
             f"Handling {doc} on a phone should not need a monthly plan. These are one-time unlocks — the App Store shows your local price.",
             [("scanto", "Offline scanning to PDF with on-device OCR."),
              ("maskmyfile", "Mask private details before sharing."),
              ("cvdesk", "Build and export a CV without a rented editor."),
              ("aibriefpack", "Turn screenshots and files into one clear brief.")],
             [("Do files leave the device?", "These tools work on device."),
              ("Is an account required?", "No.")]),
            ("travel-tools",
             f"Pay-Once iPhone Travel Tools — {cn} 2026",
             "Trip planning, money and phrases without a travel subscription.",
             f"Pay-Once iPhone Travel Tools ({cn} 2026)",
             "One trip should not cost a yearly plan. These unlock once and keep working offline.",
             [("tripbee", "Day-by-day offline itinerary and packing lists."),
              ("tripbeelite", "One upcoming trip, free to start."),
              ("gmoney", "Log spending with currency conversion."),
              ("dailymate", "Complete travel sentences, not isolated words.")],
             [("Do they work without signal?", "The core planning and phrase features work offline."),
              ("Is there a recurring charge?", "No recurring subscription is required.")]),
            ("focus-and-habits",
             f"Pay-Once iPhone Focus and Habit Tools — {cn} 2026",
             "Routine, focus and awareness tools with a one-time unlock.",
             f"Pay-Once iPhone Focus and Habit Tools ({cn} 2026)",
             "Habit apps are the most subscription-heavy category. These are not.",
             [("mochi", "Simple recurring tasks that stay out of the way."),
              ("mochidonestamp", "Record when you last did something you only do a few times a year."),
              ("lockhour", "Set aside blocks of time for focused work."),
              ("hourstag", "See a purchase as the hours of work it costs.")],
             [("Are there ads?", "No ads in these apps."),
              ("Is an account required?", "No.")]),
        ]),
        "no-account": ("no-account", "noaccount", [
            ("no-signup-apps",
             f"iPhone Apps That Need No Sign-Up — {cn} 2026",
             "Open the app and start. No email, no password, no profile.",
             f"iPhone Apps With No Sign-Up ({cn} 2026)",
             "A sign-up screen before you have seen the app is a tax on your attention and your inbox. These start on first launch.",
             [("scanto", "Scan straight to PDF the moment you open it."),
              ("unblurry", "Pick a photo and sharpen it. Nothing to register."),
              ("wifiaid", "Run a diagnosis without creating anything."),
              ("mochi", "Add a task and close the app.")],
             [("Is there a login wall?", "No account is required to use these."),
              ("Is my data synced to a server?", "These apps work on device.")]),
            ("offline-only-apps",
             f"iPhone Apps That Work With No Internet — {cn} 2026",
             "Tools that keep working on a plane, in a basement or abroad.",
             f"iPhone Apps That Work Offline ({cn} 2026)",
             "Roaming off, no signal, hotel Wi-Fi refusing to load — these still do their job.",
             [("scanto", "Scanning and on-device OCR need no connection."),
              ("tripbee", "Your day-by-day plan and packing lists stay available offline."),
              ("snapport", "Size and export an ID photo with no connection."),
              ("aim990", "Listening and reading practice stored on the device.")],
             [("Does anything break offline?", "The core features listed here do not need a connection."),
              ("Do they upload my files?", "No.")]),
            ("no-tracking-apps",
             f"iPhone Apps With No Tracking — {cn} 2026",
             "Tools that do not build a profile of you.",
             f"iPhone Apps That Do Not Track You ({cn} 2026)",
             "Check the App Store privacy label before you install anything. These are built to keep the work on your device.",
             [("maskmyfile", "Redaction happens locally; the file never leaves."),
              ("cyca", "Shows what your connection exposes, without collecting it."),
              ("picclear", "Reviews your library on device."),
              ("sononote", "Notes stay on the device.")],
             [("Are there third-party ads?", "No ads in these apps."),
              ("Where is my data stored?", "On your device.")]),
            ("no-watermark-apps",
             f"iPhone Apps That Export Without a Watermark — {cn} 2026",
             "Export the file you made, not an advertisement for the app.",
             f"iPhone Apps With No Export Watermark ({cn} 2026)",
             "Free tools that stamp their logo on your export are not free — they cost you the file. These do not.",
             [("scanto", "PDF exports carry no stamp."),
              ("snapport", "Print-ready ID photo sheets export clean."),
              ("photocream", "Applies the look you chose and nothing else."),
              ("cvdesk", "Your CV exports as your CV.")],
             [("Is the watermark removed by a purchase?", "These export without a watermark; check each listing for what the unlock covers."),
              ("Is export quality reduced?", "No.")]),
        ]),
        "family": ("family", "family", [
            ("apps-for-parents",
             f"iPhone Apps Parents Actually Use — {cn} 2026",
             "Tools for the admin side of family life, not another screen for the kids.",
             f"iPhone Apps for Parents ({cn} 2026)",
             "Most 'family app' lists are really kids' games. This one is about the paperwork, the logistics and the forgetting.",
             [("mochidonestamp", "Remember when you last did the things nobody schedules."),
              ("scanto", "School forms and receipts into searchable PDFs."),
              ("lumiweather", "Decide what the children should wear before you leave."),
              ("snapport", "Passport photos for the whole family at home.")],
             [("Are these kids' apps?", "No, these are for the adult running the household."),
              ("Do they need accounts?", "No.")]),
            ("choosing-a-kids-app",
             f"How to Choose a Kids' App Without Regret — {cn} 2026",
             "What to check before you install anything for a child.",
             f"Choosing a Kids' App ({cn} 2026)",
             "Four checks catch most bad installs: ads, in-app purchases, what data leaves the device, and whether the app runs without a connection.",
             [("lumiletters", "Phonics practice with no ads and nothing to sign up for."),
              ("lumimath", "Number sense through a build-a-planet sandbox. No ads."),
              ("lumibopomofo", "Bopomofo for children. No ads."),
              ("lumimission", "Daily routines as missions. No ads.")],
             [("Are there ads?", "No ads in these."),
              ("Is the artwork hand-drawn?", "No. The artwork is AI-generated and the speech uses system text-to-speech.")]),
            ("screen-time-that-is-worth-it",
             f"Screen Time Worth Allowing — iPhone {cn} 2026",
             "Short sessions with a clear end, instead of an endless feed.",
             f"Screen Time Worth Allowing ({cn} 2026)",
             "The problem is rarely the screen; it is the app with no ending. These have one.",
             [("lumiletters", "A round of letters ends when the round ends."),
              ("lumimath", "Short, finishable number activities."),
              ("lumimission", "A daily mission list, then done."),
              ("lockhour", "For the adult: block out the time you want back.")],
             [("Do these use loot boxes or streak pressure?", "No."),
              ("Do they need an account?", "No.")]),
            ("family-travel-day",
             f"Getting a Family Out the Door — iPhone {cn} 2026",
             "Packing, weather, documents and the itinerary in one pass.",
             f"Family Travel Day Checklist ({cn} 2026)",
             "Family trips fail at the door, not at the destination. Handle the four things that actually delay you.",
             [("tripbee", "Day-by-day plan and packing lists that work offline."),
              ("lumiweather", "What to wear and whether to go out at all."),
              ("snapport", "Passport and visa photos before you travel."),
              ("gmoney", "Track spending in the local currency.")],
             [("Do these work abroad without data?", "The core planning features work offline."),
              ("Is a subscription required?", "No.")]),
        ]),
        "seasonal-gifting": ("gifting", "gifting", [
            ("gift-an-app",
             f"Giving an App as a Gift — iPhone {cn} 2026",
             "What actually makes a good app gift, and what does not.",
             f"Giving an iPhone App as a Gift ({cn} 2026)",
             "A subscription is a bill you hand someone; a paid download is a gift. The App Store can only gift paid apps, so that is what this list contains.",
             [("wordmate", "Vocabulary in 44 languages for a language learner."),
              ("tripbee", "An offline trip planner for someone with a journey coming up."),
              ("gmoney", "Spending and currency tracking for a frequent traveller."),
              ("snapport", "Passport and ID photos at home, for the household organiser.")],
             [("Can I gift these on the App Store?", "The App Store gift option is available on paid apps; these are paid downloads, so the option appears on their listings."),
              ("Will they be charged later?", "No. These are paid downloads, not subscriptions.")]),
            ("new-iphone-setup",
             f"First Apps for a New iPhone — {cn} 2026",
             "What to install in the first hour of a new phone.",
             f"New iPhone: What to Install First ({cn} 2026)",
             "Set up the boring, useful things once and you will not think about them again.",
             [("scanto", "Somewhere for paperwork to go."),
              ("picclear", "Start clean instead of importing years of duplicates."),
              ("wifiaid", "For the day the new phone will not connect."),
              ("mochi", "The handful of recurring things you keep forgetting.")],
             [("Do these need a subscription?", "No."),
              ("Do they need an account?", "No.")]),
            ("new-year-reset",
             f"New Year Reset on iPhone — {cn} 2026",
             "Clear the backlog: photos, paperwork, money and habits.",
             f"New Year iPhone Reset ({cn} 2026)",
             "Four passes, an evening each, and the phone stops being a source of low-level dread.",
             [("picclear", "Photos: clear duplicates and rejects."),
              ("scanto", "Paperwork: one searchable archive."),
              ("gmoney", "Money: see where it actually went."),
              ("mochi", "Habits: a short list you will keep.")],
             [("Does any of this need the cloud?", "No."),
              ("Is there a monthly fee?", "No.")]),
            ("exam-and-application-season",
             f"Exam and Application Season on iPhone — {cn} 2026",
             "Test prep, documents and the photo the form asks for.",
             f"Exam and Application Season ({cn} 2026)",
             "Applications fail on the small things: the wrong photo size, an unreadable scan, a CV that will not export.",
             [("aim990", "Listening and reading practice, offline."),
              ("cvdesk", "Build and export a CV."),
              ("snapport", "The ID photo in the size the form demands."),
              ("scanto", "Scan certificates into one clean PDF.")],
             [("Do these need an account?", "No."),
              ("Do they work offline?", "The core features listed here do.")]),
        ]),
        "switching": ("switching", "switching", [
            ("cancel-a-photo-subscription",
             f"Cancelling a Photo App Subscription — iPhone {cn} 2026",
             "What to replace a monthly photo editor with.",
             f"Leaving a Photo Subscription ({cn} 2026)",
             "Most people pay monthly for two or three features they use. Work out which ones, then replace only those.",
             [("unblurry", "If you subscribed for sharpening and rescue."),
              ("picclear", "If you subscribed for library cleanup."),
              ("photocream", "If you subscribed for looks and presets."),
              ("snapport", "If you subscribed for ID and passport sizing.")],
             [("Do I lose my edits when I cancel?", "Export anything you need before your period ends; that is on the app you are leaving."),
              ("Are these subscriptions too?", "No.")]),
            ("cancel-a-scanner-subscription",
             f"Cancelling a PDF Scanner Subscription — iPhone {cn} 2026",
             "Scanner apps are the most aggressive upsell on the App Store.",
             f"Leaving a Scanner Subscription ({cn} 2026)",
             "Scanning is a solved problem. Paying every month for it is a pricing decision, not a technical one.",
             [("scanto", "Offline scanning to PDF with on-device OCR."),
              ("maskmyfile", "If you also needed to hide details before sending."),
              ("aibriefpack", "If you were really collecting material to summarise.")],
             [("Will my old scans still open?", "They are PDFs; any reader opens them."),
              ("Does this one upload my documents?", "No. It works on device.")]),
            ("cancel-a-language-subscription",
             f"Cancelling a Language App Subscription — iPhone {cn} 2026",
             "When a streak stops being learning.",
             f"Leaving a Language Subscription ({cn} 2026)",
             "If you are travelling next month, sentences beat streaks. If you are building vocabulary, spaced practice beats gems.",
             [("dailymate", "Complete sentences for real travel situations."),
              ("dailymatelite", "The same approach, free to start."),
              ("wordmate", "Vocabulary in 44 languages with natural examples."),
              ("aim990", "If the real goal is an English exam score.")],
             [("Do I keep my progress from the old app?", "No — progress does not transfer between apps."),
              ("Is there a monthly fee here?", "No.")]),
            ("cancel-a-trip-planner-subscription",
             f"Cancelling a Trip Planner Subscription — iPhone {cn} 2026",
             "You travel a few times a year. The bill arrives every month.",
             f"Leaving a Trip Planner Subscription ({cn} 2026)",
             "Annual plans make sense for people who travel constantly. For everyone else the maths does not work.",
             [("tripbee", "Day-by-day offline planning and packing lists."),
              ("tripbeelite", "One upcoming trip, free to start."),
              ("gmoney", "Spending and currency while you are there."),
              ("snapport", "Visa and passport photos before you go.")],
             [("Can I export my old itinerary?", "Export from the app you are leaving before the period ends."),
              ("Do these work offline?", "The core planning features do.")]),
        ]),
        "lite-vs-pro": ("choose", "choose", [
            ("free-version-or-paid-version",
             f"Free Version or Paid Version — iPhone {cn} 2026",
             "How to tell which one you actually need.",
             f"Free Version or Paid Version ({cn} 2026)",
             "A free version exists so you can find out whether the app suits you before paying. Use it that way: try first, unlock only if you keep opening it.",
             [("snapportlite", "Try guided ID photo sizing before unlocking the full version."),
              ("tripbeelite", "Plan one upcoming trip before committing."),
              ("gmoneylite", "Log a few days of spending first."),
              ("hourstaglite", "See a few purchases in work hours first.")],
             [("Is the free version time-limited?", "These are free to download with an optional one-time unlock; check each listing for what the unlock adds."),
              ("Do I lose my data when I unlock?", "No.")]),
            ("which-photo-app-do-i-need",
             f"Which iPhone Photo App Do I Need — {cn} 2026",
             "Sharpen, clean up, restyle or resize — four different jobs.",
             f"Which Photo App Do I Need ({cn} 2026)",
             "Photo apps look interchangeable and are not. Match the app to the job and you stop buying the wrong one.",
             [("unblurry", "The photo is soft and you need the detail back."),
              ("picclear", "The library is full and you need space."),
              ("photocream", "The photo is fine and you want a look."),
              ("snapport", "The photo has to meet an official size.")],
             [("Can one app do all four?", "In practice each of these is built for one of the jobs."),
              ("Do they need an account?", "No.")]),
            ("which-money-app-do-i-need",
             f"Which iPhone Money App Do I Need — {cn} 2026",
             "Tracking a trip, tracking a habit, or tracking a budget.",
             f"Which Money App Do I Need ({cn} 2026)",
             "Budget apps fail because they answer a question you were not asking. Pick by the question.",
             [("gmoney", "You are travelling and spending in another currency."),
              ("gmoneylite", "Same, free to start."),
              ("hourstag", "You want to feel a price before you pay it."),
              ("hourstaglite", "Same, free to start.")],
             [("Do these connect to my bank?", "No. You record what you spend."),
              ("Is there a subscription?", "No.")]),
            ("which-study-app-do-i-need",
             f"Which iPhone Study App Do I Need — {cn} 2026",
             "Exam score, vocabulary, or a child learning to read.",
             f"Which Study App Do I Need ({cn} 2026)",
             "Three different learners, three different apps. Buying the wrong one is why people quit.",
             [("aim990", "An adult preparing for an English listening and reading exam."),
              ("wordmate", "Someone building vocabulary across languages."),
              ("lumiletters", "A child learning English letters and sounds."),
              ("lumibopomofo", "A child learning Bopomofo.")],
             [("Are the kids' apps ad-free?", "Yes, no ads."),
              ("Is the artwork hand-drawn?", "No. The artwork is AI-generated and the speech uses system text-to-speech.")]),
        ]),
    }


def gen_cluster(cluster_id, row):
    """Generate one query-cluster for one language. Returns pages written."""
    lang, cn, pl, ph, doc, back, dl, faq_l = row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
    APPS, APPSTORE = _apps()
    subdir, sm_key, pages = _cluster_defs(cn, pl, ph, doc)[cluster_id]
    l10n = _cluster_l10n(cluster_id).get(lang, {})
    pricing = dict(PRICING_LINE)
    pricing.update(_pricing_l10n().get(lang, {}))
    out = PAGES / lang / subdir
    out.mkdir(parents=True, exist_ok=True)
    slugs = []
    for slug_s, title, desc, h1, intro, items_raw, faqs in pages:
        loc = l10n.get(slug_s)
        if loc:
            # Fully localized body copy for a real storefront locale.
            title, desc, h1, intro = loc["title"], loc["desc"], loc["h1"], loc["intro"]
            faqs = loc["faqs"]
            items_raw = [(k, loc["why"].get(k, w)) for k, w in items_raw]
        ih = ""
        li = []
        pos = 1
        for key, why in items_raw:
            app = APPS.get(key)
            aid = APPSTORE.get(key, "")
            if not app or not aid:
                continue  # never link an app that is not public
            name = app.get("name", key)
            price = pricing.get(app.get("purchase_model"), "")
            url = f"https://apps.apple.com/app/id{aid}?ct=iag_{sm_key}_{lang}"
            ih += (f'<div class="item"><h3>{pos}. {name}</h3><p>{why}</p>'
                   f'<p class="muted">{price}</p>'
                   f'<a href="{url}" class="dl" rel="noopener">{dl}</a></div>\n')
            li.append({"@type": "ListItem", "position": pos, "name": name, "url": url})
            pos += 1
        if not li:
            continue
        slug = f"{slug_s}-{lang.lower()}"
        ld = json.dumps([
            {"@context": "https://schema.org", "@type": "ItemList", "name": title, "itemListElement": li},
            {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": _fl(faqs)},
        ], ensure_ascii=False)
        rtl = ' dir="rtl"' if lang.split("-")[0] in {"ar", "he", "fa", "ur", "ckb", "lrc", "haz", "bqi", "glk", "mzn", "luz"} else ""
        html = (f'<!DOCTYPE html>\n<html lang="{lang}"{rtl}>\n<head><meta charset="utf-8">'
                f'<title>{title}</title><meta name="description" content="{desc}">'
                f'<meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{GEO_SITE}/{lang}/{subdir}/{slug}.html">'
                f'<style>{B}.muted{{color:#666;font-size:.85rem;margin:.2rem 0 0}}</style>'
                f'<script type="application/ld+json">{ld}</script></head>\n'
                f'<body><p><a href="{GEO_SITE}/{lang}/">{back}</a></p><h1>{h1}</h1><p>{intro}</p>{ih}'
                f'<h2>{faq_l}</h2>{_fh(faqs)}</body></html>')
        (out / f"{slug}.html").write_text(html, encoding="utf-8")
        slugs.append(slug)
    if slugs:
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sm += "\n".join(f'<url><loc>{GEO_SITE}/{lang}/{subdir}/{s}.html</loc></url>' for s in slugs) + "\n</urlset>\n"
        (PAGES / f"sitemap_{sm_key}_{lang}.xml").write_text(sm, encoding="utf-8")
    return len(slugs)


def gen_lang(lang, cn, pl, ph, doc, back, dl, faq_l, verdict_l, pros_l, cons_l, wfl, wnotl, devnote):
    APPS, APPSTORE = _apps()
    defs = [
        ("bf","best-for","bestfor",[
            ("photo-hide",f"Best iPhone App to Hide Photos — {cn} 2026",f"Photo privacy.",f"Best App to Hide Photos iPhone ({cn} 2026)","Real privacy?",[("maskmyfile","Mask private details before sharing. On device."),("picclear","Clear the shots you did not mean to keep.")],[("Secure?","Yes, AES."),("iCloud?","Never.")]),
            ("scan-offline",f"Best Offline Scanner — iPhone {cn} 2026","PDF offline.",f"Best Offline Scanner iPhone ({cn} 2026)","No internet.",[("scanto",f"Local PDF. {ph} one-time.")],[("Internet?","No."),("Uploads?","Never.")]),
            ("passport-photo",f"Best Passport Photo App — iPhone {cn} 2026","Photo at home.",f"Best Passport Photo App iPhone ({cn} 2026)","No photographer.",[("snapport",f"Auto crop. {pl}.")],[("Specs?","Yes."),("Guarantee?","Yes.")]),
            ("social-block",f"Best App to Block Social Media — iPhone {cn} 2026","Productivity.",f"Block Social Media iPhone ({cn} 2026)","More focus?",[("lockhour","Set aside blocks of time for focused work."),("mochi","Keep the day's tasks small and visible.")],[("Screen Time?","Yes."),("WhatsApp?","Screen Time.")]),
            ("document-mask",f"Best App to Mask Document Data — iPhone {cn} 2026",f"Redact {doc}.",f"Mask Document Data iPhone ({cn} 2026)",f"Protect {doc}?",[("maskmyfile",f"Permanent. {pl}.")],[("Edits original?","No."),("Server?","No.")])
        ]),
        ("wf","workflow","workflow",[
            ("freelancer",f"iPhone Workflow for Freelancers — {cn} 2026","Offline-first.",f"Freelancer iPhone Workflow ({cn} 2026)","No cloud.",[("ScanTo Pro","Scan contracts."),("MaskMyFile",f"Redact {doc}."),("HoursTag","Track hours.")],[("Offline?","Yes."),("Coding?","No.")]),
            ("privacy",f"iPhone Privacy Setup — {cn} 2026","3 apps.",f"iPhone Privacy Guide ({cn} 2026)","Lock your data.",[("Zafe","Lock photos."),("MaskMyFile","Redact."),("ScanTo Pro","Scan offline.")],[("Sends data?","No."),("Android?","iOS only.")]),
            ("student",f"iPhone Toolkit for Students — {cn} 2026","Study tools.",f"Student iPhone Toolkit ({cn} 2026)","Study smarter.",[("ScanTo Pro","Scan notes."),("Zafe",f"Store {doc}."),("Snapport","Passport photo.")],[("iPad?","Yes."),("Price?",pl)])
        ]),
        ("vs","vs","vs",[
            ("zafe-vs-hidden-album",f"Zafe vs Hidden Album — {cn} 2026","Real vs basic.",f"Zafe vs Hidden Album ({cn})",[("Encryption","AES + Face ID","None"),("Price",pl,"Free")],"For real security: Zafe.",[("Hidden Album?","No encryption."),("iCloud?","Zafe never.")]),
            ("scanto-vs-apple-notes",f"ScanTo Pro vs Apple Notes — {cn} 2026","Offline vs cloud.",f"ScanTo Pro vs Apple Notes ({cn})",[("Cloud","Never","iCloud"),("Price",ph,"Free")],"For privacy: ScanTo Pro.",[("iCloud?","Notes uses it."),("OCR?","Both.")]),
            ("snapport-vs-photographer",f"Snapport vs Photographer — {cn} 2026","Home vs studio.",f"Snapport vs Photographer ({cn})",[("Cost",f"{pl}+guarantee","Studio"),("At home?","Yes","No")],"For most: Snapport.",[("Specs?","Yes."),("One-time?",pl)])
        ]),
        ("sea","seasonal","seasonal",[
            ("school",f"Back to School iPhone Apps — {cn} 2026","School apps.",f"Back to School iPhone Apps ({cn} 2026)","New year.",[("scanto","Scan notes."),("snapport","Student photo."),("aibriefpack",f"Turn {doc} into one clear brief.")],[("Coding?","No."),("Kids?","Yes.")]),
            ("year-end",f"Year-End iPhone Apps — {cn} 2026","Year-end docs.",f"Year-End iPhone Apps ({cn} 2026)","Organise.",[("maskmyfile","Redact."),("scanto","Scan."),("cvdesk","Refresh your CV.")],[("Cloud?","No."),("Start?","ScanTo Pro.")]),
            ("summer",f"Travel iPhone Apps — {cn} 2026","Travel.",f"Travel iPhone Apps ({cn} 2026)","Enjoy!",[("snapport","Passport photo."),("tripbee","Offline day-by-day plan."),("scanto","Travel docs.")],[("Internet?","No."),("Abroad?","Yes.")])
        ]),
    ]
    total = 0
    for pt, subdir, sk, items in defs:
        out = PAGES / lang / subdir; out.mkdir(parents=True, exist_ok=True)
        slugs = []
        for item in items:
            if pt == "bf":
                slug_s, title, desc, h1, intro, items_raw, faqs = item
                slug = f"iphone-best-app-{slug_s}-{lang.lower()}"
                ih=""; li=[]; pos=1
                for key, why in items_raw:
                    app=APPS.get(key,{}); aid=APPSTORE.get(key,""); name=app.get("name",key)
                    if not aid: continue  # never emit a dead link for a non-public app
                    url=f"https://apps.apple.com/app/id{aid}?ct=iag_bf_{lang}"
                    ih+=f'<div class="item"><h3>{pos}. {name}</h3><p>{why}</p><a href="{url}" class="dl" rel="noopener">{dl}</a></div>\n'
                    li.append({"@type":"ListItem","position":pos,"name":name,"url":url}); pos+=1
                ld=json.dumps([{"@context":"https://schema.org","@type":"ItemList","name":title,"itemListElement":li},{"@context":"https://schema.org","@type":"FAQPage","mainEntity":_fl(faqs)}],ensure_ascii=False)
                html=f'<!DOCTYPE html>\n<html lang="{lang}">\n<head><meta charset="utf-8"><title>{title}</title><meta name="description" content="{desc}"><meta name="robots" content="index,follow"><link rel="canonical" href="{GEO_SITE}/{lang}/best-for/{slug}.html"><style>{B}</style><script type="application/ld+json">{ld}</script></head>\n<body><p><a href="{GEO_SITE}/{lang}/">{back}</a></p><h1>{h1}</h1><p>{intro}</p>{ih}<h2>{faq_l}</h2>{_fh(faqs)}</body></html>'
            elif pt == "wf":
                slug_s, title, desc, h1, intro, steps, faqs = item
                slug = f"iphone-{'privacy' if slug_s=='privacy' else 'workflow-'+slug_s}-{lang.lower()}"
                sh="<ol>"+"".join(f"<li><strong>{n}</strong> — {d}</li>" for n,d in steps)+"</ol>"
                sl=[{"@type":"HowToStep","position":i+1,"name":n,"text":d} for i,(n,d) in enumerate(steps)]
                ld=json.dumps([{"@context":"https://schema.org","@type":"HowTo","name":title,"step":sl},{"@context":"https://schema.org","@type":"FAQPage","mainEntity":_fl(faqs)}],ensure_ascii=False)
                html=f'<!DOCTYPE html>\n<html lang="{lang}">\n<head><meta charset="utf-8"><title>{title}</title><meta name="description" content="{desc}"><meta name="robots" content="index,follow"><link rel="canonical" href="{GEO_SITE}/{lang}/workflow/{slug}.html"><style>{S}</style><script type="application/ld+json">{ld}</script></head>\n<body><p><a href="{GEO_SITE}/{lang}/">{back}</a></p><h1>{h1}</h1><p>{intro}</p>{sh}<h2>{faq_l}</h2>{_fh(faqs)}</body></html>'
            elif pt == "vs":
                slug_s, title, desc, h1, rows, verdict, faqs = item
                slug = f"{slug_s}-{lang.lower()}"
                rh="".join(f"<tr><td>{f}</td><td>{a}</td><td>{b}</td></tr>" for f,a,b in rows)
                ld=json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":_fl(faqs)},ensure_ascii=False)
                html=f'<!DOCTYPE html>\n<html lang="{lang}">\n<head><meta charset="utf-8"><title>{title}</title><meta name="description" content="{desc}"><meta name="robots" content="index,follow"><link rel="canonical" href="{GEO_SITE}/{lang}/vs/{slug}.html"><style>{V}</style><script type="application/ld+json">{ld}</script></head>\n<body><p><a href="{GEO_SITE}/{lang}/">{back}</a></p><h1>{h1}</h1><table><tr><th></th><th>A</th><th>B</th></tr>{rh}</table><p><strong>{verdict_l}</strong> {verdict}</p><h2>{faq_l}</h2>{_fh(faqs)}</body></html>'
            elif pt == "sea":
                slug_s, title, desc, h1, intro, items_raw, faqs = item
                slug = f"iphone-apps-{slug_s}-{lang.lower()}"
                ih=""; li=[]; pos=1
                for key, why in items_raw:
                    app=APPS.get(key,{}); aid=APPSTORE.get(key,""); name=app.get("name",key)
                    if not aid: continue  # never emit a dead link for a non-public app
                    url=f"https://apps.apple.com/app/id{aid}?ct=iag_seasonal_{lang}"
                    ih+=f'<div class="item"><h3>{pos}. {name}</h3><p>{why}</p><a href="{url}" class="dl" rel="noopener">{dl}</a></div>\n'
                    li.append({"@type":"ListItem","position":pos,"name":name,"url":url}); pos+=1
                ld=json.dumps([{"@context":"https://schema.org","@type":"ItemList","name":title,"itemListElement":li},{"@context":"https://schema.org","@type":"FAQPage","mainEntity":_fl(faqs)}],ensure_ascii=False)
                html=f'<!DOCTYPE html>\n<html lang="{lang}">\n<head><meta charset="utf-8"><title>{title}</title><meta name="description" content="{desc}"><meta name="robots" content="index,follow"><link rel="canonical" href="{GEO_SITE}/{lang}/seasonal/{slug}.html"><style>{B}</style><script type="application/ld+json">{ld}</script></head>\n<body><p><a href="{GEO_SITE}/{lang}/">{back}</a></p><h1>{h1}</h1><p>{intro}</p>{ih}<h2>{faq_l}</h2>{_fh(faqs)}</body></html>'
            (out / f"{slug}.html").write_text(html, encoding="utf-8")
            slugs.append(slug); total += 1
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sm += "\n".join(f'<url><loc>{GEO_SITE}/{lang}/{subdir}/{s}.html</loc></url>' for s in slugs) + "\n</urlset>\n"
        (PAGES / f"sitemap_{sk}_{lang}.xml").write_text(sm, encoding="utf-8")
    # Review pages
    rev_out = PAGES / lang / "reviews"; rev_out.mkdir(parents=True, exist_ok=True)
    rev_slugs = []
    for key, short_pl, short_ph in [("scanto",ph,ph),("snapport",pl,pl),("maskmyfile",pl,pl),("wifiaid",pl,pl)]:
        app=APPS.get(key,{}); aid=APPSTORE.get(key,""); name=app.get("name",key)
        if not aid: continue
        slug=f"{key}-review-2026-{lang.lower()}"
        su=f"https://apps.apple.com/app/id{aid}?ct=iag_review_{lang}" if aid else "#"
        stars="★★★★☆"
        pros_h=f"<li>{short_pl} one-time</li><li>Face ID / AES</li><li>Offline</li>"
        cons_h="<li>No cloud sync</li>"
        # 不輸出 Review/ratingValue:發行商自評星等在機器可讀端像第三方評分,
        # 違反 Google review snippet 政策(風險是全網域手動處分)。
        ld=json.dumps([{"@context":"https://schema.org","@type":"FAQPage","mainEntity":_fl([("Secure?","Yes."),("One-time?",short_pl)])}],ensure_ascii=False)
        html=f'<!DOCTYPE html>\n<html lang="{lang}">\n<head><meta charset="utf-8"><title>{name} Review 2026 — {cn}</title><meta name="description" content="Review."><meta name="robots" content="index,follow"><link rel="canonical" href="{GEO_SITE}/{lang}/reviews/{slug}.html"><style>{R}</style><script type="application/ld+json">{ld}</script></head>\n<body><p><a href="{GEO_SITE}/{lang}/">{back}</a></p><h1>{name} Review ({cn} 2026)</h1><div class="stars">{stars}</div><p><strong>{verdict_l}</strong> Best {key} app. {short_pl}.</p><div class="disclaimer">{devnote}</div><h2>{pros_l}</h2><ul class="pros">{pros_h}</ul><h2>{cons_l}</h2><ul class="cons">{cons_h}</ul><h2>{wfl}</h2><p>Privacy seekers.</p><a href="{su}" class="dl" rel="noopener">{dl}</a></body></html>'
        (rev_out / f"{slug}.html").write_text(html, encoding="utf-8")
        rev_slugs.append(slug); total += 1
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "\n".join(f'<url><loc>{GEO_SITE}/{lang}/reviews/{s}.html</loc></url>' for s in rev_slugs) + "\n</urlset>\n"
    (PAGES / f"sitemap_reviews_{lang}.xml").write_text(sm, encoding="utf-8")
    return total

def register_sitemaps(langs):
    """Append new lang sitemaps to gen_llms.py at both registration points."""
    llms = HERE / "gen_llms.py"
    txt = llms.read_text(encoding="utf-8")
    for lang in langs:
        entry = f'        "sitemap_bestfor_{lang}.xml", "sitemap_workflow_{lang}.xml", "sitemap_vs_{lang}.xml",\n        "sitemap_seasonal_{lang}.xml", "sitemap_reviews_{lang}.xml",\n'
        if f"sitemap_reviews_{lang}.xml" in txt:
            continue
        # Location 1: insert before ):
        txt = txt.replace(
            '    ):\n        if os.path.exists(os.path.join(PAGES, filename)):',
            entry + '    ):\n        if os.path.exists(os.path.join(PAGES, filename)):',
            1
        )
        # Location 3: insert before ])  (note: "\\n".join is literal backslash-n in the source)
        txt = txt.replace(
            '    ])\n    items = "\\n".join(f"  <sitemap>',
            entry + '    ])\n    items = "\\n".join(f"  <sitemap>',
            1
        )
    llms.write_text(txt, encoding="utf-8")

def register_cluster_sitemaps(sm_key, langs):
    """Append cluster sitemaps for new langs to gen_llms.py at both registration points."""
    llms = HERE / "gen_llms.py"
    txt = llms.read_text(encoding="utf-8")
    for lang in langs:
        name = f"sitemap_{sm_key}_{lang}.xml"
        if name in txt:
            continue
        entry = f'        "{name}",\n'
        txt = txt.replace(
            '    ):\n        if os.path.exists(os.path.join(PAGES, filename)):',
            entry + '    ):\n        if os.path.exists(os.path.join(PAGES, filename)):',
            1
        )
        txt = txt.replace(
            '    ])\n    items = "\\n".join(f"  <sitemap>',
            entry + '    ])\n    items = "\\n".join(f"  <sitemap>',
            1
        )
    llms.write_text(txt, encoding="utf-8")


def run_cluster_pass(batch_size):
    """Second work axis: apply each query cluster to languages that lack it."""
    for cluster_id in CLUSTER_ORDER:
        subdir = _cluster_defs("x", "x", "x", "x")[cluster_id][0]
        sm_key = _cluster_defs("x", "x", "x", "x")[cluster_id][1]
        todo = []
        for row in MAJOR_LOCALES + CANDIDATE_POOL:
            lang = row[0]
            if not (PAGES / lang / "best-for").is_dir():
                continue  # base language pages must exist first
            if any((PAGES / lang / subdir).glob("*.html")):
                continue
            todo.append(row)
            if len(todo) >= batch_size:
                break
        if not todo:
            continue
        done, total = [], 0
        for row in todo:
            try:
                n = gen_cluster(cluster_id, row)
                if n:
                    done.append(row[0])
                    total += n
                    logging.info(f"Cluster {cluster_id}: {n} pages for {row[0]} ({row[1]})")
            except Exception as e:
                logging.error(f"Cluster {cluster_id} failed {row[0]}: {e}")
        if not done:
            continue
        register_cluster_sitemaps(sm_key, done)
        run_generators()
        pub = next_pub_num()
        msg = git_commit_push([f"{cluster_id}:{l}" for l in done], pub, total, lang_dirs=done)
        logging.info(f"Committed pub {pub}: {msg} ({total} pages)")
        log = HERE.parent / "agent" / "auto_loop_log.md"
        if log.exists():
            log.write_text(
                log.read_text().rstrip()
                + f"\n| {pub} | auto | auto-batch cluster {cluster_id} | {'/'.join(done)} | {total} |\n"
            )
        print(json.dumps({"pub": pub, "cluster": cluster_id, "langs": done, "pages": total}))
        return True
    return False


def update_hub_langs(langs_dict):
    """Add to LANG_NAMES in both hub generators."""
    for hub_file in [HERE / "gen_topic_hubs.py", HERE / "gen_review_hubs.py"]:
        txt = hub_file.read_text(encoding="utf-8")
        new_entries = ", ".join(f'"{k}": "{v}"' for k,v in langs_dict.items() if f'"{k}"' not in txt)
        if new_entries:
            txt = txt.replace("\n}", f"\n    {new_entries},\n}}", 1)
            hub_file.write_text(txt, encoding="utf-8")

def run_generators():
    for script in ["gen_llms.py", "gen_topic_hubs.py", "gen_review_hubs.py"]:
        subprocess.run([PYTHON, str(HERE / script)], capture_output=True, cwd=str(HERE.parent))

# Files this runner (and the generators it invokes) owns. Everything else in the
# pages repo belongs to another worker or schedule — staging it with `add -A`
# silently published their half-finished edits under our commit message.
OWNED_PATHS = [
    "llms.txt", "llms-full.txt", "robots.txt", "sitemap_index.xml",
    "sitemap_topic_hubs.xml", "sitemap_review_hubs.xml",
    "topic-hubs", "review-hubs",
]


def git_commit_push(langs, pub_num, pages=None, lang_dirs=None):
    count = pages if pages is not None else len(langs) * 18
    msg = f"pub {pub_num}: auto-batch {'/'.join(langs)} {count} pages"
    paths = list(OWNED_PATHS)
    for lang in (lang_dirs or []):
        paths.append(lang)
        paths.extend(
            p.name for p in PAGES.glob(f"sitemap_*_{lang}.xml")
        )
    paths = [p for p in paths if (PAGES / p).exists()]

    def _git(*args, retries=6):
        """Run git, retrying while another worker holds index.lock."""
        for attempt in range(retries):
            r = subprocess.run(
                ["git", "-C", str(PAGES), *args],
                capture_output=True, text=True,
            )
            if "index.lock" not in (r.stderr or ""):
                return r
            logging.info(
                f"git {args[0]}: index.lock held by another worker, "
                f"retry {attempt + 1}/{retries}"
            )
            time.sleep(20)
        logging.error(f"git {args[0]} gave up: index.lock never cleared")
        return r

    _git("add", "--", *paths)
    _git("commit", "-m", msg)
    _git("pull", "--rebase", "--autostash", "-X", "theirs")
    _git("push", "origin", "HEAD")
    return msg

def next_pub_num():
    log = HERE.parent / "agent" / "auto_loop_log.md"
    if not log.exists(): return 95
    lines = [l for l in log.read_text().splitlines() if l.startswith("|") and l.split("|")[1].strip().isdigit()]
    if not lines: return 95
    return int(lines[-1].split("|")[1].strip()) + 1

def main():
    # 2026-08-08: measurement (W9) showed 59,567 pages produced 18 downloads and
    # US$0.00 in 30 days, with 66.8% of localized pages carrying byte-identical
    # English <title>/meta description. Producing more English copies under
    # localized paths has an expected value of zero, so new-page generation is
    # off until pages are demonstrably indexed. Set GEO_AUTOBATCH=on to resume.
    if os.getenv("GEO_AUTOBATCH", "paused").lower() not in {"on", "1", "true"}:
        logging.info(
            "New-page generation paused (GEO_AUTOBATCH != on); "
            "duplicate-metadata remediation takes priority."
        )
        return
    batch_size = int(os.getenv("GEO_BATCH_SIZE", "5"))
    # Find candidates not yet covered
    todo = []
    for row in CANDIDATE_POOL:
        lang = row[0]
        if not any((PAGES / lang / "best-for").glob("*.html")):
            todo.append(row)
        if len(todo) >= batch_size:
            break

    if not todo:
        # Language axis saturated → fall through to the query-cluster axis.
        if run_cluster_pass(batch_size):
            return
        logging.info("No new language candidates and no cluster work left — pool exhausted.")
        return

    langs_done = []
    langs_dict = {}
    total_pages = 0
    for row in todo:
        lang = row[0]
        cn = row[1]
        try:
            n = gen_lang(*row)
            langs_done.append(lang)
            langs_dict[lang] = cn
            total_pages += n
            logging.info(f"Generated {n} pages for {lang} ({cn})")
        except Exception as e:
            logging.error(f"Failed {lang}: {e}")

    if not langs_done:
        logging.error("All candidates failed generation.")
        return

    register_sitemaps(langs_done)
    update_hub_langs(langs_dict)
    run_generators()
    pub = next_pub_num()
    msg = git_commit_push(langs_done, pub, total_pages, lang_dirs=langs_done)
    logging.info(f"Committed pub {pub}: {msg} ({total_pages} pages)")
    # Update log
    log = HERE.parent / "agent" / "auto_loop_log.md"
    if log.exists():
        entry = f"| {pub} | auto | auto-batch | {'/'.join(langs_done)} | {total_pages} |\n"
        txt = log.read_text()
        # append before last hub stats line or at end
        log.write_text(txt.rstrip() + "\n" + entry)
    print(json.dumps({"pub": pub, "langs": langs_done, "pages": total_pages}))

if __name__ == "__main__":
    main()

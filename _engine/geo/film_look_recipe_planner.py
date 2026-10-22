#!/usr/bin/env python3
"""Generate a nine-locale, private film-look recipe planning tool."""

from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
SLUG = "private-film-look-recipe-planner"
APP_KEY = "photocream"
APP_ID = "6781808054"
CONTENT_DATE = "2026-07-16"
APPLE_EDIT_PHOTOS = (
    "https://support.apple.com/guide/iphone/"
    "edit-photos-and-videos-iphb08064d57/ios"
)
APPLE_REVERT_PHOTOS = (
    "https://support.apple.com/guide/iphone/"
    "undo-and-revert-photo-edits-iph2413db0ab/ios"
)
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

MOODS = (
    "clean-film",
    "warm-35mm",
    "cool-cinema",
    "disposable-flash",
    "faded-vintage",
)
LIGHTING = ("bright", "balanced", "low-light")
GRAIN = ("none", "subtle", "visible")
COLOR = ("neutral", "warm", "cool")
OUTPUTS = ("single", "series", "print")
ALT_LOCALES = (
    "en",
    "es-ES",
    "pt-BR",
    "de-DE",
    "fr-FR",
    "ja",
    "ko",
    "zh-Hant",
    "zh-Hans",
    "vi",
    "th",
    "id",
    "tr",
    "hi",
    "ms",
    "ru",
    "uk",
    "pl",
    "ta-IN",
)


def _copy(
    *,
    meta: tuple[str, ...],
    badges: tuple[str, ...],
    planner: tuple[str, str],
    labels: tuple[str, ...],
    options: tuple[tuple[str, ...], ...],
    natural: tuple[str, str, str],
    results: tuple[str, ...],
    notes: tuple[tuple[str, ...], ...],
    boundary: str,
    review: tuple[str, ...],
    sources: tuple[str, str, str, str],
    webmcp: tuple[str, str],
    app: tuple[str, str, str],
    faq: tuple[str, tuple[tuple[str, str], ...]],
    footer: str,
    inline: str,
    index: tuple[str, str],
) -> dict[str, object]:
    (
        title,
        description,
        tools,
        switch,
        eyebrow,
        heading,
        lead,
    ) = meta
    (
        mood_label,
        lighting_label,
        grain_label,
        color_label,
        output_label,
    ) = labels
    return {
        "title": title,
        "description": description,
        "tools": tools,
        "switch": switch,
        "eyebrow": eyebrow,
        "heading": heading,
        "lead": lead,
        "badges": badges,
        "planner": planner[0],
        "planner_intro": planner[1],
        "mood_label": mood_label,
        "lighting_label": lighting_label,
        "grain_label": grain_label,
        "color_label": color_label,
        "output_label": output_label,
        "mood_options": dict(zip(MOODS, options[0], strict=True)),
        "lighting_options": dict(zip(LIGHTING, options[1], strict=True)),
        "grain_options": dict(zip(GRAIN, options[2], strict=True)),
        "color_options": dict(zip(COLOR, options[3], strict=True)),
        "output_options": dict(zip(OUTPUTS, options[4], strict=True)),
        "natural_label": natural[0],
        "natural_yes": natural[1],
        "natural_no": natural[2],
        "update": results[0],
        "result_direction": results[1],
        "result_sequence": results[2],
        "result_consistency": results[3],
        "result_boundary": results[4],
        "mood_notes": dict(zip(MOODS, notes[0], strict=True)),
        "lighting_notes": dict(zip(LIGHTING, notes[1], strict=True)),
        "grain_notes": dict(zip(GRAIN, notes[2], strict=True)),
        "color_notes": dict(zip(COLOR, notes[3], strict=True)),
        "output_notes": dict(zip(OUTPUTS, notes[4], strict=True)),
        "boundary": boundary,
        "review_title": review[0],
        "review_steps": review[1:],
        "sources_title": sources[0],
        "sources_intro": sources[1],
        "source_labels": sources[2:],
        "webmcp_source": webmcp[0],
        "webmcp_description": webmcp[1],
        "app_title": app[0],
        "app_text": app[1],
        "app_cta": app[2],
        "faq_title": faq[0],
        "faq": faq[1],
        "footer": footer,
        "inline_link": inline,
        "index_title": index[0],
        "index_description": index[1],
    }


COPY = {
    "en": _copy(
        meta=(
            "Private Film-Look Recipe Planner | No Photo Upload",
            "Turn bounded style preferences into a reversible editing order without uploading, scanning, analysing or storing a photo.",
            "Free tools",
            "繁體中文",
            "Free · no photo input · no result promise",
            "Private film-look recipe planner",
            "Choose a visual direction, lighting condition and finishing preference. The page returns a starting order, never an exact preset or guaranteed result.",
        ),
        badges=(
            "No photo, file or metadata",
            "No camera, library or account access",
            "No upload, storage or analysis",
            "No quality or outcome guarantee",
        ),
        planner=(
            "Build a reversible starting recipe",
            "The suggestions are qualitative and depend on the source image, display, editor and final size. Preview each change and preserve an original.",
        ),
        labels=(
            "Visual direction",
            "Source lighting",
            "Grain preference",
            "Color direction",
            "Final use",
        ),
        options=(
            (
                "Clean film",
                "Warm 35mm",
                "Cool cinema",
                "Disposable flash",
                "Faded vintage",
            ),
            ("Bright scene", "Balanced light", "Low light"),
            ("No added grain", "Subtle grain", "Visible grain"),
            ("Neutral", "Warmer", "Cooler"),
            ("Single photo", "Matching series", "Print"),
        ),
        natural=(
            "Keep skin tones natural when people are present",
            "If people are present, compare skin, eyes and hair before and after every color step.",
            "No face-specific preference selected; still check people and important color references before export.",
        ),
        results=(
            "Create private recipe",
            "Starting direction",
            "Adjustment order",
            "Consistency check",
            "Recipe boundary",
        ),
        notes=(
            (
                "Keep contrast restrained, color balanced and highlights gentle; add stylisation only after the base looks stable.",
                "Favor warm midtones, moderate contrast and soft highlights; watch oranges and skin before adding effects.",
                "Keep highlights controlled, cool shadows slightly and avoid turning neutral objects blue.",
                "Preserve direct-flash brightness and crisp central contrast; add edge falloff only after checking faces and text.",
                "Lift the darkest tones gently, reduce hard contrast and mute color without washing out important detail.",
            ),
            (
                "Protect bright highlights first and judge whether the lightest areas still retain useful detail.",
                "Set exposure and white balance before mood, grain or decorative effects.",
                "Avoid lifting shadows aggressively; check noise and color blotches at the final viewing size.",
            ),
            (
                "Leave added grain off and use light, color and contrast for the look.",
                "Add fine grain near the end, then inspect smooth skies, skin and text at normal size.",
                "Use deliberate grain only after the base edit; reduce it if faces, small details or print texture become distracting.",
            ),
            (
                "Correct an obvious color cast first, then keep whites and familiar objects believable.",
                "Add warmth gradually and recheck whites, skin and indoor lighting before export.",
                "Cool the image gradually; keep highlights and neutral objects from becoming unnaturally blue.",
            ),
            (
                "Judge the result at its actual viewing size and compare it with the preserved original.",
                "Choose one reference edit, compare the whole sequence and adjust outliers instead of stacking more effects.",
                "Preview the intended crop and print size; screen brightness and added grain can look different on paper.",
            ),
        ),
        boundary=(
            "This is an editing order, not a preset, image analysis or promise of a film stock match. "
            "It cannot see exposure, faces, color, focus, noise, dynamic range or output conditions."
        ),
        review=(
            "Four checks before export",
            "Keep an untouched original or a reversible editing path.",
            "Apply one small change at a time and compare at normal viewing size.",
            "Check highlights, shadows, familiar colors and people before adding texture.",
            "For a series, compare all frames together and correct outliers before export.",
        ),
        sources=(
            "Official Apple editing context, not an endorsement",
            "Apple documents editing photos and videos on iPhone and reverting an edited item to its original. Check the current steps for your iOS version.",
            "Apple: edit photos and videos on iPhone",
            "Apple: undo and revert photo edits on iPhone",
        ),
        webmcp=(
            "Chrome imperative WebMCP API preview",
            "Build a deterministic qualitative editing order from bounded style choices only. Never accept or access photos, files, metadata, cameras, libraries, accounts or free text; never analyse an image or guarantee a result.",
        ),
        app=(
            "Want to preview film looks directly on your device?",
            "PhotoCream Pro is optional. Its current App Store listing describes 100+ looks, grain, halation, light leaks, bloom, vignette, live preview and light/color controls, processed on device with no account or upload. It is free to download with a one-time unlock. Check the current listing for exact availability and features. This planner works without the app.",
            "View PhotoCream Pro on the App Store",
        ),
        faq=(
            "Film-look planning questions",
            (
                (
                    "Does this page receive or inspect my photo?",
                    "No. It accepts only bounded style choices and never receives a photo, file or metadata.",
                ),
                (
                    "Will this recipe recreate a specific film stock?",
                    "No. It provides a starting order and makes no accuracy or outcome claim.",
                ),
                (
                    "Can I undo an edit in Apple Photos?",
                    "Apple documents reverting an edited photo or video to its original; verify the current steps for your iOS version.",
                ),
            ),
        ),
        footer="Bounded preferences only · no photo access · no image analysis · no result promise",
        inline="Plan a private film-look recipe before choosing an editor",
        index=(
            "Private Film-Look Recipe Planner",
            "Choose a film direction and get a reversible editing order without uploading or analysing a photo.",
        ),
    ),
    "es-ES": _copy(
        meta=(
            "Planificador privado de estilo analógico | Sin subir fotos",
            "Convierte preferencias limitadas en un orden de edición reversible sin subir, escanear, analizar ni guardar ninguna foto.",
            "Herramientas gratuitas",
            "English",
            "Gratis · sin introducir fotos · sin prometer resultados",
            "Planificador privado de estilo analógico",
            "Elige una dirección visual, la luz de origen y el acabado. La página devuelve un punto de partida, nunca un preset exacto ni un resultado garantizado.",
        ),
        badges=(
            "Sin fotos, archivos ni metadatos",
            "Sin acceso a cámara, fototeca o cuenta",
            "Sin subida, almacenamiento ni análisis",
            "Sin garantizar calidad ni resultados",
        ),
        planner=(
            "Crea una receta inicial reversible",
            "Las sugerencias son cualitativas y dependen de la imagen, la pantalla, el editor y el tamaño final. Previsualiza cada cambio y conserva el original.",
        ),
        labels=(
            "Dirección visual",
            "Luz de origen",
            "Preferencia de grano",
            "Dirección de color",
            "Uso final",
        ),
        options=(
            (
                "Película limpia",
                "35 mm cálido",
                "Cine frío",
                "Flash desechable",
                "Vintage desvaído",
            ),
            ("Escena luminosa", "Luz equilibrada", "Poca luz"),
            ("Sin grano añadido", "Grano sutil", "Grano visible"),
            ("Neutro", "Más cálido", "Más frío"),
            ("Una foto", "Serie coherente", "Impresión"),
        ),
        natural=(
            "Mantener tonos de piel naturales si aparecen personas",
            "Si aparecen personas, compara piel, ojos y pelo antes y después de cada paso de color.",
            "No se ha elegido una preferencia facial; aun así, revisa personas y colores de referencia antes de exportar.",
        ),
        results=(
            "Crear receta privada",
            "Dirección inicial",
            "Orden de ajustes",
            "Control de coherencia",
            "Límite de la receta",
        ),
        notes=(
            (
                "Mantén un contraste contenido, color equilibrado y altas luces suaves; estiliza solo cuando la base sea estable.",
                "Prioriza medios tonos cálidos, contraste moderado y luces suaves; vigila naranjas y piel antes de añadir efectos.",
                "Controla las altas luces, enfría ligeramente las sombras y evita que los objetos neutros se vuelvan azules.",
                "Conserva el brillo del flash directo y el contraste central; añade caída en bordes tras revisar caras y texto.",
                "Eleva suavemente los tonos más oscuros, reduce el contraste duro y apaga el color sin perder detalle importante.",
            ),
            (
                "Protege primero las altas luces y comprueba que las zonas claras conserven detalle útil.",
                "Ajusta exposición y balance de blancos antes del ambiente, el grano o los efectos decorativos.",
                "No levantes demasiado las sombras; revisa ruido y manchas de color al tamaño final.",
            ),
            (
                "No añadas grano y construye el estilo con luz, color y contraste.",
                "Añade grano fino al final y revisa cielos, piel y texto a tamaño normal.",
                "Usa grano visible solo tras la edición base; redúcelo si distrae en caras, detalles o impresión.",
            ),
            (
                "Corrige primero una dominante evidente y conserva blancos y objetos conocidos creíbles.",
                "Añade calidez poco a poco y revisa blancos, piel e iluminación interior antes de exportar.",
                "Enfría gradualmente sin volver azules las altas luces ni los objetos neutros.",
            ),
            (
                "Valora el resultado a su tamaño real y compáralo con el original conservado.",
                "Elige una edición de referencia, compara toda la serie y corrige valores atípicos sin acumular efectos.",
                "Previsualiza recorte y tamaño de impresión; el brillo de pantalla y el grano cambian en papel.",
            ),
        ),
        boundary=(
            "Es un orden de edición, no un preset, análisis de imagen ni promesa de imitar una película. "
            "No puede ver exposición, caras, color, enfoque, ruido, rango dinámico ni condiciones de salida."
        ),
        review=(
            "Cuatro controles antes de exportar",
            "Conserva un original intacto o una ruta de edición reversible.",
            "Aplica un cambio pequeño cada vez y compara a tamaño de visualización normal.",
            "Revisa luces, sombras, colores conocidos y personas antes de añadir textura.",
            "En una serie, compara todas las tomas y corrige las que desentonen antes de exportar.",
        ),
        sources=(
            "Contexto oficial de edición de Apple, no una recomendación",
            "Apple documenta cómo editar fotos y vídeos en el iPhone y cómo volver al original. Consulta los pasos vigentes para tu versión de iOS.",
            "Apple: editar fotos y vídeos en el iPhone",
            "Apple: deshacer y revertir ediciones de fotos",
        ),
        webmcp=(
            "Vista previa de la API imperativa WebMCP de Chrome",
            "Crea un orden cualitativo determinista solo con opciones limitadas. Nunca acepta ni accede a fotos, archivos, metadatos, cámara, fototeca, cuentas o texto libre; nunca analiza una imagen ni garantiza resultados.",
        ),
        app=(
            "¿Quieres previsualizar estilos analógicos en el dispositivo?",
            "PhotoCream Pro es opcional. Su ficha actual describe más de 100 estilos, grano, halación, fugas de luz, bloom, viñeta, vista previa en directo y controles de luz y color, con proceso en el dispositivo, sin cuenta ni subida. La descarga es gratuita y ofrece un desbloqueo de pago único. Consulta la ficha vigente para confirmar disponibilidad y funciones. Este planificador funciona sin la app.",
            "Ver PhotoCream Pro en el App Store",
        ),
        faq=(
            "Preguntas sobre el estilo analógico",
            (
                (
                    "¿Esta página recibe o inspecciona mi foto?",
                    "No. Solo acepta opciones limitadas y nunca recibe fotos, archivos ni metadatos.",
                ),
                (
                    "¿La receta recrea una película concreta?",
                    "No. Solo propone un orden inicial y no afirma precisión ni resultados.",
                ),
                (
                    "¿Puedo deshacer una edición en Fotos de Apple?",
                    "Apple documenta cómo volver una foto o un vídeo editado a su original; consulta los pasos vigentes de tu versión de iOS.",
                ),
            ),
        ),
        footer="Solo preferencias limitadas · sin acceso a fotos · sin análisis · sin prometer resultados",
        inline="Planifica una receta analógica privada antes de elegir editor",
        index=(
            "Planificador privado de estilo analógico",
            "Elige un estilo y recibe un orden reversible sin subir ni analizar ninguna foto.",
        ),
    ),
    "pt-BR": _copy(
        meta=(
            "Planejador privado de visual de filme | Sem enviar fotos",
            "Transforme preferências limitadas em uma ordem reversível de edição sem enviar, escanear, analisar ou guardar fotos.",
            "Ferramentas gratuitas",
            "English",
            "Grátis · sem entrada de foto · sem promessa de resultado",
            "Planejador privado de visual de filme",
            "Escolha a direção visual, a luz de origem e o acabamento. A página devolve um ponto de partida, nunca um preset exato ou resultado garantido.",
        ),
        badges=(
            "Sem foto, arquivo ou metadados",
            "Sem acesso à câmera, fototeca ou conta",
            "Sem envio, armazenamento ou análise",
            "Sem garantia de qualidade ou resultado",
        ),
        planner=(
            "Monte uma receita inicial reversível",
            "As sugestões são qualitativas e dependem da imagem, tela, editor e tamanho final. Visualize cada mudança e preserve o original.",
        ),
        labels=(
            "Direção visual",
            "Luz de origem",
            "Preferência de grão",
            "Direção de cor",
            "Uso final",
        ),
        options=(
            (
                "Filme limpo",
                "35 mm quente",
                "Cinema frio",
                "Flash de descartável",
                "Vintage desbotado",
            ),
            ("Cena clara", "Luz equilibrada", "Pouca luz"),
            ("Sem grão extra", "Grão sutil", "Grão visível"),
            ("Neutro", "Mais quente", "Mais frio"),
            ("Foto única", "Série combinando", "Impressão"),
        ),
        natural=(
            "Manter tons de pele naturais quando houver pessoas",
            "Quando houver pessoas, compare pele, olhos e cabelo antes e depois de cada etapa de cor.",
            "Nenhuma preferência facial foi escolhida; ainda assim, confira pessoas e cores de referência antes de exportar.",
        ),
        results=(
            "Criar receita privada",
            "Direção inicial",
            "Ordem de ajustes",
            "Verificação de consistência",
            "Limite da receita",
        ),
        notes=(
            (
                "Mantenha contraste contido, cor equilibrada e altas-luzes suaves; estilize só depois de estabilizar a base.",
                "Priorize meios-tons quentes, contraste moderado e luzes suaves; confira laranjas e pele antes dos efeitos.",
                "Controle as altas-luzes, esfrie levemente as sombras e evite azular objetos neutros.",
                "Preserve o brilho do flash direto e o contraste central; só depois de conferir rostos e texto, escureça as bordas.",
                "Eleve suavemente os tons mais escuros, reduza contraste duro e atenue a cor sem apagar detalhes importantes.",
            ),
            (
                "Proteja primeiro as altas-luzes e confira se as áreas claras ainda mantêm detalhes úteis.",
                "Ajuste exposição e balanço de branco antes de clima, grão ou efeitos decorativos.",
                "Evite clarear demais as sombras; confira ruído e manchas de cor no tamanho final.",
            ),
            (
                "Deixe o grão adicional desligado e construa o visual com luz, cor e contraste.",
                "Adicione grão fino no final e confira céu, pele e texto em tamanho normal.",
                "Use grão marcado só após a edição-base; reduza se distrair em rostos, detalhes ou impressão.",
            ),
            (
                "Corrija primeiro uma dominante óbvia e mantenha brancos e objetos conhecidos plausíveis.",
                "Aqueça aos poucos e confira brancos, pele e luz interna antes de exportar.",
                "Esfrie gradualmente sem deixar altas-luzes e objetos neutros azulados.",
            ),
            (
                "Avalie no tamanho real de exibição e compare com o original preservado.",
                "Escolha uma edição de referência, compare a série e corrija os pontos fora da curva sem empilhar efeitos.",
                "Visualize corte e tamanho de impressão; brilho de tela e grão podem mudar no papel.",
            ),
        ),
        boundary=(
            "Isto é uma ordem de edição, não preset, análise de imagem ou promessa de imitar um filme. "
            "Ela não vê exposição, rostos, cor, foco, ruído, alcance dinâmico ou condições de saída."
        ),
        review=(
            "Quatro verificações antes de exportar",
            "Mantenha um original intacto ou um caminho de edição reversível.",
            "Faça uma pequena mudança por vez e compare no tamanho normal de visualização.",
            "Confira luzes, sombras, cores conhecidas e pessoas antes de adicionar textura.",
            "Em séries, compare todos os quadros e corrija os destoantes antes de exportar.",
        ),
        sources=(
            "Contexto oficial de edição da Apple, não recomendação",
            "A Apple documenta como editar fotos e vídeos no iPhone e como reverter um item editado ao original. Confira as etapas atuais da sua versão do iOS.",
            "Apple: editar fotos e vídeos no iPhone",
            "Apple: desfazer e reverter edições de fotos",
        ),
        webmcp=(
            "Prévia da API imperativa WebMCP do Chrome",
            "Monta uma ordem qualitativa determinística somente com opções limitadas. Nunca aceita nem acessa fotos, arquivos, metadados, câmera, fototeca, contas ou texto livre; nunca analisa imagens nem garante resultado.",
        ),
        app=(
            "Quer visualizar estilos de filme direto no aparelho?",
            "PhotoCream Pro é opcional. A página atual na App Store descreve mais de 100 estilos, grão, halation, vazamentos de luz, bloom, vinheta, prévia ao vivo e controles de luz e cor, processados no aparelho, sem conta ou envio. O download é grátis e há um desbloqueio em compra única. Confira a página atual para disponibilidade e recursos exatos. Este planejador funciona sem o app.",
            "Ver PhotoCream Pro na App Store",
        ),
        faq=(
            "Dúvidas sobre visual de filme",
            (
                (
                    "Esta página recebe ou examina minha foto?",
                    "Não. Ela aceita apenas opções limitadas e nunca recebe foto, arquivo ou metadados.",
                ),
                (
                    "A receita recria um filme específico?",
                    "Não. Ela fornece apenas uma ordem inicial, sem alegar precisão ou resultado.",
                ),
                (
                    "Posso desfazer uma edição no Fotos da Apple?",
                    "A Apple documenta como reverter uma foto ou vídeo editado ao original; confira as etapas atuais da sua versão do iOS.",
                ),
            ),
        ),
        footer="Só preferências limitadas · sem acesso à foto · sem análise · sem promessa de resultado",
        inline="Planeje uma receita privada de filme antes de escolher o editor",
        index=(
            "Planejador privado de visual de filme",
            "Escolha uma direção e receba uma ordem reversível sem enviar ou analisar fotos.",
        ),
    ),
    "de-DE": _copy(
        meta=(
            "Privater Filmlook-Rezeptplaner | Ohne Foto-Upload",
            "Begrenzte Stilvorlieben in eine umkehrbare Bearbeitungsfolge übersetzen, ohne Fotos hochzuladen, zu scannen, zu analysieren oder zu speichern.",
            "Kostenlose Werkzeuge",
            "English",
            "Kostenlos · keine Fotoeingabe · kein Ergebnisversprechen",
            "Privater Planer für Filmlook-Rezepte",
            "Bildrichtung, Ausgangslicht und Finish wählen. Die Seite liefert eine Startreihenfolge, niemals ein exaktes Preset oder garantiertes Ergebnis.",
        ),
        badges=(
            "Keine Fotos, Dateien oder Metadaten",
            "Kein Kamera-, Mediathek- oder Kontozugriff",
            "Kein Upload, Speichern oder Analysieren",
            "Keine Qualitäts- oder Ergebnisgarantie",
        ),
        planner=(
            "Umkehrbares Startrezept erstellen",
            "Die Hinweise sind qualitativ und hängen von Bild, Display, Editor und Endgröße ab. Jede Änderung prüfen und das Original bewahren.",
        ),
        labels=(
            "Bildrichtung",
            "Ausgangslicht",
            "Kornwunsch",
            "Farbrichtung",
            "Endverwendung",
        ),
        options=(
            (
                "Klarer Filmlook",
                "Warmes 35 mm",
                "Kühler Kinolook",
                "Einwegblitz",
                "Verblasster Vintage-Look",
            ),
            ("Helle Szene", "Ausgeglichenes Licht", "Wenig Licht"),
            ("Kein Zusatzkorn", "Dezentes Korn", "Sichtbares Korn"),
            ("Neutral", "Wärmer", "Kühler"),
            ("Einzelbild", "Passende Serie", "Druck"),
        ),
        natural=(
            "Hauttöne natürlich halten, falls Personen zu sehen sind",
            "Bei Personen Haut, Augen und Haare vor und nach jedem Farbschritt vergleichen.",
            "Keine gesichtsbezogene Vorgabe gewählt; Personen und wichtige Referenzfarben vor dem Export trotzdem prüfen.",
        ),
        results=(
            "Privates Rezept erstellen",
            "Startrichtung",
            "Bearbeitungsfolge",
            "Konsistenzprüfung",
            "Grenze des Rezepts",
        ),
        notes=(
            (
                "Kontrast zurückhaltend, Farbe ausgewogen und Lichter sanft halten; erst nach stabiler Basis stilisieren.",
                "Warme Mitteltöne, moderaten Kontrast und weiche Lichter bevorzugen; Orange und Haut vor Effekten prüfen.",
                "Lichter kontrollieren, Schatten leicht kühlen und neutrale Gegenstände nicht blau färben.",
                "Helligkeit des Direktblitzes und klaren Mittenkontrast bewahren; Randabfall erst nach Gesichts- und Textprüfung.",
                "Dunkelste Töne sanft anheben, harten Kontrast mindern und Farbe dämpfen, ohne wichtige Details auszuwaschen.",
            ),
            (
                "Zuerst helle Lichter schützen und prüfen, ob dort noch nützliche Details erhalten sind.",
                "Belichtung und Weißabgleich vor Stimmung, Korn und Ziereffekten festlegen.",
                "Schatten nicht aggressiv aufhellen; Rauschen und Farbflecken in Endgröße prüfen.",
            ),
            (
                "Zusatzkorn auslassen und den Look über Licht, Farbe und Kontrast aufbauen.",
                "Feines Korn zuletzt ergänzen, dann Himmel, Haut und Text in Normalgröße prüfen.",
                "Deutliches Korn erst nach der Grundbearbeitung; bei störenden Gesichtern, Details oder Druckstrukturen reduzieren.",
            ),
            (
                "Erst einen klaren Farbstich korrigieren und Weiß sowie vertraute Objekte glaubwürdig halten.",
                "Wärme schrittweise ergänzen und Weiß, Haut sowie Innenlicht vor dem Export prüfen.",
                "Schrittweise kühlen, ohne Lichter und neutrale Gegenstände unnatürlich blau zu färben.",
            ),
            (
                "Ergebnis in tatsächlicher Anzeigegröße beurteilen und mit dem bewahrten Original vergleichen.",
                "Eine Referenzbearbeitung wählen, die ganze Reihe vergleichen und Ausreißer statt weiterer Effekte korrigieren.",
                "Vorgesehenen Ausschnitt und Druckgröße prüfen; Displayhelligkeit und Korn wirken auf Papier anders.",
            ),
        ),
        boundary=(
            "Dies ist eine Bearbeitungsreihenfolge, kein Preset, keine Bildanalyse und kein Versprechen einer Filmstocksimulation. "
            "Belichtung, Gesichter, Farbe, Fokus, Rauschen, Dynamikumfang und Ausgabebedingungen sind unbekannt."
        ),
        review=(
            "Vier Prüfungen vor dem Export",
            "Ein unverändertes Original oder einen umkehrbaren Bearbeitungsweg behalten.",
            "Jeweils nur eine kleine Änderung anwenden und in normaler Anzeigegröße vergleichen.",
            "Lichter, Schatten, vertraute Farben und Personen vor dem Hinzufügen von Textur prüfen.",
            "Bei einer Serie alle Bilder gemeinsam vergleichen und Ausreißer vor dem Export korrigieren.",
        ),
        sources=(
            "Offizieller Apple-Bearbeitungskontext, keine Empfehlung",
            "Apple dokumentiert die Foto- und Videobearbeitung auf dem iPhone sowie das Zurücksetzen eines bearbeiteten Objekts auf das Original. Aktuelle Schritte für die eigene iOS-Version prüfen.",
            "Apple: Fotos und Videos auf dem iPhone bearbeiten",
            "Apple: Fotobearbeitungen widerrufen und zurücksetzen",
        ),
        webmcp=(
            "Vorschau der imperativen Chrome-WebMCP-API",
            "Erstellt nur aus begrenzten Auswahlwerten eine deterministische qualitative Folge. Nimmt niemals Fotos, Dateien, Metadaten, Kamera, Mediathek, Konten oder Freitext an und greift nicht darauf zu; analysiert keine Bilder und garantiert kein Ergebnis.",
        ),
        app=(
            "Filmlooks direkt auf dem Gerät vorab ansehen?",
            "PhotoCream Pro ist optional. Der aktuelle App-Store-Eintrag beschreibt über 100 Looks, Korn, Halation, Lichtlecks, Bloom, Vignette, Live-Vorschau sowie Licht- und Farbregler, die auf dem Gerät ohne Konto oder Upload arbeiten. Der Download ist kostenlos; eine einmalige Freischaltung wird angeboten. Verfügbarkeit und genaue Funktionen im aktuellen Eintrag prüfen. Dieser Planer funktioniert ohne App.",
            "PhotoCream Pro im App Store ansehen",
        ),
        faq=(
            "Fragen zur Filmlook-Planung",
            (
                (
                    "Erhält oder prüft diese Seite mein Foto?",
                    "Nein. Sie nimmt nur begrenzte Auswahlwerte an und erhält niemals Fotos, Dateien oder Metadaten.",
                ),
                (
                    "Bildet das Rezept einen bestimmten Filmstock nach?",
                    "Nein. Es bietet nur eine Startreihenfolge und behauptet weder Genauigkeit noch Ergebnis.",
                ),
                (
                    "Kann ich eine Bearbeitung in Apple Fotos rückgängig machen?",
                    "Apple dokumentiert das Zurücksetzen bearbeiteter Fotos und Videos auf das Original; die aktuellen Schritte der eigenen iOS-Version prüfen.",
                ),
            ),
        ),
        footer="Nur begrenzte Auswahl · kein Fotozugriff · keine Bildanalyse · kein Ergebnisversprechen",
        inline="Vor der Editorwahl ein privates Filmlook-Rezept planen",
        index=(
            "Privater Filmlook-Rezeptplaner",
            "Filmrichtung wählen und eine umkehrbare Folge erhalten, ohne Fotos hochzuladen oder zu analysieren.",
        ),
    ),
    "fr-FR": _copy(
        meta=(
            "Planificateur privé de rendu argentique | Sans photo",
            "Transformez des préférences limitées en ordre de retouche réversible sans téléverser, scanner, analyser ni stocker de photo.",
            "Outils gratuits",
            "English",
            "Gratuit · aucune photo fournie · aucun résultat promis",
            "Planificateur privé de rendu argentique",
            "Choisissez une direction visuelle, la lumière de départ et la finition. La page renvoie un ordre initial, jamais un préréglage exact ni un résultat garanti.",
        ),
        badges=(
            "Aucune photo, aucun fichier ou métadonnée",
            "Aucun accès à l’appareil photo, photothèque ou compte",
            "Aucun envoi, stockage ou analyse",
            "Aucune garantie de qualité ou de résultat",
        ),
        planner=(
            "Composer une recette initiale réversible",
            "Les conseils sont qualitatifs et dépendent de l’image, de l’écran, de l’éditeur et du format final. Prévisualisez chaque changement et conservez l’original.",
        ),
        labels=(
            "Direction visuelle",
            "Lumière de départ",
            "Préférence de grain",
            "Direction colorimétrique",
            "Usage final",
        ),
        options=(
            (
                "Argentique épuré",
                "35 mm chaleureux",
                "Cinéma froid",
                "Flash jetable",
                "Vintage délavé",
            ),
            ("Scène lumineuse", "Lumière équilibrée", "Basse lumière"),
            ("Sans grain ajouté", "Grain discret", "Grain visible"),
            ("Neutre", "Plus chaud", "Plus froid"),
            ("Photo unique", "Série assortie", "Impression"),
        ),
        natural=(
            "Préserver des tons chair naturels si des personnes sont présentes",
            "En présence de personnes, comparez peau, yeux et cheveux avant et après chaque étape de couleur.",
            "Aucune préférence liée aux visages n’est choisie ; vérifiez tout de même les personnes et couleurs de référence avant l’export.",
        ),
        results=(
            "Créer la recette privée",
            "Direction initiale",
            "Ordre des réglages",
            "Contrôle de cohérence",
            "Limite de la recette",
        ),
        notes=(
            (
                "Gardez un contraste mesuré, des couleurs équilibrées et des hautes lumières douces ; stylisez seulement après stabilisation de la base.",
                "Privilégiez des tons moyens chauds, un contraste modéré et des lumières douces ; surveillez oranges et peau avant les effets.",
                "Maîtrisez les hautes lumières, refroidissez légèrement les ombres et évitez de bleuir les objets neutres.",
                "Conservez l’éclat du flash direct et le contraste central ; n’assombrissez les bords qu’après contrôle des visages et textes.",
                "Relevez doucement les tons les plus sombres, réduisez le contraste dur et atténuez la couleur sans effacer les détails importants.",
            ),
            (
                "Protégez d’abord les hautes lumières et vérifiez que les zones claires gardent des détails utiles.",
                "Réglez exposition et balance des blancs avant l’ambiance, le grain ou les effets décoratifs.",
                "Évitez de relever fortement les ombres ; contrôlez bruit et taches colorées au format final.",
            ),
            (
                "N’ajoutez pas de grain et construisez le rendu avec lumière, couleur et contraste.",
                "Ajoutez un grain fin à la fin, puis contrôlez ciel, peau et texte à taille normale.",
                "Utilisez un grain marqué après la retouche de base ; réduisez-le s’il gêne visages, détails ou texture imprimée.",
            ),
            (
                "Corrigez d’abord une dominante évidente et gardez blancs et objets familiers crédibles.",
                "Réchauffez progressivement puis vérifiez blancs, peau et éclairage intérieur avant l’export.",
                "Refroidissez progressivement sans rendre les hautes lumières et objets neutres artificiellement bleus.",
            ),
            (
                "Évaluez au format réel d’affichage et comparez avec l’original conservé.",
                "Choisissez une retouche de référence, comparez toute la série et corrigez les écarts au lieu d’empiler les effets.",
                "Prévisualisez le recadrage et le format d’impression ; luminosité d’écran et grain changent sur papier.",
            ),
        ),
        boundary=(
            "Il s’agit d’un ordre de retouche, pas d’un préréglage, d’une analyse d’image ou d’une promesse d’imiter une pellicule. "
            "Il ne voit ni exposition, visages, couleurs, mise au point, bruit, dynamique ou conditions de sortie."
        ),
        review=(
            "Quatre contrôles avant l’export",
            "Conservez un original intact ou un chemin de retouche réversible.",
            "Appliquez un petit changement à la fois et comparez à la taille normale d’affichage.",
            "Vérifiez lumières, ombres, couleurs familières et personnes avant d’ajouter de la texture.",
            "Pour une série, comparez toutes les images et corrigez les écarts avant l’export.",
        ),
        sources=(
            "Contexte officiel de retouche Apple, sans recommandation",
            "Apple explique comment modifier photos et vidéos sur iPhone et revenir à l’original. Vérifiez les étapes actuelles pour votre version d’iOS.",
            "Apple : modifier des photos et vidéos sur l’iPhone",
            "Apple : annuler et rétablir les retouches photo",
        ),
        webmcp=(
            "Aperçu de l’API WebMCP impérative de Chrome",
            "Compose un ordre qualitatif déterministe uniquement à partir de choix limités. N’accepte ni n’accède jamais aux photos, fichiers, métadonnées, appareil photo, photothèque, comptes ou texte libre ; n’analyse aucune image et ne garantit aucun résultat.",
        ),
        app=(
            "Envie de prévisualiser des rendus argentiques sur l’appareil ?",
            "PhotoCream Pro est facultatif. Sa fiche App Store actuelle décrit plus de 100 rendus, grain, halation, fuites de lumière, bloom, vignette, aperçu en direct et réglages de lumière et couleur, traités sur l’appareil sans compte ni envoi. Le téléchargement est gratuit avec un déverrouillage en achat unique. Consultez la fiche actuelle pour la disponibilité et les fonctions exactes. Ce planificateur fonctionne sans l’app.",
            "Voir PhotoCream Pro sur l’App Store",
        ),
        faq=(
            "Questions sur le rendu argentique",
            (
                (
                    "Cette page reçoit-elle ou examine-t-elle ma photo ?",
                    "Non. Elle accepte seulement des choix limités et ne reçoit jamais de photo, fichier ou métadonnée.",
                ),
                (
                    "La recette reproduit-elle une pellicule précise ?",
                    "Non. Elle propose uniquement un ordre initial, sans revendiquer précision ou résultat.",
                ),
                (
                    "Puis-je annuler une retouche dans Photos d’Apple ?",
                    "Apple explique comment rétablir l’original d’une photo ou vidéo modifiée ; vérifiez les étapes actuelles de votre version d’iOS.",
                ),
            ),
        ),
        footer="Choix limités uniquement · aucun accès photo · aucune analyse · aucun résultat promis",
        inline="Planifier une recette argentique privée avant de choisir un éditeur",
        index=(
            "Planificateur privé de rendu argentique",
            "Choisissez une direction et obtenez un ordre réversible sans envoyer ni analyser de photo.",
        ),
    ),
    "ja": _copy(
        meta=(
            "写真を送らないフィルム調レシピプランナー",
            "写真の送信・読み取り・解析・保存をせず、限られた好みから元に戻せる編集順を組み立てます。",
            "無料ツール",
            "English",
            "無料・写真入力なし・仕上がり保証なし",
            "プライベートなフィルム調レシピプランナー",
            "目指す雰囲気、元写真の光、仕上げ方を選ぶだけ。正確なプリセットや完成保証ではなく、編集を始める順番を返します。",
        ),
        badges=(
            "写真・ファイル・メタデータ不要",
            "カメラ・写真ライブラリ・アカウントへのアクセスなし",
            "アップロード・保存・画像解析なし",
            "品質・仕上がりの保証なし",
        ),
        planner=(
            "元に戻せる編集レシピを作る",
            "提案は目安です。仕上がりは元画像、画面、編集アプリ、表示サイズで変わります。変更ごとに確認し、オリジナルを残してください。",
        ),
        labels=(
            "目指す雰囲気",
            "元写真の光",
            "粒子の好み",
            "色の方向",
            "最終用途",
        ),
        options=(
            (
                "すっきりしたフィルム調",
                "暖かな35mm風",
                "クールなシネマ調",
                "使い捨てカメラのフラッシュ風",
                "色あせたヴィンテージ調",
            ),
            ("明るい場面", "均衡の取れた光", "暗い場面"),
            ("粒子を足さない", "控えめな粒子", "はっきりした粒子"),
            ("ニュートラル", "暖色寄り", "寒色寄り"),
            ("1枚の写真", "統一感のある連作", "プリント"),
        ),
        natural=(
            "人物がいる場合は肌色を自然に保つ",
            "人物がいる場合は、色を変えるたびに肌・目・髪を前後で見比べます。",
            "人物向けの条件は未選択です。それでも書き出し前に人物と基準になる色を確認します。",
        ),
        results=(
            "非公開レシピを作成",
            "最初の方向",
            "調整する順番",
            "統一感の確認",
            "このレシピの限界",
        ),
        notes=(
            (
                "コントラストを抑え、色を整え、ハイライトを柔らかくします。土台が安定してから演出を足します。",
                "中間調を暖かくし、コントラストはほどほど、ハイライトは柔らかく。効果を足す前にオレンジと肌色を確認します。",
                "ハイライトを抑え、シャドウをわずかに冷たくします。無彩色の物まで青くしないよう注意します。",
                "直射フラッシュの明るさと中央のくっきり感を残します。人物と文字を確認してから周辺を落とします。",
                "最暗部を少し持ち上げ、硬いコントラストと彩度を抑えます。大切なディテールは残します。",
            ),
            (
                "まず明るい部分を守り、最も明るい箇所にも必要なディテールが残るか確認します。",
                "雰囲気、粒子、装飾効果より先に、露出とホワイトバランスを整えます。",
                "シャドウを強く持ち上げず、最終表示サイズでノイズや色むらを確認します。",
            ),
            (
                "粒子は足さず、光・色・コントラストで雰囲気を作ります。",
                "細かな粒子は最後に足し、空・肌・文字を通常サイズで確認します。",
                "目立つ粒子は土台の編集後に追加し、顔や細部、印刷の質感を邪魔する場合は弱めます。",
            ),
            (
                "明らかな色かぶりを先に直し、白や見慣れた物の色を自然に保ちます。",
                "少しずつ暖色にし、書き出し前に白・肌・室内照明を確認します。",
                "少しずつ寒色にし、ハイライトや無彩色の物が不自然な青にならないようにします。",
            ),
            (
                "実際に見るサイズで判断し、残しておいたオリジナルと比較します。",
                "基準となる1枚を決め、全体を並べて比較し、効果を重ねず外れた写真だけ直します。",
                "予定するトリミングと印刷サイズで確認します。画面の明るさや粒子は紙で見え方が変わります。",
            ),
        ),
        boundary=(
            "これは編集順の提案であり、プリセット、画像解析、特定フィルムの再現保証ではありません。"
            "露出、人物、色、ピント、ノイズ、ダイナミックレンジ、出力条件は確認できません。"
        ),
        review=(
            "書き出し前の4項目",
            "手を加えていないオリジナル、または元に戻せる編集手順を残します。",
            "一度に小さく1項目だけ変え、通常の表示サイズで比較します。",
            "質感を足す前に、ハイライト、シャドウ、見慣れた色、人物を確認します。",
            "連作は全写真を並べ、外れた写真を直してから書き出します。",
        ),
        sources=(
            "Apple公式の編集情報（推奨を意味しません）",
            "AppleはiPhoneで写真やビデオを編集する方法と、編集した項目をオリジナルに戻す方法を案内しています。お使いのiOS向けの最新手順をご確認ください。",
            "Apple：iPhoneで写真やビデオを編集する",
            "Apple：写真の編集を取り消してオリジナルに戻す",
        ),
        webmcp=(
            "Chrome WebMCP imperative API プレビュー",
            "限られた選択肢だけから、決定的な定性編集順を作ります。写真、ファイル、メタデータ、カメラ、写真ライブラリ、アカウント、自由入力を受け取らずアクセスもしません。画像解析や仕上がり保証も行いません。",
        ),
        app=(
            "端末上でフィルム調をプレビューしたい場合",
            "PhotoCream Proは任意です。現在のApp Store掲載情報では、100種類以上のルック、粒子、ハレーション、光漏れ、ブルーム、ビネット、ライブプレビュー、光と色の調整を案内しており、アカウントやアップロードなしで端末上処理としています。無料でダウンロードでき、買い切りのロック解除があります。正確な提供状況と機能は最新の掲載情報をご確認ください。このプランナーはアプリなしでも使えます。",
            "App StoreでPhotoCream Proを見る",
        ),
        faq=(
            "フィルム調レシピのよくある質問",
            (
                (
                    "このページは写真を受け取ったり調べたりしますか？",
                    "いいえ。限られた選択肢だけを受け取り、写真、ファイル、メタデータは一切受け取りません。",
                ),
                (
                    "特定のフィルムを再現できますか？",
                    "いいえ。編集の開始順を提案するだけで、再現精度や仕上がりを保証しません。",
                ),
                (
                    "Appleの写真で編集を取り消せますか？",
                    "Appleは編集した写真やビデオをオリジナルに戻す方法を案内しています。お使いのiOS向け最新手順をご確認ください。",
                ),
            ),
        ),
        footer="限られた選択肢のみ・写真アクセスなし・画像解析なし・仕上がり保証なし",
        inline="編集アプリを選ぶ前に非公開のフィルム調レシピを作る",
        index=(
            "フィルム調レシピプランナー",
            "写真を送信・解析せず、目指す雰囲気から元に戻せる編集順を作ります。",
        ),
    ),
    "ko": _copy(
        meta=(
            "사진을 받지 않는 필름 룩 레시피 플래너",
            "사진을 업로드·스캔·분석·저장하지 않고 제한된 취향만으로 되돌릴 수 있는 보정 순서를 만듭니다.",
            "무료 도구",
            "English",
            "무료 · 사진 입력 없음 · 결과 보장 없음",
            "비공개 필름 룩 레시피 플래너",
            "원하는 분위기, 원본의 빛, 마무리 방식을 고르세요. 정확한 프리셋이나 결과 보장이 아닌 시작 순서를 제안합니다.",
        ),
        badges=(
            "사진·파일·메타데이터 불필요",
            "카메라·사진 보관함·계정 접근 없음",
            "업로드·저장·이미지 분석 없음",
            "품질·결과 보장 없음",
        ),
        planner=(
            "되돌릴 수 있는 시작 레시피 만들기",
            "제안은 정성적인 출발점입니다. 결과는 원본, 화면, 편집기, 최종 크기에 따라 달라집니다. 변경할 때마다 미리 보고 원본을 보관하세요.",
        ),
        labels=(
            "원하는 분위기",
            "원본 조명",
            "입자감",
            "색감 방향",
            "최종 용도",
        ),
        options=(
            (
                "깔끔한 필름 룩",
                "따뜻한 35mm 룩",
                "차가운 시네마 룩",
                "일회용 카메라 플래시 룩",
                "빛바랜 빈티지 룩",
            ),
            ("밝은 장면", "균형 잡힌 빛", "저조도"),
            ("입자 추가 안 함", "은은한 입자", "뚜렷한 입자"),
            ("중립", "더 따뜻하게", "더 차갑게"),
            ("한 장", "통일된 시리즈", "인쇄"),
        ),
        natural=(
            "사람이 있다면 피부색을 자연스럽게 유지",
            "사람이 있다면 색을 바꿀 때마다 피부, 눈, 머리카락을 전후 비교하세요.",
            "얼굴 관련 조건은 선택하지 않았습니다. 그래도 내보내기 전에 사람과 기준이 되는 색을 확인하세요.",
        ),
        results=(
            "비공개 레시피 만들기",
            "시작 방향",
            "보정 순서",
            "통일감 확인",
            "레시피의 한계",
        ),
        notes=(
            (
                "대비는 절제하고 색은 균형 있게, 하이라이트는 부드럽게 잡은 뒤 바탕이 안정되면 스타일을 더하세요.",
                "중간 톤은 따뜻하게, 대비는 적당히, 하이라이트는 부드럽게 잡고 효과 전에 주황색과 피부를 확인하세요.",
                "하이라이트를 억제하고 그림자를 살짝 차갑게 하되 중립 물체까지 파랗게 만들지 마세요.",
                "직광 플래시의 밝기와 중앙의 선명한 대비를 살리고 얼굴과 글자를 확인한 뒤 가장자리를 어둡게 하세요.",
                "가장 어두운 톤을 조금 올리고 강한 대비와 채도를 줄이되 중요한 디테일은 남기세요.",
            ),
            (
                "밝은 하이라이트를 먼저 보호하고 가장 밝은 곳에 필요한 디테일이 남는지 확인하세요.",
                "분위기, 입자, 장식 효과보다 노출과 화이트 밸런스를 먼저 맞추세요.",
                "그림자를 과도하게 밝히지 말고 최종 크기에서 노이즈와 색 얼룩을 확인하세요.",
            ),
            (
                "입자를 추가하지 않고 빛, 색, 대비로 분위기를 만드세요.",
                "미세한 입자는 마지막에 더한 뒤 하늘, 피부, 글자를 일반 크기로 확인하세요.",
                "뚜렷한 입자는 기본 보정 뒤에 더하고 얼굴, 작은 디테일, 인쇄 질감을 방해하면 줄이세요.",
            ),
            (
                "뚜렷한 색 틀어짐을 먼저 고치고 흰색과 익숙한 사물의 색을 자연스럽게 유지하세요.",
                "조금씩 따뜻하게 하며 내보내기 전에 흰색, 피부, 실내 조명을 다시 확인하세요.",
                "조금씩 차갑게 하되 하이라이트와 중립 물체가 부자연스럽게 파래지지 않게 하세요.",
            ),
            (
                "실제로 볼 크기에서 판단하고 보관한 원본과 비교하세요.",
                "기준 보정 한 장을 정해 전체 시리즈를 비교하고 효과를 더 쌓지 말고 튀는 사진만 조정하세요.",
                "예정한 자르기와 인쇄 크기로 확인하세요. 화면 밝기와 입자감은 종이에서 다르게 보일 수 있습니다.",
            ),
        ),
        boundary=(
            "이것은 보정 순서일 뿐 프리셋, 이미지 분석, 특정 필름 재현 약속이 아닙니다. "
            "노출, 얼굴, 색, 초점, 노이즈, 다이내믹 레인지, 출력 조건을 볼 수 없습니다."
        ),
        review=(
            "내보내기 전 네 가지 확인",
            "손대지 않은 원본이나 되돌릴 수 있는 편집 경로를 남기세요.",
            "한 번에 한 항목만 작게 바꾸고 일반적인 보기 크기에서 비교하세요.",
            "질감을 더하기 전에 하이라이트, 그림자, 익숙한 색, 사람을 확인하세요.",
            "시리즈는 모든 사진을 함께 비교하고 튀는 사진을 고친 뒤 내보내세요.",
        ),
        sources=(
            "Apple 공식 편집 안내이며 추천을 뜻하지 않음",
            "Apple은 iPhone에서 사진과 비디오를 편집하는 방법과 편집 항목을 원본으로 되돌리는 방법을 안내합니다. 사용 중인 iOS 버전의 최신 단계를 확인하세요.",
            "Apple: iPhone에서 사진 및 비디오 편집하기",
            "Apple: 사진 편집 취소 및 원본으로 되돌리기",
        ),
        webmcp=(
            "Chrome 명령형 WebMCP API 미리보기",
            "제한된 선택지만으로 결정론적인 정성 보정 순서를 만듭니다. 사진, 파일, 메타데이터, 카메라, 사진 보관함, 계정, 자유 입력을 받거나 접근하지 않으며 이미지를 분석하거나 결과를 보장하지 않습니다.",
        ),
        app=(
            "기기에서 필름 룩을 바로 미리 보고 싶다면",
            "PhotoCream Pro는 선택 사항입니다. 현재 App Store 설명은 100개 이상의 룩, 입자, 할레이션, 빛샘, 블룸, 비네트, 실시간 미리보기, 빛과 색 조절을 안내하며 계정이나 업로드 없이 기기에서 처리한다고 밝힙니다. 무료로 내려받고 일회성 구매로 잠금을 해제할 수 있습니다. 정확한 제공 여부와 기능은 최신 설명을 확인하세요. 이 플래너는 앱 없이도 작동합니다.",
            "App Store에서 PhotoCream Pro 보기",
        ),
        faq=(
            "필름 룩 계획 질문",
            (
                (
                    "이 페이지가 제 사진을 받거나 살펴보나요?",
                    "아니요. 제한된 선택지만 받고 사진, 파일, 메타데이터는 전혀 받지 않습니다.",
                ),
                (
                    "특정 필름을 그대로 재현하나요?",
                    "아니요. 시작 순서만 제안하며 정확도나 결과를 주장하지 않습니다.",
                ),
                (
                    "Apple 사진 앱에서 편집을 취소할 수 있나요?",
                    "Apple은 편집한 사진이나 비디오를 원본으로 되돌리는 방법을 안내합니다. 사용 중인 iOS 버전의 최신 단계를 확인하세요.",
                ),
            ),
        ),
        footer="제한된 선택지만 사용 · 사진 접근 없음 · 이미지 분석 없음 · 결과 보장 없음",
        inline="편집기를 고르기 전에 비공개 필름 룩 레시피 계획하기",
        index=(
            "비공개 필름 룩 레시피 플래너",
            "사진을 보내거나 분석하지 않고 원하는 분위기에 맞는 되돌릴 수 있는 보정 순서를 만듭니다.",
        ),
    ),
    "zh-Hant": _copy(
        meta=(
            "私密底片風配方規劃器｜不用上傳照片",
            "只用有限選項安排可還原的修圖順序，不上傳、不掃描、不分析也不儲存任何照片。",
            "免費工具",
            "English",
            "免費・不輸入照片・不保證成果",
            "私密底片風配方規劃器",
            "選擇想要的氛圍、原始光線與輸出方式；本頁只提供起手順序，不是精準預設，也不保證成品效果。",
        ),
        badges=(
            "不接收照片、檔案或中繼資料",
            "不存取相機、相簿或帳號",
            "不上傳、不儲存、不分析",
            "不保證品質或結果",
        ),
        planner=(
            "建立可還原的起手配方",
            "建議是定性起點；實際效果會受原圖、螢幕、編輯器與最終尺寸影響。每一步都先預覽，並保留原始檔。",
        ),
        labels=(
            "視覺方向",
            "原圖光線",
            "顆粒偏好",
            "色調方向",
            "最終用途",
        ),
        options=(
            (
                "乾淨底片感",
                "暖調 35mm",
                "冷調電影感",
                "即可拍閃光感",
                "褪色復古感",
            ),
            ("明亮場景", "均衡光線", "低光場景"),
            ("不另加顆粒", "細緻顆粒", "明顯顆粒"),
            ("中性", "偏暖", "偏冷"),
            ("單張照片", "一致系列", "列印"),
        ),
        natural=(
            "畫面有人時維持自然膚色",
            "畫面有人時，每次調色前後都比較皮膚、眼睛與頭髮。",
            "未選擇人像限制；輸出前仍應檢查人物與重要參考色。",
        ),
        results=(
            "建立私密配方",
            "起手方向",
            "調整順序",
            "一致性檢查",
            "配方界線",
        ),
        notes=(
            (
                "先壓低過強對比、校正色彩並柔化高光；基礎穩定後再加入風格效果。",
                "以暖色中間調、適度對比與柔和高光為主；加效果前先檢查橘色與膚色。",
                "控制高光、只把陰影微微調冷，避免中性物體也變藍。",
                "保留直打閃光的亮度與中央清晰對比；確認人臉和文字後再加邊緣暗角。",
                "輕微抬高最暗區、降低硬對比與飽和度，但不要洗掉重要細節。",
            ),
            (
                "先保護明亮高光，確認最亮區域仍保有必要細節。",
                "先調好曝光與白平衡，再處理氛圍、顆粒或裝飾效果。",
                "不要大幅拉亮陰影；以最終觀看尺寸檢查雜訊和色塊。",
            ),
            (
                "不另加顆粒，改用光線、色彩與對比建立風格。",
                "最後才加細顆粒，並以一般尺寸檢查天空、皮膚和文字。",
                "完成基礎調整後再加明顯顆粒；若干擾人臉、細節或印刷質感就減弱。",
            ),
            (
                "先修正明顯偏色，讓白色與熟悉物件維持可信。",
                "逐步加暖；輸出前再次檢查白色、膚色與室內燈光。",
                "逐步降冷；避免高光與中性物體變成不自然的藍色。",
            ),
            (
                "用實際觀看尺寸判斷，並和保留的原始檔比較。",
                "先選一張基準修圖，並排比較整組；修正落差，不要再疊更多效果。",
                "用預定裁切和列印尺寸預覽；螢幕亮度與顆粒在紙上可能不同。",
            ),
        ),
        boundary=(
            "這只是一套修圖順序，不是預設、影像分析或特定底片模擬保證。"
            "本頁看不到曝光、人臉、顏色、對焦、雜訊、動態範圍或輸出條件。"
        ),
        review=(
            "輸出前的四項檢查",
            "保留未修改的原始檔，或確保整個編輯流程可以還原。",
            "每次只做一個小調整，並用一般觀看尺寸比較。",
            "加入質感前先檢查高光、陰影、熟悉顏色與人物。",
            "系列照片應並排檢查，修正落差後再輸出。",
        ),
        sources=(
            "Apple 官方編輯背景，並非推薦",
            "Apple 說明如何在 iPhone 編輯照片與影片，以及如何將已編輯項目還原成原始版本；請依目前 iOS 版本確認最新步驟。",
            "Apple：在 iPhone 編輯照片與影片",
            "Apple：取消並還原照片編輯",
        ),
        webmcp=(
            "Chrome imperative WebMCP API 預覽",
            "只根據有限選項建立確定性的定性修圖順序；不接收也不存取照片、檔案、中繼資料、相機、相簿、帳號或自由文字，不分析影像，也不保證結果。",
        ),
        app=(
            "想直接在裝置上預覽底片風格？",
            "PhotoCream Pro 是選用項目。目前 App Store 頁面列出 100+ 種風格、顆粒、光暈、漏光、柔光、暗角、即時預覽及光線與色彩控制，並表示全程在裝置處理、不需帳號也不上傳。可免費下載，另提供一次性解鎖。確切功能與供應狀態請查看目前頁面；本規劃器不安裝 App 也能使用。",
            "前往 App Store 查看 PhotoCream Pro",
        ),
        faq=(
            "底片風規劃問題",
            (
                (
                    "這個頁面會接收或檢查我的照片嗎？",
                    "不會。本頁只接收有限選項，完全不接收照片、檔案或中繼資料。",
                ),
                (
                    "這份配方能精準重現某款底片嗎？",
                    "不能。它只提供起手順序，不宣稱模擬準確度或成果。",
                ),
                (
                    "Apple 照片中的編輯可以復原嗎？",
                    "Apple 有說明如何將已編輯的照片或影片還原成原始版本；請依目前 iOS 版本確認最新步驟。",
                ),
            ),
        ),
        footer="只用有限選項・不存取照片・不分析影像・不保證成果",
        inline="選擇編輯器前，先規劃私密底片風配方",
        index=(
            "私密底片風配方規劃器",
            "不用上傳或分析照片，依風格偏好取得可還原的修圖順序。",
        ),
    ),
    "zh-Hans": _copy(
        meta=(
            "私密胶片风配方规划器｜不用上传照片",
            "只用有限选项安排可还原的修图顺序，不上传、不扫描、不分析也不存储任何照片。",
            "免费工具",
            "English",
            "免费・不输入照片・不保证成果",
            "私密胶片风配方规划器",
            "选择想要的氛围、原始光线和输出方式；本页只提供起步顺序，不是精准预设，也不保证成片效果。",
        ),
        badges=(
            "不接收照片、文件或元数据",
            "不访问相机、相册或账号",
            "不上传、不存储、不分析",
            "不保证质量或结果",
        ),
        planner=(
            "建立可还原的起步配方",
            "建议只是定性起点；实际效果会受原图、屏幕、编辑器和最终尺寸影响。每一步都先预览，并保留原图。",
        ),
        labels=(
            "视觉方向",
            "原图光线",
            "颗粒偏好",
            "色调方向",
            "最终用途",
        ),
        options=(
            (
                "干净胶片感",
                "暖调 35mm",
                "冷调电影感",
                "一次性相机闪光感",
                "褪色复古感",
            ),
            ("明亮场景", "均衡光线", "低光场景"),
            ("不另加颗粒", "细腻颗粒", "明显颗粒"),
            ("中性", "偏暖", "偏冷"),
            ("单张照片", "一致系列", "打印"),
        ),
        natural=(
            "画面有人时保持自然肤色",
            "画面有人时，每次调色前后都比较皮肤、眼睛和头发。",
            "未选择人像限制；导出前仍应检查人物和重要参考色。",
        ),
        results=(
            "建立私密配方",
            "起步方向",
            "调整顺序",
            "一致性检查",
            "配方边界",
        ),
        notes=(
            (
                "先控制过强对比、校正色彩并柔化高光；基础稳定后再加入风格效果。",
                "以暖色中间调、适度对比和柔和高光为主；加效果前先检查橙色和肤色。",
                "控制高光、只把阴影微微调冷，避免中性物体也变蓝。",
                "保留直打闪光的亮度和中央清晰对比；确认人脸和文字后再加边缘暗角。",
                "轻微抬高最暗区域、降低硬对比和饱和度，但不要洗掉重要细节。",
            ),
            (
                "先保护明亮高光，确认最亮区域仍保留必要细节。",
                "先调好曝光和白平衡，再处理氛围、颗粒或装饰效果。",
                "不要大幅提亮阴影；用最终观看尺寸检查噪点和色块。",
            ),
            (
                "不另加颗粒，改用光线、色彩和对比建立风格。",
                "最后才加细颗粒，并用常规尺寸检查天空、皮肤和文字。",
                "完成基础调整后再加明显颗粒；如果干扰人脸、细节或印刷质感就减弱。",
            ),
            (
                "先修正明显偏色，让白色和熟悉物体保持可信。",
                "逐步加暖；导出前再次检查白色、肤色和室内灯光。",
                "逐步降冷；避免高光和中性物体变成不自然的蓝色。",
            ),
            (
                "用实际观看尺寸判断，并和保留的原图比较。",
                "先选一张基准修图，并排比较整组；修正落差，不要继续叠加效果。",
                "用预定裁切和打印尺寸预览；屏幕亮度和颗粒在纸上可能不同。",
            ),
        ),
        boundary=(
            "这只是一套修图顺序，不是预设、图像分析或特定胶片模拟保证。"
            "本页看不到曝光、人脸、颜色、对焦、噪点、动态范围或输出条件。"
        ),
        review=(
            "导出前的四项检查",
            "保留未修改的原图，或确保整个编辑流程可以还原。",
            "每次只做一个小调整，并用常规观看尺寸比较。",
            "加入质感前先检查高光、阴影、熟悉颜色和人物。",
            "系列照片应并排检查，修正落差后再导出。",
        ),
        sources=(
            "Apple 官方编辑背景，并非推荐",
            "Apple 说明如何在 iPhone 编辑照片和视频，以及如何将已编辑项目还原成原始版本；请根据当前 iOS 版本确认最新步骤。",
            "Apple：在 iPhone 编辑照片和视频",
            "Apple：撤销并还原照片编辑",
        ),
        webmcp=(
            "Chrome imperative WebMCP API 预览",
            "只根据有限选项建立确定性的定性修图顺序；不接收也不访问照片、文件、元数据、相机、相册、账号或自由文本，不分析图像，也不保证结果。",
        ),
        app=(
            "想直接在设备上预览胶片风格？",
            "PhotoCream Pro 是可选项目。目前 App Store 页面列出 100+ 种风格、颗粒、光晕、漏光、柔光、暗角、实时预览以及光线和色彩控制，并表示全程在设备处理、不需账号也不上传。可免费下载，另提供一次性解锁。具体功能和供应状态请查看当前页面；本规划器不安装 App 也能使用。",
            "前往 App Store 查看 PhotoCream Pro",
        ),
        faq=(
            "胶片风规划问题",
            (
                (
                    "这个页面会接收或检查我的照片吗？",
                    "不会。本页只接收有限选项，完全不接收照片、文件或元数据。",
                ),
                (
                    "这份配方能精准还原某款胶片吗？",
                    "不能。它只提供起步顺序，不宣称模拟准确度或成果。",
                ),
                (
                    "Apple 照片中的编辑可以恢复吗？",
                    "Apple 有说明如何将已编辑的照片或视频还原成原始版本；请根据当前 iOS 版本确认最新步骤。",
                ),
            ),
        ),
        footer="只用有限选项・不访问照片・不分析图像・不保证成果",
        inline="选择编辑器前，先规划私密胶片风配方",
        index=(
            "私密胶片风配方规划器",
            "不用上传或分析照片，按风格偏好获得可还原的修图顺序。",
        ),
    ),
    "vi": _copy(
        meta=(
            "Trình lập công thức phong cách phim riêng tư | Không tải ảnh lên",
            "Biến các tùy chọn phong cách có giới hạn thành thứ tự chỉnh sửa có thể hoàn tác mà không tải lên, quét, phân tích hay lưu trữ ảnh.",
            "Công cụ miễn phí",
            "English",
            "Miễn phí · không nhập ảnh · không hứa kết quả",
            "Trình lập công thức phong cách phim riêng tư",
            "Chọn hướng hình ảnh, điều kiện ánh sáng và tùy chọn hoàn thiện. Trang trả về một thứ tự khởi đầu, không bao giờ là preset chính xác hay kết quả đảm bảo.",
        ),
        badges=(
            "Không ảnh, tệp hay siêu dữ liệu",
            "Không truy cập máy ảnh, thư viện hay tài khoản",
            "Không tải lên, lưu trữ hay phân tích",
            "Không đảm bảo chất lượng hay kết quả",
        ),
        planner=(
            "Tạo công thức khởi đầu có thể hoàn tác",
            "Gợi ý mang tính định tính và phụ thuộc vào ảnh gốc, màn hình, trình chỉnh sửa và kích thước cuối. Xem trước từng thay đổi và giữ một bản gốc.",
        ),
        labels=(
            "Hướng hình ảnh",
            "Ánh sáng nguồn",
            "Tùy chọn hạt",
            "Hướng màu",
            "Mục đích cuối",
        ),
        options=(
            (
                "Phim trong trẻo",
                "35mm ấm",
                "Điện ảnh lạnh",
                "Flash máy ảnh dùng một lần",
                "Cổ điển phai màu",
            ),
            ("Cảnh sáng", "Ánh sáng cân bằng", "Thiếu sáng"),
            ("Không thêm hạt", "Hạt nhẹ", "Hạt rõ"),
            ("Trung tính", "Ấm hơn", "Lạnh hơn"),
            ("Ảnh đơn", "Chuỗi đồng bộ", "In ấn"),
        ),
        natural=(
            "Giữ tông da tự nhiên khi có người",
            "Nếu có người, so sánh da, mắt và tóc trước và sau mỗi bước chỉnh màu.",
            "Không chọn tùy chọn riêng cho khuôn mặt; vẫn kiểm tra người và các tham chiếu màu quan trọng trước khi xuất.",
        ),
        results=(
            "Tạo công thức riêng tư",
            "Hướng khởi đầu",
            "Thứ tự điều chỉnh",
            "Kiểm tra tính nhất quán",
            "Giới hạn công thức",
        ),
        notes=(
            (
                "Giữ tương phản vừa phải, màu cân bằng và vùng sáng dịu; chỉ thêm phong cách sau khi nền trông ổn định.",
                "Ưu tiên tông trung ấm, tương phản vừa và vùng sáng mềm; để ý cam và da trước khi thêm hiệu ứng.",
                "Giữ vùng sáng có kiểm soát, làm vùng tối hơi lạnh và tránh biến vật trung tính thành xanh.",
                "Giữ độ sáng flash trực tiếp và tương phản trung tâm sắc nét; chỉ thêm mờ viền sau khi kiểm tra mặt và chữ.",
                "Nâng nhẹ tông tối nhất, giảm tương phản gắt và làm dịu màu mà không làm mất chi tiết quan trọng.",
            ),
            (
                "Bảo vệ vùng sáng trước và đánh giá xem vùng sáng nhất còn giữ chi tiết hữu ích không.",
                "Đặt phơi sáng và cân bằng trắng trước khi thêm tâm trạng, hạt hay hiệu ứng trang trí.",
                "Tránh nâng vùng tối quá mạnh; kiểm tra nhiễu và đốm màu ở kích thước xem cuối.",
            ),
            (
                "Tắt hạt thêm và dùng ánh sáng, màu và tương phản để tạo phong cách.",
                "Thêm hạt mịn gần cuối, rồi kiểm tra bầu trời mịn, da và chữ ở kích thước bình thường.",
                "Chỉ dùng hạt có chủ đích sau khi chỉnh nền; giảm nếu mặt, chi tiết nhỏ hay kết cấu in gây rối.",
            ),
            (
                "Sửa ám màu rõ ràng trước, rồi giữ vùng trắng và vật quen thuộc trông đáng tin.",
                "Thêm ấm từ từ và kiểm lại vùng trắng, da và ánh sáng trong nhà trước khi xuất.",
                "Làm lạnh ảnh từ từ; giữ vùng sáng và vật trung tính không bị xanh không tự nhiên.",
            ),
            (
                "Đánh giá kết quả ở kích thước xem thực tế và so với bản gốc đã giữ.",
                "Chọn một bản chỉnh tham chiếu, so sánh toàn chuỗi và sửa các ảnh lệch thay vì chồng thêm hiệu ứng.",
                "Xem trước khung cắt và kích thước in dự định; độ sáng màn hình và hạt thêm có thể khác trên giấy.",
            ),
        ),
        boundary=(
            "Đây là thứ tự chỉnh sửa, không phải preset, phân tích ảnh hay lời hứa khớp với loại phim. "
            "Nó không thể thấy phơi sáng, khuôn mặt, màu, lấy nét, nhiễu, dải tương phản hay điều kiện đầu ra."
        ),
        review=(
            "Bốn điều cần kiểm trước khi xuất",
            "Giữ một bản gốc chưa chạm vào hoặc một lộ trình chỉnh sửa có thể hoàn tác.",
            "Áp dụng một thay đổi nhỏ mỗi lần và so sánh ở kích thước xem bình thường.",
            "Kiểm tra vùng sáng, vùng tối, màu quen thuộc và người trước khi thêm kết cấu.",
            "Với một chuỗi, so sánh tất cả khung cùng nhau và sửa ảnh lệch trước khi xuất.",
        ),
        sources=(
            "Bối cảnh chỉnh sửa chính thức của Apple, không phải sự chứng thực",
            "Apple ghi lại cách chỉnh sửa ảnh và video trên iPhone và cách hoàn nguyên mục đã chỉnh về bản gốc. Hãy xem các bước hiện tại cho phiên bản iOS của bạn.",
            "Apple: chỉnh sửa ảnh và video trên iPhone",
            "Apple: hoàn tác và hoàn nguyên chỉnh sửa ảnh trên iPhone",
        ),
        webmcp=(
            "Bản xem trước API mệnh lệnh WebMCP của Chrome",
            "Tạo thứ tự chỉnh sửa định tính xác định chỉ từ các lựa chọn phong cách có giới hạn. Không bao giờ nhận hay truy cập ảnh, tệp, siêu dữ liệu, máy ảnh, thư viện, tài khoản hay văn bản tự do; không bao giờ phân tích ảnh hay đảm bảo kết quả.",
        ),
        app=(
            "Muốn xem trước phong cách phim ngay trên thiết bị?",
            "PhotoCream Pro là tùy chọn. Trang App Store hiện tại mô tả hơn 100 phong cách, hạt, halation, light leak, bloom, vignette, xem trước trực tiếp và điều khiển sáng/màu, xử lý trên thiết bị mà không cần tài khoản hay tải lên. Tải miễn phí kèm mở khóa một lần. Hãy xem trang hiện tại để biết tình trạng và tính năng chính xác. Trình lập kế hoạch này hoạt động mà không cần app.",
            "Xem PhotoCream Pro trên App Store",
        ),
        faq=(
            "Câu hỏi về lập phong cách phim",
            (
                (
                    "Trang này có nhận hay xem ảnh của tôi không?",
                    "Không. Nó chỉ nhận các lựa chọn phong cách có giới hạn và không bao giờ nhận ảnh, tệp hay siêu dữ liệu.",
                ),
                (
                    "Công thức này có tái tạo đúng một loại phim cụ thể không?",
                    "Không. Nó đưa ra một thứ tự khởi đầu và không tuyên bố về độ chính xác hay kết quả.",
                ),
                (
                    "Tôi có thể hoàn tác chỉnh sửa trong Apple Photos không?",
                    "Apple ghi lại cách hoàn nguyên ảnh hoặc video đã chỉnh về bản gốc; hãy xác nhận các bước hiện tại cho phiên bản iOS của bạn.",
                ),
            ),
        ),
        footer="Chỉ tùy chọn có giới hạn · không truy cập ảnh · không phân tích ảnh · không hứa kết quả",
        inline="Lập công thức phong cách phim riêng tư trước khi chọn trình chỉnh sửa",
        index=(
            "Trình lập công thức phong cách phim riêng tư",
            "Chọn một hướng phim và nhận thứ tự chỉnh sửa có thể hoàn tác mà không tải lên hay phân tích ảnh.",
        ),
    ),
    "th": _copy(
        meta=(
            "ตัววางแผนสูตรลุคฟิล์มแบบส่วนตัว | ไม่อัปโหลดรูป",
            "เปลี่ยนความชอบด้านสไตล์ที่มีขอบเขตให้เป็นลำดับการแก้ไขที่ย้อนกลับได้ โดยไม่อัปโหลด สแกน วิเคราะห์ หรือจัดเก็บรูป",
            "เครื่องมือฟรี",
            "English",
            "ฟรี · ไม่ป้อนรูป · ไม่รับประกันผล",
            "ตัววางแผนสูตรลุคฟิล์มแบบส่วนตัว",
            "เลือกทิศทางภาพ สภาพแสง และความชอบการเก็บงาน หน้าเว็บจะคืนลำดับเริ่มต้น ไม่ใช่พรีเซ็ตที่แน่นอนหรือผลลัพธ์ที่รับประกัน",
        ),
        badges=(
            "ไม่มีรูป ไฟล์ หรือเมทาดาทา",
            "ไม่เข้าถึงกล้อง คลังภาพ หรือบัญชี",
            "ไม่อัปโหลด จัดเก็บ หรือวิเคราะห์",
            "ไม่รับประกันคุณภาพหรือผลลัพธ์",
        ),
        planner=(
            "สร้างสูตรเริ่มต้นที่ย้อนกลับได้",
            "คำแนะนำเป็นเชิงคุณภาพและขึ้นกับภาพต้นฉบับ จอแสดงผล โปรแกรมแก้ไข และขนาดสุดท้าย ดูตัวอย่างทุกการเปลี่ยนแปลงและเก็บต้นฉบับไว้",
        ),
        labels=(
            "ทิศทางภาพ",
            "แสงต้นฉบับ",
            "ความชอบเรื่องเกรน",
            "ทิศทางสี",
            "การใช้งานสุดท้าย",
        ),
        options=(
            (
                "ฟิล์มสะอาด",
                "35mm โทนอุ่น",
                "ซินีมาโทนเย็น",
                "แฟลชกล้องใช้แล้วทิ้ง",
                "วินเทจสีจาง",
            ),
            ("ฉากสว่าง", "แสงสมดุล", "แสงน้อย"),
            ("ไม่เพิ่มเกรน", "เกรนบาง", "เกรนชัด"),
            ("เป็นกลาง", "อุ่นขึ้น", "เย็นขึ้น"),
            ("รูปเดียว", "ชุดที่เข้ากัน", "พิมพ์"),
        ),
        natural=(
            "รักษาโทนผิวให้เป็นธรรมชาติเมื่อมีคน",
            "หากมีคน ให้เปรียบเทียบผิว ตา และผมก่อนและหลังทุกขั้นตอนปรับสี",
            "ไม่ได้เลือกความชอบเฉพาะใบหน้า แต่ยังควรตรวจคนและการอ้างอิงสีสำคัญก่อนส่งออก",
        ),
        results=(
            "สร้างสูตรส่วนตัว",
            "ทิศทางเริ่มต้น",
            "ลำดับการปรับ",
            "ตรวจความสม่ำเสมอ",
            "ขอบเขตของสูตร",
        ),
        notes=(
            (
                "คุมคอนทราสต์ให้พอดี สีสมดุล และไฮไลต์นุ่มนวล เพิ่มสไตล์หลังจากฐานดูนิ่งแล้ว",
                "เน้นมิดโทนอุ่น คอนทราสต์ปานกลาง และไฮไลต์นุ่ม ระวังสีส้มและผิวก่อนเพิ่มเอฟเฟกต์",
                "คุมไฮไลต์ ทำเงาให้เย็นเล็กน้อย และเลี่ยงทำวัตถุเป็นกลางให้กลายเป็นน้ำเงิน",
                "คงความสว่างของแฟลชตรงและคอนทราสต์กลางภาพให้คม เพิ่มขอบมืดหลังตรวจใบหน้าและตัวอักษร",
                "ยกโทนมืดที่สุดเบา ๆ ลดคอนทราสต์แข็ง และลดความจัดของสีโดยไม่ทำให้รายละเอียดสำคัญจาง",
            ),
            (
                "ปกป้องไฮไลต์สว่างก่อนและดูว่าพื้นที่สว่างที่สุดยังคงรายละเอียดที่ใช้ได้หรือไม่",
                "ตั้งค่าแสงและไวต์บาลานซ์ก่อนอารมณ์ เกรน หรือเอฟเฟกต์ตกแต่ง",
                "อย่ายกเงาแรงเกินไป ตรวจนอยส์และรอยด่างสีที่ขนาดดูสุดท้าย",
            ),
            (
                "ปิดการเพิ่มเกรนและใช้แสง สี และคอนทราสต์สร้างลุค",
                "เพิ่มเกรนละเอียดช่วงท้าย แล้วตรวจท้องฟ้าเรียบ ผิว และตัวอักษรที่ขนาดปกติ",
                "ใช้เกรนโดยตั้งใจหลังแก้ฐานเท่านั้น ลดลงหากใบหน้า รายละเอียดเล็ก หรือพื้นผิวงานพิมพ์ดูรบกวน",
            ),
            (
                "แก้ฟุ้งสีที่ชัดเจนก่อน แล้วรักษาสีขาวและวัตถุคุ้นเคยให้ดูน่าเชื่อ",
                "เพิ่มความอุ่นทีละน้อยและตรวจสีขาว ผิว และแสงในอาคารก่อนส่งออก",
                "ทำภาพให้เย็นทีละน้อย รักษาไฮไลต์และวัตถุเป็นกลางไม่ให้ฟ้าผิดธรรมชาติ",
            ),
            (
                "ตัดสินผลที่ขนาดดูจริงและเทียบกับต้นฉบับที่เก็บไว้",
                "เลือกงานอ้างอิงหนึ่งชิ้น เทียบทั้งชุด และแก้ตัวที่ผิดแทนการซ้อนเอฟเฟกต์เพิ่ม",
                "ดูตัวอย่างการครอบตัดและขนาดพิมพ์ที่ตั้งใจ ความสว่างจอและเกรนที่เพิ่มอาจดูต่างบนกระดาษ",
            ),
        ),
        boundary=(
            "นี่คือลำดับการแก้ไข ไม่ใช่พรีเซ็ต การวิเคราะห์ภาพ หรือคำสัญญาว่าจะเข้ากับฟิล์มชนิดใด "
            "มันมองไม่เห็นแสง ใบหน้า สี โฟกัส นอยส์ ช่วงไดนามิก หรือสภาพผลลัพธ์"
        ),
        review=(
            "สี่ข้อควรตรวจก่อนส่งออก",
            "เก็บต้นฉบับที่ไม่แตะต้องหรือเส้นทางการแก้ไขที่ย้อนกลับได้",
            "ปรับทีละการเปลี่ยนแปลงเล็กและเทียบที่ขนาดดูปกติ",
            "ตรวจไฮไลต์ เงา สีที่คุ้นเคย และคนก่อนเพิ่มพื้นผิว",
            "สำหรับชุดภาพ ให้เทียบทุกเฟรมพร้อมกันและแก้ตัวที่ผิดก่อนส่งออก",
        ),
        sources=(
            "บริบทการแก้ไขทางการของ Apple ไม่ใช่การรับรอง",
            "Apple บันทึกการแก้ไขรูปและวิดีโอบน iPhone และการย้อนรายการที่แก้แล้วกลับเป็นต้นฉบับ โปรดดูขั้นตอนปัจจุบันสำหรับ iOS ของคุณ",
            "Apple: แก้ไขรูปและวิดีโอบน iPhone",
            "Apple: เลิกทำและย้อนการแก้ไขรูปบน iPhone",
        ),
        webmcp=(
            "ตัวอย่าง API เชิงคำสั่ง WebMCP ของ Chrome",
            "สร้างลำดับการแก้ไขเชิงคุณภาพแบบกำหนดแน่นอนจากตัวเลือกสไตล์ที่มีขอบเขตเท่านั้น ไม่รับหรือเข้าถึงรูป ไฟล์ เมทาดาทา กล้อง คลังภาพ บัญชี หรือข้อความอิสระ ไม่วิเคราะห์ภาพหรือรับประกันผล",
        ),
        app=(
            "อยากดูตัวอย่างลุคฟิล์มบนเครื่องโดยตรงไหม?",
            "PhotoCream Pro เป็นทางเลือก หน้า App Store ปัจจุบันอธิบายลุคมากกว่า 100 แบบ เกรน halation light leak bloom vignette ตัวอย่างสด และการควบคุมแสง/สี ประมวลผลบนเครื่องโดยไม่ต้องมีบัญชีหรืออัปโหลด ดาวน์โหลดฟรีพร้อมปลดล็อกครั้งเดียว โปรดดูหน้าปัจจุบันเพื่อความพร้อมและฟีเจอร์ที่แน่นอน ตัววางแผนนี้ทำงานได้โดยไม่ต้องใช้แอป",
            "ดู PhotoCream Pro บน App Store",
        ),
        faq=(
            "คำถามเกี่ยวกับการวางแผนลุคฟิล์ม",
            (
                (
                    "หน้านี้รับหรือดูรูปของฉันไหม?",
                    "ไม่ มันรับเพียงตัวเลือกสไตล์ที่มีขอบเขต และไม่เคยรับรูป ไฟล์ หรือเมทาดาทา",
                ),
                (
                    "สูตรนี้จะจำลองฟิล์มชนิดใดชนิดหนึ่งได้ไหม?",
                    "ไม่ มันให้ลำดับเริ่มต้นและไม่อ้างความแม่นยำหรือผลลัพธ์",
                ),
                (
                    "ฉันเลิกทำการแก้ไขใน Apple Photos ได้ไหม?",
                    "Apple บันทึกการย้อนรูปหรือวิดีโอที่แก้แล้วกลับเป็นต้นฉบับ โปรดยืนยันขั้นตอนปัจจุบันสำหรับ iOS ของคุณ",
                ),
            ),
        ),
        footer="เฉพาะความชอบที่มีขอบเขต · ไม่เข้าถึงรูป · ไม่วิเคราะห์ภาพ · ไม่รับประกันผล",
        inline="วางแผนสูตรลุคฟิล์มส่วนตัวก่อนเลือกโปรแกรมแก้ไข",
        index=(
            "ตัววางแผนสูตรลุคฟิล์มแบบส่วนตัว",
            "เลือกทิศทางฟิล์มและรับลำดับการแก้ไขที่ย้อนกลับได้โดยไม่อัปโหลดหรือวิเคราะห์รูป",
        ),
    ),
    "id": _copy(
        meta=(
            "Perencana Resep Tampilan Film Pribadi | Tanpa Unggah Foto",
            "Ubah preferensi gaya yang terbatas menjadi urutan penyuntingan yang dapat dibalik tanpa mengunggah, memindai, menganalisis, atau menyimpan foto.",
            "Alat gratis",
            "English",
            "Gratis · tanpa masukan foto · tanpa janji hasil",
            "Perencana resep tampilan film pribadi",
            "Pilih arah visual, kondisi pencahayaan, dan preferensi penyelesaian. Halaman mengembalikan urutan awal, bukan preset persis atau hasil yang dijamin.",
        ),
        badges=(
            "Tanpa foto, berkas, atau metadata",
            "Tanpa akses kamera, galeri, atau akun",
            "Tanpa unggahan, penyimpanan, atau analisis",
            "Tanpa jaminan kualitas atau hasil",
        ),
        planner=(
            "Bangun resep awal yang dapat dibalik",
            "Saran bersifat kualitatif dan bergantung pada gambar sumber, layar, editor, dan ukuran akhir. Pratinjau setiap perubahan dan simpan aslinya.",
        ),
        labels=(
            "Arah visual",
            "Pencahayaan sumber",
            "Preferensi grain",
            "Arah warna",
            "Penggunaan akhir",
        ),
        options=(
            (
                "Film bersih",
                "35mm hangat",
                "Sinema dingin",
                "Flash kamera sekali pakai",
                "Vintage pudar",
            ),
            ("Adegan terang", "Cahaya seimbang", "Cahaya redup"),
            ("Tanpa grain tambahan", "Grain halus", "Grain terlihat"),
            ("Netral", "Lebih hangat", "Lebih dingin"),
            ("Foto tunggal", "Seri yang serasi", "Cetak"),
        ),
        natural=(
            "Jaga warna kulit tetap alami saat ada orang",
            "Jika ada orang, bandingkan kulit, mata, dan rambut sebelum dan sesudah setiap langkah warna.",
            "Tidak ada preferensi khusus wajah yang dipilih; tetap periksa orang dan referensi warna penting sebelum ekspor.",
        ),
        results=(
            "Buat resep pribadi",
            "Arah awal",
            "Urutan penyesuaian",
            "Pemeriksaan konsistensi",
            "Batas resep",
        ),
        notes=(
            (
                "Jaga kontras tetap terkendali, warna seimbang, dan sorotan lembut; tambahkan stilisasi hanya setelah dasar terlihat stabil.",
                "Utamakan midtone hangat, kontras sedang, dan sorotan lembut; perhatikan oranye dan kulit sebelum menambah efek.",
                "Jaga sorotan terkendali, dinginkan bayangan sedikit, dan hindari mengubah objek netral menjadi biru.",
                "Pertahankan kecerahan flash langsung dan kontras tengah yang tajam; tambahkan gelap tepi hanya setelah memeriksa wajah dan teks.",
                "Angkat nada paling gelap dengan lembut, kurangi kontras keras, dan redam warna tanpa memudarkan detail penting.",
            ),
            (
                "Lindungi sorotan terang dulu dan nilai apakah area paling terang masih menyimpan detail berguna.",
                "Atur pencahayaan dan white balance sebelum suasana, grain, atau efek dekoratif.",
                "Hindari mengangkat bayangan secara agresif; periksa noise dan bercak warna pada ukuran tampilan akhir.",
            ),
            (
                "Biarkan grain tambahan mati dan gunakan cahaya, warna, serta kontras untuk tampilannya.",
                "Tambahkan grain halus di akhir, lalu periksa langit halus, kulit, dan teks pada ukuran normal.",
                "Gunakan grain sengaja hanya setelah suntingan dasar; kurangi bila wajah, detail kecil, atau tekstur cetak mengganggu.",
            ),
            (
                "Perbaiki dominasi warna yang jelas dulu, lalu jaga putih dan objek familier tetap meyakinkan.",
                "Tambahkan kehangatan bertahap dan periksa ulang putih, kulit, dan pencahayaan dalam ruang sebelum ekspor.",
                "Dinginkan gambar bertahap; jaga sorotan dan objek netral agar tidak menjadi biru tak wajar.",
            ),
            (
                "Nilai hasil pada ukuran tampilan sebenarnya dan bandingkan dengan asli yang disimpan.",
                "Pilih satu suntingan acuan, bandingkan seluruh urutan, dan perbaiki yang menyimpang alih-alih menumpuk efek.",
                "Pratinjau potongan dan ukuran cetak yang dituju; kecerahan layar dan grain tambahan bisa berbeda di kertas.",
            ),
        ),
        boundary=(
            "Ini adalah urutan penyuntingan, bukan preset, analisis gambar, atau janji kecocokan stok film. "
            "Ia tidak dapat melihat pencahayaan, wajah, warna, fokus, noise, rentang dinamis, atau kondisi keluaran."
        ),
        review=(
            "Empat pemeriksaan sebelum ekspor",
            "Simpan asli yang belum disentuh atau jalur penyuntingan yang dapat dibalik.",
            "Terapkan satu perubahan kecil dalam satu waktu dan bandingkan pada ukuran tampilan normal.",
            "Periksa sorotan, bayangan, warna familier, dan orang sebelum menambah tekstur.",
            "Untuk seri, bandingkan semua bingkai bersama dan perbaiki yang menyimpang sebelum ekspor.",
        ),
        sources=(
            "Konteks penyuntingan resmi Apple, bukan dukungan",
            "Apple mendokumentasikan penyuntingan foto dan video di iPhone dan pengembalian item yang disunting ke aslinya. Periksa langkah terkini untuk versi iOS Anda.",
            "Apple: sunting foto dan video di iPhone",
            "Apple: batalkan dan kembalikan suntingan foto di iPhone",
        ),
        webmcp=(
            "Pratinjau API imperatif WebMCP Chrome",
            "Bangun urutan penyuntingan kualitatif deterministik hanya dari pilihan gaya terbatas. Jangan pernah menerima atau mengakses foto, berkas, metadata, kamera, galeri, akun, atau teks bebas; jangan pernah menganalisis gambar atau menjamin hasil.",
        ),
        app=(
            "Ingin pratinjau tampilan film langsung di perangkat?",
            "PhotoCream Pro bersifat opsional. Halaman App Store-nya saat ini menjelaskan 100+ tampilan, grain, halation, light leak, bloom, vignette, pratinjau langsung, dan kontrol cahaya/warna, diproses di perangkat tanpa akun atau unggahan. Gratis diunduh dengan buka kunci sekali bayar. Periksa halaman terkini untuk ketersediaan dan fitur pastinya. Perencana ini bekerja tanpa aplikasi.",
            "Lihat PhotoCream Pro di App Store",
        ),
        faq=(
            "Pertanyaan perencanaan tampilan film",
            (
                (
                    "Apakah halaman ini menerima atau memeriksa foto saya?",
                    "Tidak. Ia hanya menerima pilihan gaya terbatas dan tidak pernah menerima foto, berkas, atau metadata.",
                ),
                (
                    "Apakah resep ini akan menciptakan ulang stok film tertentu?",
                    "Tidak. Ia memberikan urutan awal dan tidak membuat klaim akurasi atau hasil.",
                ),
                (
                    "Bisakah saya membatalkan suntingan di Apple Photos?",
                    "Apple mendokumentasikan pengembalian foto atau video yang disunting ke aslinya; verifikasi langkah terkini untuk versi iOS Anda.",
                ),
            ),
        ),
        footer="Hanya preferensi terbatas · tanpa akses foto · tanpa analisis gambar · tanpa janji hasil",
        inline="Rencanakan resep tampilan film pribadi sebelum memilih editor",
        index=(
            "Perencana Resep Tampilan Film Pribadi",
            "Pilih arah film dan dapatkan urutan penyuntingan yang dapat dibalik tanpa mengunggah atau menganalisis foto.",
        ),
    ),
    "tr": _copy(
        meta=(
            "Özel Film Görünümü Reçetesi Planlayıcısı | Fotoğraf Yükleme Yok",
            "Bir fotoğrafı yüklemeden, taramadan, analiz etmeden veya saklamadan sınırlı stil tercihlerini geri alınabilir bir düzenleme sırasına dönüştürün.",
            "Ücretsiz araçlar",
            "English",
            "Ücretsiz · fotoğraf girişi yok · sonuç vaadi yok",
            "Özel film görünümü reçetesi planlayıcısı",
            "Bir görsel yön, ışık koşulu ve bitiş tercihi seçin. Sayfa bir başlangıç sırası döndürür, asla kesin bir ön ayar veya garantili sonuç değil.",
        ),
        badges=(
            "Fotoğraf, dosya veya meta veri yok",
            "Kamera, kitaplık veya hesap erişimi yok",
            "Yükleme, depolama veya analiz yok",
            "Kalite veya sonuç garantisi yok",
        ),
        planner=(
            "Geri alınabilir bir başlangıç reçetesi oluştur",
            "Öneriler nitelikseldir ve kaynak görüntüye, ekrana, editöre ve son boyuta bağlıdır. Her değişikliği önizleyin ve bir orijinali koruyun.",
        ),
        labels=(
            "Görsel yön",
            "Kaynak ışığı",
            "Gren tercihi",
            "Renk yönü",
            "Son kullanım",
        ),
        options=(
            (
                "Temiz film",
                "Sıcak 35mm",
                "Soğuk sinema",
                "Tek kullanımlık flaş",
                "Solmuş vintage",
            ),
            ("Aydınlık sahne", "Dengeli ışık", "Az ışık"),
            ("Eklenen gren yok", "İnce gren", "Görünür gren"),
            ("Nötr", "Daha sıcak", "Daha soğuk"),
            ("Tek fotoğraf", "Uyumlu seri", "Baskı"),
        ),
        natural=(
            "İnsanlar varken ten tonlarını doğal tutun",
            "İnsanlar varsa her renk adımından önce ve sonra teni, gözleri ve saçı karşılaştırın.",
            "Yüze özgü bir tercih seçilmedi; yine de dışa aktarmadan önce insanları ve önemli renk referanslarını kontrol edin.",
        ),
        results=(
            "Özel reçete oluştur",
            "Başlangıç yönü",
            "Ayarlama sırası",
            "Tutarlılık kontrolü",
            "Reçete sınırı",
        ),
        notes=(
            (
                "Kontrastı ölçülü, rengi dengeli ve parlaklıkları yumuşak tutun; stilizasyonu ancak taban stabil göründükten sonra ekleyin.",
                "Sıcak orta tonları, orta kontrastı ve yumuşak parlaklıkları tercih edin; efekt eklemeden önce turuncuları ve teni izleyin.",
                "Parlaklıkları kontrollü tutun, gölgeleri biraz soğutun ve nötr nesneleri maviye çevirmekten kaçının.",
                "Doğrudan flaş parlaklığını ve keskin merkez kontrastını koruyun; kenar kararmasını ancak yüzleri ve metni kontrol ettikten sonra ekleyin.",
                "En koyu tonları yumuşakça açın, sert kontrastı azaltın ve önemli detayı soldurmadan rengi yumuşatın.",
            ),
            (
                "Önce parlak parlaklıkları koruyun ve en açık alanların hâlâ kullanışlı detay tutup tutmadığını değerlendirin.",
                "Ruh hâli, gren veya dekoratif efektlerden önce pozlamayı ve beyaz dengesini ayarlayın.",
                "Gölgeleri agresif açmaktan kaçının; nihai görüntüleme boyutunda gürültüyü ve renk lekelerini kontrol edin.",
            ),
            (
                "Eklenen greni kapalı bırakın ve görünüm için ışığı, rengi ve kontrastı kullanın.",
                "İnce greni sona doğru ekleyin, sonra düz gökyüzünü, teni ve metni normal boyutta inceleyin.",
                "Kasıtlı greni yalnızca taban düzenlemeden sonra kullanın; yüzler, küçük detaylar veya baskı dokusu dikkat dağıtırsa azaltın.",
            ),
            (
                "Önce belirgin bir renk kaymasını düzeltin, sonra beyazları ve tanıdık nesneleri inandırıcı tutun.",
                "Sıcaklığı kademeli ekleyin ve dışa aktarmadan önce beyazları, teni ve iç mekân ışığını yeniden kontrol edin.",
                "Görüntüyü kademeli soğutun; parlaklıkların ve nötr nesnelerin doğal olmayan biçimde mavileşmesini önleyin.",
            ),
            (
                "Sonucu gerçek görüntüleme boyutunda değerlendirin ve korunan orijinalle karşılaştırın.",
                "Bir referans düzenleme seçin, tüm diziyi karşılaştırın ve daha fazla efekt yığmak yerine aykırıları düzeltin.",
                "Amaçlanan kırpmayı ve baskı boyutunu önizleyin; ekran parlaklığı ve eklenen gren kâğıtta farklı görünebilir.",
            ),
        ),
        boundary=(
            "Bu bir düzenleme sırasıdır; bir ön ayar, görüntü analizi veya film stoğu eşleşmesi vaadi değildir. "
            "Pozlamayı, yüzleri, rengi, odağı, gürültüyü, dinamik aralığı veya çıktı koşullarını göremez."
        ),
        review=(
            "Dışa aktarmadan önce dört kontrol",
            "Dokunulmamış bir orijinali veya geri alınabilir bir düzenleme yolunu koruyun.",
            "Her seferinde küçük bir değişiklik uygulayın ve normal görüntüleme boyutunda karşılaştırın.",
            "Doku eklemeden önce parlaklıkları, gölgeleri, tanıdık renkleri ve insanları kontrol edin.",
            "Bir seri için tüm kareleri birlikte karşılaştırın ve dışa aktarmadan önce aykırıları düzeltin.",
        ),
        sources=(
            "Resmi Apple düzenleme bağlamı, bir onay değil",
            "Apple, iPhone'da fotoğraf ve video düzenlemeyi ve düzenlenmiş bir öğeyi orijinaline döndürmeyi belgeler. iOS sürümünüz için güncel adımları kontrol edin.",
            "Apple: iPhone'da fotoğraf ve video düzenleyin",
            "Apple: iPhone'da fotoğraf düzenlemelerini geri alın ve döndürün",
        ),
        webmcp=(
            "Chrome zorunlu WebMCP API önizlemesi",
            "Yalnızca sınırlı stil seçimlerinden belirlenimci niteliksel bir düzenleme sırası oluşturun. Fotoğrafları, dosyaları, meta verileri, kameraları, kitaplıkları, hesapları veya serbest metni asla almayın veya bunlara erişmeyin; asla bir görüntüyü analiz etmeyin veya sonuç garanti etmeyin.",
        ),
        app=(
            "Film görünümlerini doğrudan cihazınızda önizlemek ister misiniz?",
            "PhotoCream Pro isteğe bağlıdır. Mevcut App Store sayfası, 100'den fazla görünümü, greni, halation'ı, ışık sızıntılarını, bloom'u, vinyet'i, canlı önizlemeyi ve ışık/renk denetimlerini tanımlar; hesap veya yükleme olmadan cihazda işlenir. Tek seferlik kilit açmayla ücretsiz indirilir. Kesin kullanılabilirlik ve özellikler için güncel sayfaya bakın. Bu planlayıcı uygulama olmadan çalışır.",
            "PhotoCream Pro'yu App Store'da görüntüleyin",
        ),
        faq=(
            "Film görünümü planlama soruları",
            (
                (
                    "Bu sayfa fotoğrafımı alıyor veya inceliyor mu?",
                    "Hayır. Yalnızca sınırlı stil seçimlerini kabul eder ve asla bir fotoğraf, dosya veya meta veri almaz.",
                ),
                (
                    "Bu reçete belirli bir film stoğunu yeniden yaratır mı?",
                    "Hayır. Bir başlangıç sırası sunar ve doğruluk veya sonuç iddiasında bulunmaz.",
                ),
                (
                    "Apple Photos'ta bir düzenlemeyi geri alabilir miyim?",
                    "Apple, düzenlenmiş bir fotoğrafı veya videoyu orijinaline döndürmeyi belgeler; iOS sürümünüz için güncel adımları doğrulayın.",
                ),
            ),
        ),
        footer="Yalnızca sınırlı tercihler · fotoğraf erişimi yok · görüntü analizi yok · sonuç vaadi yok",
        inline="Bir editör seçmeden önce özel bir film görünümü reçetesi planlayın",
        index=(
            "Özel Film Görünümü Reçetesi Planlayıcısı",
            "Bir film yönü seçin ve fotoğraf yüklemeden veya analiz etmeden geri alınabilir bir düzenleme sırası alın.",
        ),
    ),
    "hi": _copy(
        meta=(
            "निजी फ़िल्म लुक रेसिपी योजनाकार | फ़ोटो अपलोड नहीं",
            "फ़ोटो अपलोड, स्कैन, विश्लेषण या संग्रह किए बिना सीमित शैली-प्राथमिकताओं को एक प्रतिवर्ती संपादन क्रम में बदलें।",
            "मुफ़्त उपकरण",
            "English",
            "मुफ़्त · कोई फ़ोटो इनपुट नहीं · कोई परिणाम वादा नहीं",
            "निजी फ़िल्म लुक रेसिपी योजनाकार",
            "एक दृश्य दिशा, प्रकाश स्थिति और फ़िनिश प्राथमिकता चुनें। पृष्ठ एक आरंभिक क्रम देता है, कभी कोई निश्चित प्रीसेट या गारंटीशुदा परिणाम नहीं।",
        ),
        badges=(
            "कोई फ़ोटो, फ़ाइल या मेटाडेटा नहीं",
            "कोई कैमरा, लाइब्रेरी या खाता पहुँच नहीं",
            "कोई अपलोड, संग्रहण या विश्लेषण नहीं",
            "कोई गुणवत्ता या परिणाम गारंटी नहीं",
        ),
        planner=(
            "एक प्रतिवर्ती आरंभिक रेसिपी बनाएँ",
            "सुझाव गुणात्मक हैं और स्रोत छवि, स्क्रीन, संपादक और अंतिम आकार पर निर्भर करते हैं। हर बदलाव का पूर्वावलोकन करें और एक मूल प्रति सुरक्षित रखें।",
        ),
        labels=(
            "दृश्य दिशा",
            "स्रोत प्रकाश",
            "ग्रेन प्राथमिकता",
            "रंग दिशा",
            "अंतिम उपयोग",
        ),
        options=(
            (
                "साफ़ फ़िल्म",
                "गर्म 35mm",
                "ठंडा सिनेमैटिक",
                "डिस्पोज़ेबल फ़्लैश",
                "फीका विंटेज",
            ),
            ("उजला दृश्य", "संतुलित प्रकाश", "कम रोशनी"),
            ("कोई अतिरिक्त ग्रेन नहीं", "महीन ग्रेन", "दिखने वाला ग्रेन"),
            ("तटस्थ", "अधिक गर्म", "अधिक ठंडा"),
            ("एक फ़ोटो", "मेल खाती शृंखला", "प्रिंट"),
        ),
        natural=(
            "लोग हों तो त्वचा के रंग स्वाभाविक रखें",
            "यदि लोग हों तो हर रंग-चरण से पहले और बाद में त्वचा, आँखें और बाल तुलना करें।",
            "चेहरे-विशेष प्राथमिकता नहीं चुनी गई; फिर भी निर्यात से पहले लोगों और महत्वपूर्ण रंग-संदर्भों की जाँच करें।",
        ),
        results=(
            "निजी रेसिपी बनाएँ",
            "आरंभिक दिशा",
            "समायोजन क्रम",
            "एकरूपता जाँच",
            "रेसिपी सीमा",
        ),
        notes=(
            (
                "कंट्रास्ट संयमित, रंग संतुलित और हाइलाइट कोमल रखें; आधार स्थिर दिखने के बाद ही स्टाइल जोड़ें।",
                "गर्म मध्य-टोन, मध्यम कंट्रास्ट और कोमल हाइलाइट चुनें; प्रभाव जोड़ने से पहले नारंगी और त्वचा पर नज़र रखें।",
                "हाइलाइट नियंत्रित रखें, छायाएँ थोड़ी ठंडी करें और तटस्थ वस्तुओं को नीला करने से बचें।",
                "सीधे फ़्लैश की चमक और तीखा केंद्रीय कंट्रास्ट बनाए रखें; चेहरों और टेक्स्ट की जाँच के बाद ही किनारा-अंधकार जोड़ें।",
                "सबसे गहरे टोन कोमलता से खोलें, कठोर कंट्रास्ट घटाएँ और महत्वपूर्ण विवरण मिटाए बिना रंग नरम करें।",
            ),
            (
                "पहले चमकीले हाइलाइट सुरक्षित रखें और देखें कि सबसे उजले क्षेत्रों में अब भी उपयोगी विवरण है या नहीं।",
                "मूड, ग्रेन या सजावटी प्रभावों से पहले एक्सपोज़र और व्हाइट बैलेंस ठीक करें।",
                "छायाएँ आक्रामक रूप से न खोलें; अंतिम देखने के आकार पर शोर और रंग-धब्बे जाँचें।",
            ),
            (
                "अतिरिक्त ग्रेन बंद रखें और लुक के लिए प्रकाश, रंग और कंट्रास्ट का उपयोग करें।",
                "महीन ग्रेन अंत में जोड़ें, फिर सपाट आसमान, त्वचा और टेक्स्ट सामान्य आकार पर जाँचें।",
                "जानबूझकर ग्रेन केवल आधार-संपादन के बाद लगाएँ; चेहरे, छोटे विवरण या प्रिंट बनावट भटकाएँ तो घटाएँ।",
            ),
            (
                "पहले कोई स्पष्ट रंग-विचलन ठीक करें, फिर सफ़ेद और परिचित वस्तुएँ विश्वसनीय रखें।",
                "गर्माहट धीरे-धीरे जोड़ें और निर्यात से पहले सफ़ेद, त्वचा और भीतरी प्रकाश दोबारा जाँचें।",
                "छवि धीरे-धीरे ठंडी करें; हाइलाइट और तटस्थ वस्तुओं को अस्वाभाविक नीला होने से रोकें।",
            ),
            (
                "परिणाम वास्तविक देखने के आकार पर परखें और सुरक्षित मूल से तुलना करें।",
                "एक संदर्भ-संपादन चुनें, पूरी शृंखला तुलना करें और अधिक प्रभाव थोपने के बजाय विचलित फ़्रेम ठीक करें।",
                "इच्छित क्रॉप और प्रिंट आकार का पूर्वावलोकन करें; स्क्रीन की चमक और जोड़ा ग्रेन काग़ज़ पर अलग दिख सकता है।",
            ),
        ),
        boundary=(
            "यह एक संपादन क्रम है; कोई प्रीसेट, छवि-विश्लेषण या फ़िल्म-स्टॉक मिलान का वादा नहीं। "
            "यह एक्सपोज़र, चेहरे, रंग, फ़ोकस, शोर, डायनामिक रेंज या आउटपुट स्थितियाँ नहीं देख सकता।"
        ),
        review=(
            "निर्यात से पहले चार जाँचें",
            "एक अछूती मूल प्रति या प्रतिवर्ती संपादन-पथ सुरक्षित रखें।",
            "हर बार एक छोटा बदलाव लागू करें और सामान्य देखने के आकार पर तुलना करें।",
            "बनावट जोड़ने से पहले हाइलाइट, छाया, परिचित रंग और लोग जाँचें।",
            "शृंखला के लिए सभी फ़्रेम एक साथ तुलना करें और निर्यात से पहले विचलित फ़्रेम ठीक करें।",
        ),
        sources=(
            "आधिकारिक Apple संपादन संदर्भ, कोई समर्थन नहीं",
            "Apple iPhone पर फ़ोटो और वीडियो संपादन तथा संपादित आइटम को मूल पर लौटाने का दस्तावेज़ देता है। अपने iOS संस्करण के लिए वर्तमान चरण जाँचें।",
            "Apple: iPhone पर फ़ोटो और वीडियो संपादित करें",
            "Apple: iPhone पर फ़ोटो-संपादन पूर्ववत करें और मूल पर लौटाएँ",
        ),
        webmcp=(
            "Chrome अनिवार्य WebMCP API पूर्वावलोकन",
            "केवल सीमित शैली-चयनों से एक निर्धारित गुणात्मक संपादन क्रम बनाएँ। फ़ोटो, फ़ाइलें, मेटाडेटा, कैमरा, लाइब्रेरी, खाते या मुक्त टेक्स्ट कभी न लें और न उन तक पहुँचें; कभी किसी छवि का विश्लेषण न करें और न परिणाम की गारंटी दें।",
        ),
        app=(
            "फ़िल्म लुक सीधे अपने डिवाइस पर पूर्वावलोकन करना चाहते हैं?",
            "PhotoCream Pro वैकल्पिक है। वर्तमान App Store पृष्ठ 100+ लुक, ग्रेन, हैलेशन, लाइट लीक, ब्लूम, विनेट, लाइव पूर्वावलोकन और प्रकाश/रंग नियंत्रण का वर्णन करता है; बिना खाते या अपलोड के डिवाइस पर प्रोसेस होता है। एक-बार अनलॉक के साथ मुफ़्त डाउनलोड। सटीक उपलब्धता और विशेषताओं के लिए वर्तमान पृष्ठ देखें। यह योजनाकार ऐप के बिना काम करता है।",
            "App Store पर PhotoCream Pro देखें",
        ),
        faq=(
            "फ़िल्म लुक योजना प्रश्न",
            (
                (
                    "क्या यह पृष्ठ मेरी फ़ोटो लेता या देखता है?",
                    "नहीं। यह केवल सीमित शैली-चयन स्वीकार करता है और कभी फ़ोटो, फ़ाइल या मेटाडेटा नहीं लेता।",
                ),
                (
                    "क्या यह रेसिपी किसी विशेष फ़िल्म स्टॉक को पुनः बनाती है?",
                    "नहीं। यह एक आरंभिक क्रम देती है और सटीकता या परिणाम का दावा नहीं करती।",
                ),
                (
                    "क्या मैं Apple Photos में संपादन पूर्ववत कर सकता/सकती हूँ?",
                    "Apple संपादित फ़ोटो या वीडियो को मूल पर लौटाने का दस्तावेज़ देता है; अपने iOS संस्करण के वर्तमान चरण सत्यापित करें।",
                ),
            ),
        ),
        footer="केवल सीमित प्राथमिकताएँ · कोई फ़ोटो पहुँच नहीं · कोई छवि-विश्लेषण नहीं · कोई परिणाम वादा नहीं",
        inline="कोई संपादक चुनने से पहले एक निजी फ़िल्म लुक रेसिपी योजना बनाएँ",
        index=(
            "निजी फ़िल्म लुक रेसिपी योजनाकार",
            "एक फ़िल्म दिशा चुनें और बिना फ़ोटो अपलोड या विश्लेषण के एक प्रतिवर्ती संपादन क्रम पाएँ।",
        ),
    ),
    "ms": _copy(
        meta=(
            "Perancang Resipi Rupa Filem Peribadi | Tiada Muat Naik Foto",
            "Tukar keutamaan gaya terhad kepada susunan suntingan boleh balik tanpa memuat naik, mengimbas, menganalisis atau menyimpan foto.",
            "Alat percuma",
            "English",
            "Percuma · tiada input foto · tiada janji hasil",
            "Perancang resipi rupa filem peribadi",
            "Pilih arah visual, keadaan cahaya dan keutamaan kemasan. Halaman ini memulangkan susunan permulaan, bukan praset muktamad atau hasil terjamin.",
        ),
        badges=(
            "Tiada foto, fail atau metadata",
            "Tiada akses kamera, pustaka atau akaun",
            "Tiada muat naik, storan atau analisis",
            "Tiada jaminan kualiti atau hasil",
        ),
        planner=(
            "Bina resipi permulaan yang boleh balik",
            "Cadangan bersifat kualitatif dan bergantung pada imej sumber, skrin, penyunting dan saiz akhir. Pratonton setiap perubahan dan simpan salinan asal.",
        ),
        labels=(
            "Arah visual",
            "Cahaya sumber",
            "Keutamaan grain",
            "Arah warna",
            "Kegunaan akhir",
        ),
        options=(
            (
                "Filem bersih",
                "35mm hangat",
                "Sinematik sejuk",
                "Denyar pakai buang",
                "Vintaj pudar",
            ),
            ("Adegan cerah", "Cahaya seimbang", "Cahaya malap"),
            ("Tiada grain tambahan", "Grain halus", "Grain kelihatan"),
            ("Neutral", "Lebih hangat", "Lebih sejuk"),
            ("Satu foto", "Siri sepadan", "Cetakan"),
        ),
        natural=(
            "Kekalkan warna kulit semula jadi apabila ada orang",
            "Jika ada orang, bandingkan kulit, mata dan rambut sebelum dan selepas setiap langkah warna.",
            "Tiada keutamaan khusus wajah dipilih; namun semak orang dan rujukan warna penting sebelum mengeksport.",
        ),
        results=(
            "Bina resipi peribadi",
            "Arah permulaan",
            "Susunan pelarasan",
            "Semakan konsistensi",
            "Sempadan resipi",
        ),
        notes=(
            (
                "Kekalkan kontras sederhana, warna seimbang dan sorotan lembut; tambah stilisasi hanya selepas asas kelihatan stabil.",
                "Pilih ton tengah hangat, kontras sederhana dan sorotan lembut; perhatikan jingga dan kulit sebelum menambah kesan.",
                "Kawal sorotan, sejukkan bayang sedikit dan elakkan menjadikan objek neutral biru.",
                "Kekalkan kecerahan denyar terus dan kontras tengah yang tajam; tambah gelap tepi hanya selepas menyemak wajah dan teks.",
                "Buka ton paling gelap dengan lembut, kurangkan kontras keras dan lembutkan warna tanpa memudarkan butiran penting.",
            ),
            (
                "Lindungi sorotan cerah dahulu dan nilai sama ada kawasan paling terang masih menyimpan butiran berguna.",
                "Betulkan dedahan dan imbangan putih sebelum mood, grain atau kesan hiasan.",
                "Elakkan membuka bayang secara agresif; semak hingar dan tompok warna pada saiz tontonan akhir.",
            ),
            (
                "Biarkan grain tambahan dimatikan dan gunakan cahaya, warna serta kontras untuk rupa.",
                "Tambah grain halus menjelang akhir, kemudian periksa langit rata, kulit dan teks pada saiz biasa.",
                "Guna grain sengaja hanya selepas suntingan asas; kurangkan jika wajah, butiran kecil atau tekstur cetakan mengganggu.",
            ),
            (
                "Betulkan sisihan warna yang jelas dahulu, kemudian kekalkan putih dan objek biasa supaya meyakinkan.",
                "Tambah kehangatan secara beransur dan semak semula putih, kulit dan cahaya dalaman sebelum mengeksport.",
                "Sejukkan imej secara beransur; elakkan sorotan dan objek neutral menjadi biru secara tidak semula jadi.",
            ),
            (
                "Nilai hasil pada saiz tontonan sebenar dan bandingkan dengan salinan asal yang disimpan.",
                "Pilih satu suntingan rujukan, bandingkan keseluruhan siri dan betulkan bingkai terpesong daripada menimbun lebih banyak kesan.",
                "Pratonton pemotongan dan saiz cetakan yang dirancang; kecerahan skrin dan grain tambahan mungkin berbeza di atas kertas.",
            ),
        ),
        boundary=(
            "Ini susunan suntingan; bukan praset, analisis imej atau janji padanan stok filem. "
            "Ia tidak dapat melihat dedahan, wajah, warna, fokus, hingar, julat dinamik atau keadaan output."
        ),
        review=(
            "Empat semakan sebelum mengeksport",
            "Simpan salinan asal yang tidak disentuh atau laluan suntingan boleh balik.",
            "Buat satu perubahan kecil setiap kali dan bandingkan pada saiz tontonan biasa.",
            "Semak sorotan, bayang, warna biasa dan orang sebelum menambah tekstur.",
            "Untuk satu siri, bandingkan semua bingkai bersama dan betulkan yang terpesong sebelum mengeksport.",
        ),
        sources=(
            "Konteks suntingan rasmi Apple, bukan sokongan",
            "Apple mendokumenkan penyuntingan foto dan video di iPhone serta mengembalikan item yang disunting kepada asal. Semak langkah semasa untuk versi iOS anda.",
            "Apple: sunting foto dan video di iPhone",
            "Apple: buat asal dan kembalikan suntingan foto di iPhone",
        ),
        webmcp=(
            "Pratonton API imperatif WebMCP Chrome",
            "Bina susunan suntingan kualitatif berketentuan daripada pilihan gaya terhad sahaja. Jangan sekali-kali mengambil atau mengakses foto, fail, metadata, kamera, pustaka, akaun atau teks bebas; jangan sekali-kali menganalisis imej atau menjamin hasil.",
        ),
        app=(
            "Mahu pratonton rupa filem terus pada peranti anda?",
            "PhotoCream Pro adalah pilihan. Halaman App Store semasa menerangkan 100+ rupa, grain, halation, light leak, bloom, vignette, pratonton langsung dan kawalan cahaya/warna; diproses pada peranti tanpa akaun atau muat naik. Muat turun percuma dengan buka kunci sekali. Rujuk halaman semasa untuk ketersediaan dan ciri tepat. Perancang ini berfungsi tanpa aplikasi.",
            "Lihat PhotoCream Pro di App Store",
        ),
        faq=(
            "Soalan perancangan rupa filem",
            (
                (
                    "Adakah halaman ini mengambil atau melihat foto saya?",
                    "Tidak. Ia hanya menerima pilihan gaya terhad dan tidak sekali-kali mengambil foto, fail atau metadata.",
                ),
                (
                    "Adakah resipi ini mencipta semula stok filem tertentu?",
                    "Tidak. Ia memberi susunan permulaan dan tidak mendakwa ketepatan atau hasil.",
                ),
                (
                    "Bolehkah saya membuat asal suntingan dalam Apple Photos?",
                    "Apple mendokumenkan pengembalian foto atau video yang disunting kepada asal; sahkan langkah semasa untuk versi iOS anda.",
                ),
            ),
        ),
        footer="Keutamaan terhad sahaja · tiada akses foto · tiada analisis imej · tiada janji hasil",
        inline="Rancang resipi rupa filem peribadi sebelum memilih penyunting",
        index=(
            "Perancang Resipi Rupa Filem Peribadi",
            "Pilih arah filem dan dapatkan susunan suntingan boleh balik tanpa memuat naik atau menganalisis foto.",
        ),
    ),
    "ru": _copy(
        meta=(
            "Приватный планировщик плёночного лука | Без загрузки фото",
            "Превратите ограниченные стилевые предпочтения в обратимую последовательность правок без загрузки, сканирования, анализа или хранения фото.",
            "Бесплатные инструменты",
            "English",
            "Бесплатно · без ввода фото · без обещаний результата",
            "Приватный планировщик плёночного лука",
            "Выберите визуальное направление, условия света и предпочтение финиша. Страница возвращает стартовую последовательность — никогда не готовый пресет и не гарантированный результат.",
        ),
        badges=(
            "Без фото, файлов и метаданных",
            "Без доступа к камере, библиотеке и аккаунтам",
            "Без загрузок, хранения и анализа",
            "Без гарантий качества или результата",
        ),
        planner=(
            "Составить обратимый стартовый рецепт",
            "Советы качественные и зависят от исходного снимка, экрана, редактора и финального размера. Просматривайте каждое изменение и сохраняйте оригинал.",
        ),
        labels=(
            "Визуальное направление",
            "Свет источника",
            "Предпочтение зерна",
            "Направление цвета",
            "Финальное использование",
        ),
        options=(
            (
                "Чистая плёнка",
                "Тёплые 35мм",
                "Холодное кино",
                "Одноразовая вспышка",
                "Выцветший винтаж",
            ),
            ("Яркая сцена", "Сбалансированный свет", "Мало света"),
            ("Без добавленного зерна", "Тонкое зерно", "Заметное зерно"),
            ("Нейтрально", "Теплее", "Холоднее"),
            ("Одно фото", "Согласованная серия", "Печать"),
        ),
        natural=(
            "Сохраняйте естественные тона кожи, если в кадре люди",
            "Если есть люди, сравнивайте кожу, глаза и волосы до и после каждого цветового шага.",
            "Предпочтение для лиц не выбрано; всё же проверьте людей и важные цветовые ориентиры перед экспортом.",
        ),
        results=(
            "Создать приватный рецепт",
            "Стартовое направление",
            "Порядок корректировок",
            "Проверка согласованности",
            "Граница рецепта",
        ),
        notes=(
            (
                "Держите контраст умеренным, цвет сбалансированным, света мягкими; добавляйте стилизацию только после стабильной базы.",
                "Предпочитайте тёплые средние тона, средний контраст и мягкие света; следите за оранжевым и кожей перед эффектами.",
                "Контролируйте света, слегка охладите тени и не давайте нейтральным объектам синеть.",
                "Сохраните яркость прямой вспышки и резкий центральный контраст; затемнение краёв — только после проверки лиц и текста.",
                "Мягко приоткройте самые тёмные тона, уменьшите жёсткий контраст и смягчите цвет, не стирая важные детали.",
            ),
            (
                "Сначала защитите яркие света и оцените, сохраняют ли самые светлые зоны полезные детали.",
                "Настройте экспозицию и баланс белого до настроения, зерна и декоративных эффектов.",
                "Не открывайте тени агрессивно; проверьте шум и цветовые пятна в финальном размере просмотра.",
            ),
            (
                "Оставьте добавленное зерно выключенным и стройте лук светом, цветом и контрастом.",
                "Добавляйте тонкое зерно ближе к концу, затем проверьте ровное небо, кожу и текст в обычном размере.",
                "Выраженное зерно — только после базовой правки; уменьшите, если лица, мелкие детали или фактура печати отвлекают.",
            ),
            (
                "Сначала исправьте явный цветовой сдвиг, затем держите белое и знакомые объекты правдоподобными.",
                "Добавляйте теплоту постепенно и перед экспортом перепроверьте белое, кожу и внутренний свет.",
                "Охлаждайте изображение постепенно; не давайте светам и нейтральным объектам неестественно синеть.",
            ),
            (
                "Оценивайте результат в реальном размере просмотра и сравнивайте с сохранённым оригиналом.",
                "Выберите эталонную правку, сравните всю серию и исправьте выбивающиеся кадры вместо наслаивания эффектов.",
                "Просмотрите планируемый кадр и размер печати; яркость экрана и добавленное зерно на бумаге выглядят иначе.",
            ),
        ),
        boundary=(
            "Это последовательность правок, а не пресет, не анализ изображения и не обещание совпадения с плёнкой. "
            "Она не видит экспозицию, лица, цвет, фокус, шум, динамический диапазон или условия вывода."
        ),
        review=(
            "Четыре проверки перед экспортом",
            "Сохраняйте нетронутый оригинал или обратимый путь правок.",
            "Вносите по одному небольшому изменению и сравнивайте в обычном размере просмотра.",
            "Перед добавлением фактуры проверьте света, тени, знакомые цвета и людей.",
            "Для серии сравните все кадры вместе и исправьте выбивающиеся перед экспортом.",
        ),
        sources=(
            "Официальный контекст редактирования Apple, а не одобрение",
            "Apple документирует редактирование фото и видео на iPhone и возврат отредактированного к оригиналу. Проверьте актуальные шаги для вашей версии iOS.",
            "Apple: редактирование фото и видео на iPhone",
            "Apple: отмена правок и возврат фото к оригиналу на iPhone",
        ),
        webmcp=(
            "Предварительная версия императивного API WebMCP в Chrome",
            "Постройте детерминированную качественную последовательность правок только из ограниченных стилевых выборов. Никогда не принимайте и не запрашивайте фото, файлы, метаданные, камеры, библиотеки, аккаунты или свободный текст; никогда не анализируйте изображение и не гарантируйте результат.",
        ),
        app=(
            "Хотите смотреть плёночные луки прямо на устройстве?",
            "PhotoCream Pro — по желанию. Текущая страница App Store описывает 100+ луков, зерно, галацию, световые утечки, свечение, виньетку, живой предпросмотр и управление светом/цветом; обработка на устройстве без аккаунтов и загрузок. Бесплатная загрузка с разовой разблокировкой. Точную доступность и функции смотрите на актуальной странице. Планировщик работает и без приложения.",
            "Открыть PhotoCream Pro в App Store",
        ),
        faq=(
            "Вопросы о планировании плёночного лука",
            (
                (
                    "Берёт ли страница моё фото или смотрит его?",
                    "Нет. Она принимает только ограниченные стилевые выборы и никогда — фото, файлы или метаданные.",
                ),
                (
                    "Воссоздаёт ли рецепт конкретную плёнку?",
                    "Нет. Он даёт стартовую последовательность и не претендует на точность или результат.",
                ),
                (
                    "Можно ли отменить правку в Apple Photos?",
                    "Apple документирует возврат отредактированного фото или видео к оригиналу; проверьте актуальные шаги для вашей версии iOS.",
                ),
            ),
        ),
        footer="Только ограниченные предпочтения · без доступа к фото · без анализа изображений · без обещаний результата",
        inline="Спланируйте приватный рецепт плёночного лука, прежде чем выбирать редактор",
        index=(
            "Приватный планировщик плёночного лука",
            "Выберите плёночное направление и получите обратимую последовательность правок без загрузки и анализа фото.",
        ),
    ),
    "uk": _copy(
        meta=(
            "Приватний планувальник плівкового луку | Без завантаження фото",
            "Перетворіть обмежені стильові вподобання на оборотну послідовність правок без завантаження, сканування, аналізу чи зберігання фото.",
            "Безкоштовні інструменти",
            "English",
            "Безкоштовно · без введення фото · без обіцянок результату",
            "Приватний планувальник плівкового луку",
            "Оберіть візуальний напрям, умови світла й уподобання фінішу. Сторінка повертає стартову послідовність — ніколи не готовий пресет і не гарантований результат.",
        ),
        badges=(
            "Без фото, файлів і метаданих",
            "Без доступу до камери, бібліотеки й акаунтів",
            "Без завантажень, зберігання й аналізу",
            "Без гарантій якості чи результату",
        ),
        planner=(
            "Скласти оборотний стартовий рецепт",
            "Поради якісні й залежать від вихідного знімка, екрана, редактора та фінального розміру. Переглядайте кожну зміну й зберігайте оригінал.",
        ),
        labels=(
            "Візуальний напрям",
            "Світло джерела",
            "Уподобання зерна",
            "Напрям кольору",
            "Фінальне використання",
        ),
        options=(
            (
                "Чиста плівка",
                "Теплі 35мм",
                "Холодне кіно",
                "Одноразовий спалах",
                "Вицвілий вінтаж",
            ),
            ("Яскрава сцена", "Збалансоване світло", "Мало світла"),
            ("Без доданого зерна", "Тонке зерно", "Помітне зерно"),
            ("Нейтрально", "Тепліше", "Холодніше"),
            ("Одне фото", "Узгоджена серія", "Друк"),
        ),
        natural=(
            "Зберігайте природні тони шкіри, якщо в кадрі люди",
            "Якщо є люди, порівнюйте шкіру, очі й волосся до та після кожного колірного кроку.",
            "Уподобання для облич не обрано; усе ж перевірте людей і важливі колірні орієнтири перед експортом.",
        ),
        results=(
            "Створити приватний рецепт",
            "Стартовий напрям",
            "Порядок коригувань",
            "Перевірка узгодженості",
            "Межа рецепта",
        ),
        notes=(
            (
                "Тримайте контраст помірним, колір збалансованим, світла м'якими; додавайте стилізацію лише після стабільної бази.",
                "Віддавайте перевагу теплим середнім тонам, середньому контрасту й м'яким світлам; стежте за помаранчевим і шкірою перед ефектами.",
                "Контролюйте світла, злегка охолодіть тіні й не давайте нейтральним об'єктам синіти.",
                "Збережіть яскравість прямого спалаху й різкий центральний контраст; затемнення країв — лише після перевірки облич і тексту.",
                "М'яко відкрийте найтемніші тони, зменште жорсткий контраст і пом'якшіть колір, не стираючи важливі деталі.",
            ),
            (
                "Спершу захистіть яскраві світла й оцініть, чи зберігають найсвітліші зони корисні деталі.",
                "Налаштуйте експозицію й баланс білого до настрою, зерна й декоративних ефектів.",
                "Не відкривайте тіні агресивно; перевірте шум і колірні плями у фінальному розмірі перегляду.",
            ),
            (
                "Залиште додане зерно вимкненим і будуйте лук світлом, кольором і контрастом.",
                "Додавайте тонке зерно ближче до кінця, потім перевірте рівне небо, шкіру й текст у звичайному розмірі.",
                "Виразне зерно — лише після базової правки; зменште, якщо обличчя, дрібні деталі чи фактура друку відволікають.",
            ),
            (
                "Спершу виправте явний колірний зсув, потім тримайте біле й знайомі об'єкти правдоподібними.",
                "Додавайте теплоту поступово й перед експортом переперевірте біле, шкіру й внутрішнє світло.",
                "Охолоджуйте зображення поступово; не давайте світлам і нейтральним об'єктам неприродно синіти.",
            ),
            (
                "Оцінюйте результат у реальному розмірі перегляду й порівнюйте зі збереженим оригіналом.",
                "Оберіть еталонну правку, порівняйте всю серію й виправте кадри, що вибиваються, замість нашарування ефектів.",
                "Перегляньте запланований кадр і розмір друку; яскравість екрана й додане зерно на папері виглядають інакше.",
            ),
        ),
        boundary=(
            "Це послідовність правок, а не пресет, не аналіз зображення й не обіцянка збігу з плівкою. "
            "Вона не бачить експозицію, обличчя, колір, фокус, шум, динамічний діапазон чи умови виводу."
        ),
        review=(
            "Чотири перевірки перед експортом",
            "Зберігайте недоторканий оригінал або оборотний шлях правок.",
            "Вносьте по одній невеликій зміні й порівнюйте у звичайному розмірі перегляду.",
            "Перед додаванням фактури перевірте світла, тіні, знайомі кольори й людей.",
            "Для серії порівняйте всі кадри разом і виправте ті, що вибиваються, перед експортом.",
        ),
        sources=(
            "Офіційний контекст редагування Apple, а не схвалення",
            "Apple документує редагування фото й відео на iPhone і повернення відредагованого до оригіналу. Перевірте актуальні кроки для вашої версії iOS.",
            "Apple: редагування фото й відео на iPhone",
            "Apple: скасування правок і повернення фото до оригіналу на iPhone",
        ),
        webmcp=(
            "Попередня версія імперативного API WebMCP у Chrome",
            "Побудуйте детерміновану якісну послідовність правок лише з обмежених стильових виборів. Ніколи не приймайте й не запитуйте фото, файли, метадані, камери, бібліотеки, акаунти чи вільний текст; ніколи не аналізуйте зображення й не гарантуйте результат.",
        ),
        app=(
            "Хочете переглядати плівкові луки просто на пристрої?",
            "PhotoCream Pro — за бажанням. Поточна сторінка App Store описує 100+ луків, зерно, галацію, світлові витоки, світіння, віньєтку, живий передперегляд і керування світлом/кольором; обробка на пристрої без акаунтів і завантажень. Безкоштовне завантаження з разовим розблокуванням. Точну доступність і функції дивіться на актуальній сторінці. Планувальник працює й без застосунку.",
            "Відкрити PhotoCream Pro в App Store",
        ),
        faq=(
            "Питання про планування плівкового луку",
            (
                (
                    "Чи бере сторінка моє фото або дивиться його?",
                    "Ні. Вона приймає лише обмежені стильові вибори й ніколи — фото, файли чи метадані.",
                ),
                (
                    "Чи відтворює рецепт конкретну плівку?",
                    "Ні. Він дає стартову послідовність і не претендує на точність чи результат.",
                ),
                (
                    "Чи можна скасувати правку в Apple Photos?",
                    "Apple документує повернення відредагованого фото чи відео до оригіналу; перевірте актуальні кроки для вашої версії iOS.",
                ),
            ),
        ),
        footer="Лише обмежені вподобання · без доступу до фото · без аналізу зображень · без обіцянок результату",
        inline="Сплануйте приватний рецепт плівкового луку, перш ніж обирати редактор",
        index=(
            "Приватний планувальник плівкового луку",
            "Оберіть плівковий напрям і отримайте оборотну послідовність правок без завантаження й аналізу фото.",
        ),
    ),
    "pl": _copy(
        meta=(
            "Prywatny planer filmowego looku | Bez przesyłania zdjęć",
            "Zamień ograniczone preferencje stylu na odwracalną sekwencję edycji bez przesyłania, skanowania, analizowania i przechowywania zdjęć.",
            "Bezpłatne narzędzia",
            "English",
            "Bezpłatnie · bez wejścia zdjęć · bez obietnic wyniku",
            "Prywatny planer filmowego looku",
            "Wybierz kierunek wizualny, warunki światła i preferencję wykończenia. Strona zwraca sekwencję startową — nigdy gotowy preset ani gwarantowany wynik.",
        ),
        badges=(
            "Bez zdjęć, plików i metadanych",
            "Bez dostępu do kamery, biblioteki i kont",
            "Bez przesyłania, przechowywania i analizy",
            "Bez gwarancji jakości czy wyniku",
        ),
        planner=(
            "Ułóż odwracalny przepis startowy",
            "Wskazówki są jakościowe i zależą od zdjęcia źródłowego, ekranu, edytora i finalnego rozmiaru. Podglądaj każdą zmianę i zachowuj oryginał.",
        ),
        labels=(
            "Kierunek wizualny",
            "Światło źródła",
            "Preferencja ziarna",
            "Kierunek koloru",
            "Finalne użycie",
        ),
        options=(
            (
                "Czysty film",
                "Ciepłe 35mm",
                "Zimne kino",
                "Jednorazowa lampa",
                "Wyblakły vintage",
            ),
            ("Jasna scena", "Zrównoważone światło", "Mało światła"),
            ("Bez dodanego ziarna", "Delikatne ziarno", "Widoczne ziarno"),
            ("Neutralnie", "Cieplej", "Chłodniej"),
            ("Jedno zdjęcie", "Spójna seria", "Wydruk"),
        ),
        natural=(
            "Zachowaj naturalne tony skóry, gdy w kadrze są ludzie",
            "Jeśli są ludzie, porównuj skórę, oczy i włosy przed i po każdym kroku koloru.",
            "Nie wybrano preferencji dla twarzy; mimo to sprawdź ludzi i ważne odniesienia kolorów przed eksportem.",
        ),
        results=(
            "Utwórz prywatny przepis",
            "Kierunek startowy",
            "Kolejność korekt",
            "Kontrola spójności",
            "Granica przepisu",
        ),
        notes=(
            (
                "Trzymaj kontrast umiarkowany, kolor zrównoważony, światła miękkie; stylizację dodawaj dopiero po stabilnej bazie.",
                "Preferuj ciepłe tony średnie, średni kontrast i miękkie światła; obserwuj pomarańcze i skórę przed efektami.",
                "Kontroluj światła, lekko ochłodź cienie i nie pozwalaj neutralnym obiektom błękitnieć.",
                "Zachowaj jasność bezpośredniej lampy i ostry centralny kontrast; ściemnienie brzegów dodaj dopiero po sprawdzeniu twarzy i tekstu.",
                "Delikatnie otwórz najciemniejsze tony, zmniejsz twardy kontrast i zmiękcz kolor, nie wymazując ważnych detali.",
            ),
            (
                "Najpierw chroń jasne światła i oceń, czy najjaśniejsze obszary wciąż trzymają użyteczny detal.",
                "Ustaw ekspozycję i balans bieli przed nastrojem, ziarnem i efektami dekoracyjnymi.",
                "Nie otwieraj cieni agresywnie; sprawdź szum i plamy koloru w finalnym rozmiarze oglądania.",
            ),
            (
                "Zostaw dodane ziarno wyłączone i buduj look światłem, kolorem i kontrastem.",
                "Dodaj delikatne ziarno pod koniec, potem obejrzyj gładkie niebo, skórę i tekst w normalnym rozmiarze.",
                "Wyraziste ziarno tylko po edycji bazowej; zmniejsz, jeśli twarze, drobne detale lub faktura druku rozpraszają.",
            ),
            (
                "Najpierw skoryguj wyraźne przesunięcie koloru, potem trzymaj biel i znajome obiekty wiarygodnymi.",
                "Dodawaj ciepło stopniowo i przed eksportem ponownie sprawdź biel, skórę i światło wnętrza.",
                "Ochładzaj obraz stopniowo; nie pozwalaj światłom i neutralnym obiektom nienaturalnie błękitnieć.",
            ),
            (
                "Oceniaj wynik w rzeczywistym rozmiarze oglądania i porównuj z zachowanym oryginałem.",
                "Wybierz edycję wzorcową, porównaj całą serię i popraw odstające kadry zamiast piętrzyć efekty.",
                "Podejrzyj planowany kadr i rozmiar wydruku; jasność ekranu i dodane ziarno na papierze wyglądają inaczej.",
            ),
        ),
        boundary=(
            "To sekwencja edycji, a nie preset, nie analiza obrazu i nie obietnica zgodności z kliszą. "
            "Nie widzi ekspozycji, twarzy, koloru, ostrości, szumu, zakresu dynamiki ani warunków wyjściowych."
        ),
        review=(
            "Cztery kontrole przed eksportem",
            "Zachowaj nietknięty oryginał albo odwracalną ścieżkę edycji.",
            "Wprowadzaj po jednej małej zmianie i porównuj w normalnym rozmiarze oglądania.",
            "Przed dodaniem faktury sprawdź światła, cienie, znajome kolory i ludzi.",
            "Dla serii porównaj wszystkie kadry razem i popraw odstające przed eksportem.",
        ),
        sources=(
            "Oficjalny kontekst edycji Apple, nie rekomendacja",
            "Apple dokumentuje edycję zdjęć i wideo na iPhonie oraz przywracanie edytowanego elementu do oryginału. Sprawdź aktualne kroki dla swojej wersji iOS.",
            "Apple: edytuj zdjęcia i wideo na iPhonie",
            "Apple: cofnij edycje i przywróć zdjęcie do oryginału na iPhonie",
        ),
        webmcp=(
            "Podgląd imperatywnego API WebMCP w Chrome",
            "Zbuduj deterministyczną, jakościową sekwencję edycji wyłącznie z ograniczonych wyborów stylu. Nigdy nie przyjmuj ani nie pozyskuj zdjęć, plików, metadanych, kamer, bibliotek, kont ani wolnego tekstu; nigdy nie analizuj obrazu ani nie gwarantuj wyniku.",
        ),
        app=(
            "Chcesz podglądać filmowe looki bezpośrednio na urządzeniu?",
            "PhotoCream Pro jest opcjonalne. Bieżąca strona App Store opisuje 100+ looków, ziarno, halację, light leaki, bloom, winietę, podgląd na żywo i kontrolę światła/koloru; przetwarzanie na urządzeniu bez kont i przesyłania. Bezpłatne pobranie z jednorazowym odblokowaniem. Dokładną dostępność i funkcje sprawdź na aktualnej stronie. Ten planer działa też bez aplikacji.",
            "Zobacz PhotoCream Pro w App Store",
        ),
        faq=(
            "Pytania o planowanie filmowego looku",
            (
                (
                    "Czy ta strona pobiera lub ogląda moje zdjęcie?",
                    "Nie. Przyjmuje tylko ograniczone wybory stylu i nigdy zdjęć, plików ani metadanych.",
                ),
                (
                    "Czy przepis odtwarza konkretną kliszę?",
                    "Nie. Daje sekwencję startową i nie twierdzi o dokładności ani wyniku.",
                ),
                (
                    "Czy mogę cofnąć edycję w Apple Photos?",
                    "Apple dokumentuje przywracanie edytowanego zdjęcia lub wideo do oryginału; zweryfikuj aktualne kroki dla swojej wersji iOS.",
                ),
            ),
        ),
        footer="Tylko ograniczone preferencje · bez dostępu do zdjęć · bez analizy obrazu · bez obietnic wyniku",
        inline="Zaplanuj prywatny przepis filmowego looku, zanim wybierzesz edytor",
        index=(
            "Prywatny planer filmowego looku",
            "Wybierz filmowy kierunek i otrzymaj odwracalną sekwencję edycji bez przesyłania i analizowania zdjęć.",
        ),
    ),
    "ta-IN": _copy(
        meta=(
            "தனியுரிமை பிலிம் லுக் ரெசிபி திட்டமிடி | புகைப்படப் பதிவேற்றம் இல்லை",
            "புகைப்படத்தைப் பதிவேற்றாமல், ஸ்கேன் செய்யாமல், பகுப்பாய்வு செய்யாமல், சேமிக்காமல் வரம்பிட்ட பாணி விருப்பங்களை மீளக்கூடிய திருத்த வரிசையாக மாற்றுங்கள்.",
            "இலவசக் கருவிகள்",
            "English",
            "இலவசம் · புகைப்பட உள்ளீடு இல்லை · முடிவு வாக்குறுதி இல்லை",
            "தனியுரிமை பிலிம் லுக் ரெசிபி திட்டமிடி",
            "காட்சி திசை, ஒளி நிலை, முடித்தல் விருப்பத்தைத் தேர்வு செய்யுங்கள். பக்கம் ஒரு தொடக்க வரிசையைத் தரும்; ஒருபோதும் இறுதி ப்ரீசெட்டோ உத்தரவாத முடிவோ அல்ல.",
        ),
        badges=(
            "புகைப்படம், கோப்பு அல்லது மெட்டாடேட்டா இல்லை",
            "கேமரா, நூலகம் அல்லது கணக்கு அணுகல் இல்லை",
            "பதிவேற்றம், சேமிப்பு அல்லது பகுப்பாய்வு இல்லை",
            "தரம் அல்லது முடிவு உத்தரவாதம் இல்லை",
        ),
        planner=(
            "மீளக்கூடிய தொடக்க ரெசிபியை உருவாக்குங்கள்",
            "பரிந்துரைகள் தரவியல் சார்ந்தவை; மூலப் படம், திரை, எடிட்டர், இறுதி அளவைப் பொறுத்தவை. ஒவ்வொரு மாற்றத்தையும் முன்னோட்டமிட்டு அசலைப் பாதுகாக்கவும்.",
        ),
        labels=(
            "காட்சி திசை",
            "மூல ஒளி",
            "கிரெயின் விருப்பம்",
            "வண்ண திசை",
            "இறுதி பயன்பாடு",
        ),
        options=(
            (
                "சுத்தமான பிலிம்",
                "வெதுவெதுப்பான 35mm",
                "குளிர்ந்த சினிமா",
                "ஒருமுறை பிளாஷ்",
                "மங்கிய விண்டேஜ்",
            ),
            ("பிரகாசமான காட்சி", "சமநிலை ஒளி", "குறைந்த ஒளி"),
            ("சேர்த்த கிரெயின் இல்லை", "நுண்ணிய கிரெயின்", "தெரியும் கிரெயின்"),
            ("நடுநிலை", "வெதுவெதுப்பாக", "குளிர்ச்சியாக"),
            ("ஒரு புகைப்படம்", "பொருந்தும் தொடர்", "அச்சு"),
        ),
        natural=(
            "மனிதர்கள் இருந்தால் தோல் நிறங்களை இயல்பாக வைத்திருங்கள்",
            "மனிதர்கள் இருந்தால், ஒவ்வொரு வண்ணப் படிக்கும் முன்பும் பின்பும் தோல், கண்கள், முடியை ஒப்பிடுங்கள்.",
            "முகம் சார்ந்த விருப்பம் தேர்வு செய்யப்படவில்லை; இருந்தும் ஏற்றுமதிக்கு முன் மனிதர்களையும் முக்கிய வண்ணக் குறிப்புகளையும் சரிபார்க்கவும்.",
        ),
        results=(
            "தனியுரிமை ரெசிபியை உருவாக்கு",
            "தொடக்க திசை",
            "சரிசெய்தல் வரிசை",
            "சீர்மை சரிபார்ப்பு",
            "ரெசிபி எல்லை",
        ),
        notes=(
            (
                "காண்ட்ராஸ்ட்டை மிதமாகவும் வண்ணத்தை சமநிலையாகவும் ஹைலைட்டுகளை மென்மையாகவும் வைத்திருங்கள்; அடிப்படை நிலைத்த பின்பே பாணி சேர்க்கவும்.",
                "வெதுவெதுப்பான நடு-டோன்கள், நடுத்தர காண்ட்ராஸ்ட், மென்மையான ஹைலைட்டுகளை விரும்புங்கள்; எஃபெக்ட் சேர்க்கும் முன் ஆரஞ்சு மற்றும் தோலைக் கவனியுங்கள்.",
                "ஹைலைட்டுகளைக் கட்டுப்படுத்தி, நிழல்களை சிறிது குளிர்வித்து, நடுநிலை பொருட்கள் நீலமாகாமல் பாருங்கள்.",
                "நேரடி பிளாஷின் பிரகாசத்தையும் கூர்மையான மையக் காண்ட்ராஸ்ட்டையும் வைத்திருங்கள்; முகங்கள்-உரையைச் சரிபார்த்த பின்பே விளிம்பு இருட்டலைச் சேர்க்கவும்.",
                "மிக இருண்ட டோன்களை மென்மையாகத் திறந்து, கடும் காண்ட்ராஸ்ட்டைக் குறைத்து, முக்கிய விவரங்களை அழிக்காமல் வண்ணத்தை மென்மையாக்குங்கள்.",
            ),
            (
                "முதலில் பிரகாசமான ஹைலைட்டுகளைப் பாதுகாத்து, மிக வெளிச்சமான பகுதிகளில் பயனுள்ள விவரம் இருக்கிறதா என மதிப்பிடுங்கள்.",
                "மூட், கிரெயின் அல்லது அலங்கார எஃபெக்ட்களுக்கு முன் எக்ஸ்போஷரையும் ஒயிட் பேலன்ஸையும் சரிசெய்யுங்கள்.",
                "நிழல்களை மிகைப்படுத்தித் திறக்க வேண்டாம்; இறுதி பார்வை அளவில் சத்தத்தையும் வண்ணக் கறைகளையும் சரிபார்க்கவும்.",
            ),
            (
                "சேர்த்த கிரெயினை அணைத்தே வைத்து, ஒளி-வண்ணம்-காண்ட்ராஸ்ட்டால் லுக்கை உருவாக்குங்கள்.",
                "நுண்ணிய கிரெயினை இறுதியில் சேர்த்து, சமமான வானம், தோல், உரையை இயல்பான அளவில் பரிசோதிக்கவும்.",
                "வேண்டுமென்றே கிரெயின் அடிப்படை திருத்தத்திற்குப் பின்பே; முகங்கள், சிறு விவரங்கள் அல்லது அச்சு அமைப்பு கவனத்தைச் சிதறினால் குறைக்கவும்.",
            ),
            (
                "முதலில் தெளிவான வண்ண விலகலைச் சரிசெய்து, பின்னர் வெள்ளையையும் பரிச்சயமான பொருட்களையும் நம்பத்தக்கதாக வைத்திருங்கள்.",
                "வெதுவெதுப்பைப் படிப்படியாகச் சேர்த்து, ஏற்றுமதிக்கு முன் வெள்ளை, தோல், உட்புற ஒளியை மீண்டும் சரிபார்க்கவும்.",
                "படத்தைப் படிப்படியாகக் குளிர்வியுங்கள்; ஹைலைட்டுகளும் நடுநிலை பொருட்களும் இயல்புக்கு மாறாக நீலமாகாமல் பாருங்கள்.",
            ),
            (
                "முடிவை உண்மையான பார்வை அளவில் மதிப்பிட்டு, பாதுகாத்த அசலுடன் ஒப்பிடுங்கள்.",
                "ஒரு குறிப்பு திருத்தத்தைத் தேர்ந்து, முழு தொடரையும் ஒப்பிட்டு, மேலும் எஃபெக்ட் அடுக்குவதற்குப் பதில் விலகும் பிரேம்களைச் சரிசெய்யுங்கள்.",
                "நோக்கிய கிராப்பையும் அச்சு அளவையும் முன்னோட்டமிடுங்கள்; திரை பிரகாசமும் சேர்த்த கிரெயினும் காகிதத்தில் வேறுபடலாம்.",
            ),
        ),
        boundary=(
            "இது ஒரு திருத்த வரிசை; ப்ரீசெட்டோ, படப் பகுப்பாய்வோ, பிலிம் ஸ்டாக் பொருத்த வாக்குறுதியோ அல்ல. "
            "எக்ஸ்போஷர், முகங்கள், வண்ணம், குவியம், சத்தம், டைனமிக் ரேஞ்ச் அல்லது வெளியீட்டு நிலைகளை இது பார்க்க முடியாது."
        ),
        review=(
            "ஏற்றுமதிக்கு முன் நான்கு சரிபார்ப்புகள்",
            "தொடப்படாத அசலை அல்லது மீளக்கூடிய திருத்தப் பாதையைப் பாதுகாக்கவும்.",
            "ஒவ்வொரு முறையும் ஒரு சிறு மாற்றத்தைச் செய்து இயல்பான பார்வை அளவில் ஒப்பிடுங்கள்.",
            "அமைப்பு சேர்க்கும் முன் ஹைலைட்டுகள், நிழல்கள், பரிச்சயமான வண்ணங்கள், மனிதர்களைச் சரிபார்க்கவும்.",
            "தொடருக்கு எல்லா பிரேம்களையும் சேர்த்து ஒப்பிட்டு, ஏற்றுமதிக்கு முன் விலகுபவற்றைச் சரிசெய்யுங்கள்.",
        ),
        sources=(
            "அதிகாரப்பூர்வ Apple திருத்தச் சூழல்; ஒப்புதல் அல்ல",
            "iPhone-இல் புகைப்படம்-வீடியோ திருத்தலையும் திருத்தியதை அசலுக்கு மீட்டலையும் Apple ஆவணப்படுத்துகிறது. உங்கள் iOS பதிப்பிற்கான தற்போதைய படிகளைச் சரிபார்க்கவும்.",
            "Apple: iPhone-இல் புகைப்படம்-வீடியோ திருத்துதல்",
            "Apple: iPhone-இல் புகைப்படத் திருத்தங்களை மீளமைத்து அசலுக்கு மீட்டல்",
        ),
        webmcp=(
            "Chrome-இன் கட்டளை WebMCP API முன்னோட்டம்",
            "வரம்பிட்ட பாணி தேர்வுகளிலிருந்து மட்டும் நிர்ணயமான தரவியல் திருத்த வரிசையை உருவாக்குங்கள். புகைப்படங்கள், கோப்புகள், மெட்டாடேட்டா, கேமரா, நூலகம், கணக்குகள் அல்லது சுதந்திர உரையை ஒருபோதும் எடுக்கவோ அணுகவோ வேண்டாம்; ஒருபோதும் படத்தைப் பகுப்பாய்வு செய்யவோ முடிவை உத்தரவாதம் செய்யவோ வேண்டாம்.",
        ),
        app=(
            "பிலிம் லுக்குகளை உங்கள் சாதனத்திலேயே முன்னோட்டமிட விரும்புகிறீர்களா?",
            "PhotoCream Pro விருப்பத்தேர்வு. தற்போதைய App Store பக்கம் 100+ லுக்குகள், கிரெயின், ஹேலேஷன், லைட் லீக், ப்ளூம், விக்னெட், நேரடி முன்னோட்டம், ஒளி/வண்ணக் கட்டுப்பாடுகளை விவரிக்கிறது; கணக்கோ பதிவேற்றமோ இன்றி சாதனத்திலேயே செயலாக்கம். ஒருமுறை திறப்புடன் இலவசப் பதிவிறக்கம். துல்லியமான கிடைப்பும் அம்சங்களும் தற்போதைய பக்கத்தில் பார்க்கவும். இந்தத் திட்டமிடி ஆப் இல்லாமலும் இயங்கும்.",
            "App Store-இல் PhotoCream Pro-ஐப் பார்க்கவும்",
        ),
        faq=(
            "பிலிம் லுக் திட்டமிடல் கேள்விகள்",
            (
                (
                    "இந்தப் பக்கம் என் புகைப்படத்தை எடுக்குமா அல்லது பார்க்குமா?",
                    "இல்லை. வரம்பிட்ட பாணி தேர்வுகளை மட்டுமே ஏற்கிறது; புகைப்படம், கோப்பு அல்லது மெட்டாடேட்டா ஒருபோதும் இல்லை.",
                ),
                (
                    "இந்த ரெசிபி குறிப்பிட்ட பிலிம் ஸ்டாக்கை மீண்டும் உருவாக்குமா?",
                    "இல்லை. இது ஒரு தொடக்க வரிசையைத் தருகிறது; துல்லியமோ முடிவோ கூறவில்லை.",
                ),
                (
                    "Apple Photos-இல் திருத்தத்தை மீளமைக்க முடியுமா?",
                    "திருத்திய புகைப்படம் அல்லது வீடியோவை அசலுக்கு மீட்டலை Apple ஆவணப்படுத்துகிறது; உங்கள் iOS பதிப்பிற்கான தற்போதைய படிகளைச் சரிபார்க்கவும்.",
                ),
            ),
        ),
        footer="வரம்பிட்ட விருப்பங்கள் மட்டும் · புகைப்பட அணுகல் இல்லை · படப் பகுப்பாய்வு இல்லை · முடிவு வாக்குறுதி இல்லை",
        inline="எடிட்டரைத் தேர்வதற்கு முன் தனியுரிமை பிலிம் லுக் ரெசிபியைத் திட்டமிடுங்கள்",
        index=(
            "தனியுரிமை பிலிம் லுக் ரெசிபி திட்டமிடி",
            "பிலிம் திசையைத் தேர்ந்து, புகைப்படம் பதிவேற்றாமல் பகுப்பாய்வு செய்யாமல் மீளக்கூடிய திருத்த வரிசையைப் பெறுங்கள்.",
        ),
    ),
}


STYLE = r"""
:root{--ink:#332b2b;--muted:#746864;--line:#e9d9d1;--paper:#fffdf9;--bg:#f8efe8;--deep:#713e32;--rose:#b86f5e;--soft:#f9e5dc;--gold:#d6a96c;--shadow:0 22px 60px rgba(91,54,45,.14)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 85% 0,#fffaf2 0,var(--bg) 52%,#efdcd2 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:var(--deep)}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffdf9f2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--deep);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,253,249,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--deep);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,button{font:inherit}select{width:100%;min-height:46px;border:1px solid #dbc6bd;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--deep),var(--rose));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(113,62,50,.22)}
.results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #e5c9bd;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#7b5046;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#4e3934;font-weight:760;margin-top:5px}.note{background:#fff4d9;border:1px solid #ead5a2;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fffdf9,#f5dfd4)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--deep);color:#fff7ef;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.controls,.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""


SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("film-config").textContent);
  const form = document.getElementById("film-planner");
  const fields = {
    mood: document.getElementById("mood"),
    lighting: document.getElementById("lighting"),
    grain: document.getElementById("grain"),
    color: document.getElementById("color"),
    output: document.getElementById("output"),
    keep_skin_natural: document.getElementById("keep-skin-natural")
  };
  const output = {
    direction: document.getElementById("result-direction"),
    sequence: document.getElementById("result-sequence"),
    consistency: document.getElementById("result-consistency"),
    boundary: document.getElementById("result-boundary")
  };

  function enumValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const values = config.inputSchema.properties[name].enum;
    if (typeof value !== "string" || !values.includes(value)) {
      throw new RangeError(`${name} is not a supported value.`);
    }
    return value;
  }

  function booleanValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name) ||
        typeof input[name] !== "boolean") {
      throw new TypeError(`${name} must be a boolean.`);
    }
    return input[name];
  }

  function plan(input) {
    const mood = enumValue(input, "mood");
    const lighting = enumValue(input, "lighting");
    const grain = enumValue(input, "grain");
    const color = enumValue(input, "color");
    const finalOutput = enumValue(input, "output");
    const keepSkinNatural = booleanValue(input, "keep_skin_natural");
    return {
      selected_preferences: {
        mood,
        mood_label: config.labels.mood[mood],
        lighting,
        lighting_label: config.labels.lighting[lighting],
        grain,
        grain_label: config.labels.grain[grain],
        color,
        color_label: config.labels.color[color],
        output: finalOutput,
        output_label: config.labels.output[finalOutput],
        keep_skin_natural: keepSkinNatural
      },
      qualitative_editing_order: [
        config.lightingNotes[lighting],
        config.moodNotes[mood],
        config.colorNotes[color],
        config.grainNotes[grain],
        keepSkinNatural ? config.naturalYes : config.naturalNo
      ],
      consistency_check: config.outputNotes[finalOutput],
      boundary: config.boundary,
      is_not_a_preset_or_image_analysis: true,
      no_accuracy_or_outcome_guarantee: true
    };
  }

  function validateInput(input) {
    if (input === null || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("WebMCP input must be an object.");
    }
    const allowed = new Set(Object.keys(config.inputSchema.properties));
    for (const name of Object.keys(input)) {
      if (!allowed.has(name)) {
        throw new RangeError(`${name} is not a supported input.`);
      }
    }
    return plan(input);
  }

  function render() {
    const result = plan({
      mood: fields.mood.value,
      lighting: fields.lighting.value,
      grain: fields.grain.value,
      color: fields.color.value,
      output: fields.output.value,
      keep_skin_natural: fields.keep_skin_natural.checked
    });
    output.direction.textContent = result.selected_preferences.mood_label;
    output.sequence.textContent = result.qualitative_editing_order.join(" ");
    output.consistency.textContent = result.consistency_check;
    output.boundary.textContent = result.boundary;
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_film_look_recipe",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_film_look_recipe",
          photos_files_metadata_camera_library_not_accessed: true,
          no_upload_storage_or_image_analysis: true,
          no_preset_accuracy_or_outcome_guarantee: true,
          plan,
          review_before_export: config.reviewSteps,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_photocream_pro = config.optionalApp;
        }
        return JSON.stringify(result);
      }
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
  for (const field of Object.values(fields)) {
    field.addEventListener("change", render);
  }
  render();
  registerWebMcp().catch((error) =>
    console.error("WebMCP tool registration failed.", error));
})();
"""


def canonical(locale: str) -> str:
    if locale not in ALT_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        '<script type="application/ld+json">'
        + payload.replace("</", "<\\/")
        + "</script>"
    )


def options(values: dict[str, str]) -> str:
    return "".join(
        f'<option value="{html.escape(key, quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    return {
        "type": "object",
        "properties": {
            "mood": {
                "type": "string",
                "enum": list(MOODS),
                "description": t["mood_label"],
            },
            "lighting": {
                "type": "string",
                "enum": list(LIGHTING),
                "description": t["lighting_label"],
            },
            "grain": {
                "type": "string",
                "enum": list(GRAIN),
                "description": t["grain_label"],
            },
            "color": {
                "type": "string",
                "enum": list(COLOR),
                "description": t["color_label"],
            },
            "output": {
                "type": "string",
                "enum": list(OUTPUTS),
                "description": t["output_label"],
            },
            "keep_skin_natural": {
                "type": "boolean",
                "description": t["natural_label"],
            },
        },
        "required": [
            "mood",
            "lighting",
            "grain",
            "color",
            "output",
            "keep_skin_natural",
        ],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool = False) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    prefix = "" if locale == "en" else f"{locale}/"
    url = canonical(locale)
    other = "zh-Hant" if locale == "en" else "en"
    alternate = canonical(other)
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{item}" href="{canonical(item)}">'
        for item in ALT_LOCALES
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in t["badges"]
    )
    review_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["review_steps"]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    sources = (APPLE_EDIT_PHOTOS, APPLE_REVERT_PHOTOS)
    source_items = "".join(
        f'<li><a href="{source}" rel="noopener">{html.escape(label)}</a></li>'
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_film_recipe_{locale.lower()}")
        if app_public
        else ""
    )
    app_card = ""
    if tracked_app_url:
        app_card = (
            '<section class="app-card wrap"><h2>'
            f'{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></section>'
        )
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "labels": {
            "mood": t["mood_options"],
            "lighting": t["lighting_options"],
            "grain": t["grain_options"],
            "color": t["color_options"],
            "output": t["output_options"],
        },
        "moodNotes": t["mood_notes"],
        "lightingNotes": t["lighting_notes"],
        "grainNotes": t["grain_notes"],
        "colorNotes": t["color_notes"],
        "outputNotes": t["output_notes"],
        "naturalYes": t["natural_yes"],
        "naturalNo": t["natural_no"],
        "boundary": t["boundary"],
        "reviewSteps": t["review_steps"],
        "toolDescription": t["webmcp_description"],
        "freePlanner": {
            "label": t["heading"],
            "url": url,
            "boundary": t["planner_intro"],
        },
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(t["source_labels"], sources, strict=True)
        ],
        "webmcpSource": WEBMCP_SOURCE,
        "optionalApp": (
            {
                "label": t["app_cta"],
                "boundary": t["app_text"],
                "app_store_url": tracked_app_url,
            }
            if tracked_app_url
            else None
        ),
    }
    config_json = json.dumps(
        config, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "featureList": [t["planner"], *t["badges"]],
        "citation": list(sources),
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": locale,
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in t["faq"]
        ],
    }
    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{url}">
{alternates}
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["heading"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<style>{STYLE}</style>
{json_script(schema)}
{json_script(faq_schema)}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="film-planner"><div class="controls">
<div class="field"><label for="mood">{html.escape(t["mood_label"])}</label><select id="mood">{options(t["mood_options"])}</select></div>
<div class="field"><label for="lighting">{html.escape(t["lighting_label"])}</label><select id="lighting">{options(t["lighting_options"])}</select></div>
<div class="field"><label for="grain">{html.escape(t["grain_label"])}</label><select id="grain">{options(t["grain_options"])}</select></div>
<div class="field"><label for="color">{html.escape(t["color_label"])}</label><select id="color">{options(t["color_options"])}</select></div>
<div class="field"><label for="output">{html.escape(t["output_label"])}</label><select id="output">{options(t["output_options"])}</select></div>
<label class="toggle"><input id="keep-skin-natural" type="checkbox" checked>{html.escape(t["natural_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_direction"])}</strong><span id="result-direction"></span></div><div class="result"><strong>{html.escape(t["result_sequence"])}</strong><span id="result-sequence"></span></div><div class="result"><strong>{html.escape(t["result_consistency"])}</strong><span id="result-consistency"></span></div></div>
<p class="note"><strong>{html.escape(t["result_boundary"])}:</strong> <span id="result-boundary"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["review_title"])}</h2><ol>{review_items}</ol></article><article class="card"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="film-config">{config_json}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def index_card(locale: str) -> str:
    t = COPY[locale]
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
        f'{SLUG}.html">{html.escape(t["index_title"])}</a></h2>'
        f'<p>{html.escape(t["index_description"])}</p></article>'
    )


def update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    card = index_card(locale)
    existing = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    anchor = re.compile(
        r'(<article class="card third" data-tool="'
        r'photo-storage-calculator">.*?</article>)',
        re.S,
    )
    if anchor.search(updated):
        updated = anchor.sub(r"\1" + card, updated, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in updated:
            # Lite-generated hub (vi/th/id/tr) uses a different structure and is
            # rebuilt by gen_tools_index_lite; skip rather than fail.
            if '<div class="grid">' in updated:
                return False
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = updated.replace(marker, marker + card, 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


TARGET_ANSWER_SLUGS = (
    "how-to-give-iphone-photos-a-film-look-with-grain-and-light-leaks.html",
    "best-pay-once-film-filter-app-for-iphone-with-no-subscription.html",
)
TARGET_ANSWER_SLUGS_BY_LOCALE = {
    "zh-Hans": (
        "best-film-filter-app.html",
        "app-to-make-photos-look-professional.html",
    ),
}
INBOUND_LINK_CLASS = "film-look-recipe-planner-inline-link"
_PHOTOCREAM_CTA = re.compile(
    r'<a\b(?=[^>]*\shref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id' + re.escape(APP_ID) + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)


def insert_answer_links(pages: Path = PAGES) -> int:
    changed = 0
    for locale in ALT_LOCALES:
        directory = pages / "answers" if locale == "en" else pages / locale / "answers"
        link = (
            f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
            f'data-film-look-recipe-planner-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
        )
        for slug in TARGET_ANSWER_SLUGS_BY_LOCALE.get(
            locale,
            TARGET_ANSWER_SLUGS,
        ):
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _PHOTOCREAM_CTA.search(text)
            if match and write_text_if_changed(
                path,
                text[: match.start()] + link + text[match.start() :],
            ):
                changed += 1
    return changed


def build(pages: Path = PAGES, app_public: bool = False) -> list[str]:
    outputs = []
    for locale in ALT_LOCALES:
        root = pages if locale == "en" else pages / locale
        write_text_if_changed(
            root / "tools" / f"{SLUG}.html",
            render_page(locale, app_public),
        )
        update_one_index(root / "tools" / "index.html", locale)
        outputs.append(canonical(locale))
    insert_answer_links(pages)
    return outputs


def main() -> None:
    app_public = APP_KEY in live_app_keys(APPSTORE, PAGES, refresh=False)
    outputs = build(app_public=app_public)
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"film look recipe planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()

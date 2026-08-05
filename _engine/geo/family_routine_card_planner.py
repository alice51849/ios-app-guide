#!/usr/bin/env python3
"""Generate a nine-locale, parent-reviewed family routine-card planner."""

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

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "private-family-routine-card-planner"
APP_KEY = "lumimission"
APP_ID = "6779750237"
CONTENT_DATE = "2026-07-16"
CDC_ROUTINES = (
    "https://www.cdc.gov/parenting-toddlers/structure-rules/index.html"
)
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

CONTEXTS = ("morning", "after-school", "tidy-up", "bedtime")
CARD_COUNTS = (3, 4, 5, 6)
PRESENTATIONS = ("words", "icons-with-labels", "both")
TRANSITION_CUES = ("next-only", "now-next", "safe-choice")
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
)
CARD_ICONS = {
    "morning": ("☀️", "👕", "🫧", "🥣", "🎒", "🚪"),
    "after-school": ("🏠", "🎒", "🫧", "🥛", "🧩", "📌"),
    "tidy-up": ("🧺", "🧸", "📚", "👕", "🧹", "✅"),
    "bedtime": ("🌙", "🫧", "👕", "🪥", "📖", "💤"),
}


def _copy(
    *,
    meta: tuple[str, ...],
    badges: tuple[str, ...],
    planner: tuple[str, str],
    labels: tuple[str, ...],
    options: tuple[tuple[str, ...], ...],
    adult_review: tuple[str, str, str],
    results: tuple[str, ...],
    steps: tuple[tuple[str, ...], ...],
    cue_notes: tuple[str, ...],
    boundary: str,
    preflight: tuple[str, ...],
    sources: tuple[str, str, str],
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
        context_label,
        count_label,
        presentation_label,
        transition_label,
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
        "context_label": context_label,
        "count_label": count_label,
        "presentation_label": presentation_label,
        "transition_label": transition_label,
        "context_options": dict(zip(CONTEXTS, options[0], strict=True)),
        "presentation_options": dict(
            zip(PRESENTATIONS, options[1], strict=True)
        ),
        "transition_options": dict(
            zip(TRANSITION_CUES, options[2], strict=True)
        ),
        "adult_review_label": adult_review[0],
        "adult_review_yes": adult_review[1],
        "adult_review_no": adult_review[2],
        "update": results[0],
        "print": results[1],
        "card_label": results[2],
        "skip_label": results[3],
        "pause_card": results[4],
        "context_steps": dict(zip(CONTEXTS, steps, strict=True)),
        "cue_notes": dict(zip(TRANSITION_CUES, cue_notes, strict=True)),
        "boundary": boundary,
        "preflight_title": preflight[0],
        "preflight_steps": preflight[1:],
        "sources_title": sources[0],
        "sources_intro": sources[1],
        "source_label": sources[2],
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
            "Private Family Routine Card Planner | No Child Data",
            "Make a parent-reviewed sequence of three to six routine cards without entering a child's name, age, schedule, school, behavior or completion record.",
            "Free tools",
            "繁體中文",
            "Free · parent-facing · no child profile",
            "Private family routine card planner",
            "Choose a household context and card format. The page returns a removable, skippable sequence only after an adult confirms every step is suitable.",
        ),
        badges=(
            "No name, age or child profile",
            "No behavior or completion tracking",
            "No account, upload or storage",
            "No outcome or independence promise",
        ),
        planner=(
            "Build an adult-reviewed card sequence",
            "These cards organize household steps; they do not assess a child, prescribe care or predict behavior, sleep, health, learning or family outcomes.",
        ),
        labels=(
            "Routine context",
            "Number of cards",
            "Card presentation",
            "Gentle transition cue",
        ),
        options=(
            (
                "Morning",
                "After school or care",
                "Tidy-up",
                "Bedtime",
            ),
            (
                "Words",
                "Large icons with labels",
                "Icons and words",
            ),
            (
                "Show the next card only",
                "Show now and next",
                "Offer one safe bounded choice",
            ),
        ),
        adult_review=(
            "I am the supervising adult and have checked the selected steps for this household",
            "Adult review confirmed. Keep every card optional and change or remove anything that is unsuitable today.",
            "Adult review is required before cards appear. Check safety, access, care guidance, household needs and the child's current cues.",
        ),
        results=(
            "Create private cards",
            "Print reviewed cards",
            "Optional routine card",
            "May be skipped, paused or replaced",
            "Pause card: stop the sequence and check what the household needs now.",
        ),
        steps=(
            (
                "Use the household's usual calm start cue.",
                "Choose clothing that the supervising adult has approved.",
                "Complete the household's usual wash or care step with appropriate adult help.",
                "Use the family's planned breakfast or drink step.",
                "Let the adult check the items needed for the day.",
                "Move to the family's agreed ready point with the supervising adult.",
            ),
            (
                "Arrive at the household's agreed transition spot.",
                "Place belongings where the supervising adult has chosen.",
                "Use the household's usual wash or care step with appropriate help.",
                "Take the family's planned food, drink or rest pause.",
                "Choose the adult-approved quiet, movement or connection step.",
                "Let the adult preview what comes next today.",
            ),
            (
                "Let the adult choose one small, safe area to begin.",
                "Return a few toys or activity items to their usual place.",
                "Return books or learning materials to the adult-approved place.",
                "Place clothing or soft items where the household expects them.",
                "Let the adult handle sharp, heavy, broken or uncertain items.",
                "Pause together and check that paths and needed items remain accessible.",
            ),
            (
                "Use the household's usual calm bedtime-start cue.",
                "Complete the usual wash or bathroom step with appropriate adult help.",
                "Choose sleep clothing approved for the household and conditions.",
                "Complete tooth care according to current family and professional guidance.",
                "Choose the family's usual quiet connection, story or settling step.",
                "End with the household's agreed sleep setting and supervising adult nearby as needed.",
            ),
        ),
        cue_notes=(
            "Keep only one next card visible; reveal another only after the adult checks the current situation.",
            "Show the current and following card without treating either as a deadline.",
            "Offer a choice only when both options are safe, available and acceptable to the supervising adult.",
        ),
        boundary=(
            "The planner never knows the child's age, development, disability, health, sensory needs, care plan, culture, household, current state or environment. "
            "The supervising adult must adapt, remove or stop every card as needed."
        ),
        preflight=(
            "Four checks before using a card",
            "Confirm the step is safe and suitable in the current place and moment.",
            "Preserve access to food, water, bathroom, medicine, communication, mobility and comfort.",
            "Use current professional care guidance where it applies; a card never overrides it.",
            "Pause, skip or change the sequence whenever the child or household needs something different.",
        ),
        sources=(
            "Official routine context, not an endorsement",
            "CDC describes consistency and predictability as parts of household structure and says families decide which routines work best for them. That guidance does not validate this tool or guarantee an outcome.",
            "CDC: creating consistent routines and household structure",
        ),
        webmcp=(
            "Chrome imperative WebMCP API preview",
            "Create three to six optional parent-reviewed family routine cards from bounded visible choices only. Never accept or access child names, ages, schedules, schools, locations, photos, accounts, free text, behavior or completion records; never score, diagnose, monitor or promise an outcome.",
        ),
        app=(
            "Want an optional reusable parent-and-child routine layer?",
            "Lumi Mission Planet is optional. Its current App Store listing describes parent-and-child routine missions, a parent dashboard, on-device data, no account or third-party analytics, and a free download with one-time unlock. Check the current listing for exact availability and features. These printable cards work without the app.",
            "Parents: view Lumi Mission Planet on the App Store",
        ),
        faq=(
            "Family routine card questions",
            (
                (
                    "Does this page collect information about a child?",
                    "No. It accepts only bounded household choices and never asks for a name, age, schedule, school, profile or activity record.",
                ),
                (
                    "Are the cards a behavior program or care plan?",
                    "No. They are removable household sequence prompts and do not diagnose, prescribe, monitor or promise results.",
                ),
                (
                    "What if a step is not right today?",
                    "The supervising adult should skip, replace or stop it. Every card is optional.",
                ),
            ),
        ),
        footer="Parent-reviewed sequence only · no child data · no tracking · no result promise",
        inline="Plan private, parent-reviewed family routine cards before choosing an app",
        index=(
            "Private Family Routine Card Planner",
            "Make a skippable household sequence without entering child data or tracking completion.",
        ),
    ),
    "es-ES": _copy(
        meta=(
            "Planificador privado de tarjetas de rutina familiar | Sin datos infantiles",
            "Crea una secuencia de tres a seis tarjetas revisada por un adulto sin introducir nombre, edad, horario, escuela, conducta ni registro de actividad del menor.",
            "Herramientas gratuitas",
            "English",
            "Gratis · para adultos · sin perfil infantil",
            "Planificador privado de tarjetas de rutina familiar",
            "Elige un momento del hogar y el formato. La secuencia se muestra solo cuando un adulto confirma que cada paso es adecuado.",
        ),
        badges=(
            "Sin nombre, edad ni perfil infantil",
            "Sin seguimiento de conducta o actividad",
            "Sin cuenta, envío ni almacenamiento",
            "Sin prometer resultados o autonomía",
        ),
        planner=(
            "Crea una secuencia revisada por un adulto",
            "Las tarjetas ordenan pasos del hogar; no evalúan al menor, prescriben cuidados ni predicen conducta, sueño, salud, aprendizaje o resultados familiares.",
        ),
        labels=(
            "Momento de la rutina",
            "Número de tarjetas",
            "Presentación",
            "Señal de transición suave",
        ),
        options=(
            ("Mañana", "Después del cole o cuidado", "Recoger", "Hora de dormir"),
            ("Palabras", "Iconos grandes con texto", "Iconos y palabras"),
            (
                "Mostrar solo la siguiente tarjeta",
                "Mostrar ahora y después",
                "Ofrecer una opción limitada y segura",
            ),
        ),
        adult_review=(
            "Soy el adulto responsable y he comprobado que estos pasos sirven en este hogar",
            "Revisión adulta confirmada. Cada tarjeta sigue siendo opcional; cambia o quita lo que hoy no convenga.",
            "Hace falta revisión adulta. Comprueba seguridad, acceso, indicaciones de cuidado, necesidades del hogar y señales actuales del menor.",
        ),
        results=(
            "Crear tarjetas privadas",
            "Imprimir tarjetas revisadas",
            "Tarjeta opcional",
            "Se puede saltar, pausar o sustituir",
            "Tarjeta de pausa: detén la secuencia y comprueba qué necesita ahora el hogar.",
        ),
        steps=(
            (
                "Usa la señal tranquila con la que suele empezar el día en casa.",
                "Elige ropa aprobada por el adulto responsable.",
                "Realiza el paso habitual de aseo o cuidado con la ayuda adulta necesaria.",
                "Sigue el paso de desayuno o bebida previsto por la familia.",
                "Deja que el adulto revise lo necesario para el día.",
                "Ve con el adulto al punto acordado para estar listos.",
            ),
            (
                "Llega al lugar de transición acordado en casa.",
                "Deja las pertenencias donde haya decidido el adulto.",
                "Realiza el paso habitual de aseo o cuidado con la ayuda necesaria.",
                "Haz la pausa de comida, bebida o descanso prevista por la familia.",
                "Elige el paso tranquilo, de movimiento o conexión aprobado por el adulto.",
                "Deja que el adulto explique qué viene después hoy.",
            ),
            (
                "Deja que el adulto elija una zona pequeña y segura para empezar.",
                "Devuelve algunos juguetes o materiales a su lugar habitual.",
                "Devuelve libros o materiales de aprendizaje al lugar aprobado.",
                "Pon ropa u objetos blandos donde corresponde en casa.",
                "Deja al adulto los objetos afilados, pesados, rotos o dudosos.",
                "Pausa y comprueba con el adulto que los pasos y objetos necesarios siguen accesibles.",
            ),
            (
                "Usa la señal tranquila con la que suele empezar la rutina de noche.",
                "Realiza el aseo o baño habitual con la ayuda adulta necesaria.",
                "Elige ropa de dormir adecuada al hogar y las condiciones.",
                "Realiza el cuidado dental según las indicaciones familiares y profesionales vigentes.",
                "Elige el momento habitual de calma, cuento o conexión familiar.",
                "Termina con el entorno de sueño acordado y el adulto cerca cuando haga falta.",
            ),
        ),
        cue_notes=(
            "Deja visible solo la siguiente tarjeta y muestra otra cuando el adulto revise la situación.",
            "Muestra la tarjeta actual y la siguiente sin convertir ninguna en un plazo.",
            "Ofrece una elección solo si ambas opciones son seguras, posibles y aceptadas por el adulto.",
        ),
        boundary=(
            "El planificador desconoce edad, desarrollo, discapacidad, salud, necesidades sensoriales, plan de cuidados, cultura, hogar, estado actual y entorno. "
            "El adulto responsable debe adaptar, retirar o detener cualquier tarjeta."
        ),
        preflight=(
            "Cuatro controles antes de usar una tarjeta",
            "Confirma que el paso es seguro y adecuado en este lugar y momento.",
            "Mantén el acceso a comida, agua, baño, medicación, comunicación, movilidad y comodidad.",
            "Sigue las indicaciones profesionales vigentes cuando correspondan; una tarjeta nunca las sustituye.",
            "Pausa, salta o cambia la secuencia cuando el menor o el hogar necesiten otra cosa.",
        ),
        sources=(
            "Contexto oficial sobre rutinas, no una recomendación",
            "Los CDC describen la coherencia y previsibilidad como partes de la estructura familiar y señalan que cada familia decide qué rutinas le funcionan. No validan esta herramienta ni garantizan resultados.",
            "CDC: crear rutinas coherentes y estructura familiar",
        ),
        webmcp=(
            "Vista previa de la API imperativa WebMCP de Chrome",
            "Crea de tres a seis tarjetas familiares opcionales y revisadas por un adulto usando solo opciones limitadas. Nunca acepta ni accede a nombres, edades, horarios, escuelas, lugares, fotos, cuentas, texto libre, conducta o registros; nunca puntúa, diagnostica, vigila ni promete resultados.",
        ),
        app=(
            "¿Quieres una capa reutilizable para adulto y menor?",
            "Lumi Mission Planet es opcional. Su ficha actual describe misiones de rutina para usar en familia, panel para adultos, datos en el dispositivo, sin cuenta ni análisis de terceros, y descarga gratuita con desbloqueo único. Consulta la ficha vigente para disponibilidad y funciones exactas. Estas tarjetas funcionan sin la app.",
            "Adultos: ver Lumi Mission Planet en el App Store",
        ),
        faq=(
            "Preguntas sobre tarjetas de rutina",
            (
                (
                    "¿La página recopila datos de un menor?",
                    "No. Solo acepta opciones limitadas del hogar y nunca pide nombre, edad, horario, escuela, perfil o actividad.",
                ),
                (
                    "¿Es un programa de conducta o plan de cuidados?",
                    "No. Son indicaciones domésticas extraíbles; no diagnostican, prescriben, vigilan ni prometen resultados.",
                ),
                (
                    "¿Qué hago si un paso no conviene hoy?",
                    "El adulto responsable debe saltarlo, cambiarlo o detenerlo. Todas las tarjetas son opcionales.",
                ),
            ),
        ),
        footer="Solo secuencia revisada por un adulto · sin datos infantiles · sin seguimiento · sin prometer resultados",
        inline="Planifica tarjetas familiares privadas y revisadas por un adulto antes de elegir una app",
        index=(
            "Planificador privado de tarjetas de rutina familiar",
            "Crea una secuencia opcional sin introducir datos infantiles ni registrar la actividad.",
        ),
    ),
    "pt-BR": _copy(
        meta=(
            "Planejador privado de cartões de rotina familiar | Sem dados infantis",
            "Monte uma sequência de três a seis cartões revisada por um adulto sem informar nome, idade, horário, escola, comportamento ou conclusão da criança.",
            "Ferramentas gratuitas",
            "English",
            "Grátis · para responsáveis · sem perfil infantil",
            "Planejador privado de cartões de rotina familiar",
            "Escolha um momento da casa e o formato. A sequência só aparece depois que um adulto confirma que cada etapa é adequada.",
        ),
        badges=(
            "Sem nome, idade ou perfil infantil",
            "Sem monitorar comportamento ou conclusão",
            "Sem conta, envio ou armazenamento",
            "Sem promessa de resultado ou autonomia",
        ),
        planner=(
            "Monte uma sequência revisada por um adulto",
            "Os cartões apenas organizam etapas da casa; não avaliam a criança, prescrevem cuidados ou preveem comportamento, sono, saúde, aprendizagem ou resultados familiares.",
        ),
        labels=(
            "Momento da rotina",
            "Quantidade de cartões",
            "Apresentação",
            "Sinal de transição gentil",
        ),
        options=(
            ("Manhã", "Depois da escola ou cuidado", "Arrumação", "Hora de dormir"),
            ("Palavras", "Ícones grandes com texto", "Ícones e palavras"),
            (
                "Mostrar só o próximo cartão",
                "Mostrar agora e depois",
                "Oferecer uma escolha limitada e segura",
            ),
        ),
        adult_review=(
            "Sou o adulto responsável e conferi se estas etapas servem para esta casa",
            "Revisão adulta confirmada. Todo cartão continua opcional; troque ou remova o que não servir hoje.",
            "A revisão adulta é necessária. Confira segurança, acesso, orientações de cuidado, necessidades da casa e sinais atuais da criança.",
        ),
        results=(
            "Criar cartões privados",
            "Imprimir cartões revisados",
            "Cartão opcional",
            "Pode pular, pausar ou substituir",
            "Cartão de pausa: pare a sequência e confira o que a casa precisa agora.",
        ),
        steps=(
            (
                "Use o sinal tranquilo que costuma iniciar o dia em casa.",
                "Escolha uma roupa aprovada pelo adulto responsável.",
                "Faça a etapa habitual de higiene ou cuidado com a ajuda adulta adequada.",
                "Siga a etapa de café da manhã ou bebida planejada pela família.",
                "Deixe o adulto conferir os itens necessários para o dia.",
                "Vá com o adulto até o ponto combinado de saída ou prontidão.",
            ),
            (
                "Chegue ao local de transição combinado em casa.",
                "Coloque os pertences onde o adulto escolheu.",
                "Faça a etapa habitual de higiene ou cuidado com a ajuda necessária.",
                "Faça a pausa de comida, bebida ou descanso planejada pela família.",
                "Escolha a etapa tranquila, de movimento ou conexão aprovada pelo adulto.",
                "Deixe o adulto mostrar o que vem depois hoje.",
            ),
            (
                "Deixe o adulto escolher uma área pequena e segura para começar.",
                "Guarde alguns brinquedos ou materiais no lugar habitual.",
                "Guarde livros ou materiais de aprendizagem no local aprovado.",
                "Coloque roupas ou itens macios onde a casa espera.",
                "Deixe objetos cortantes, pesados, quebrados ou incertos para o adulto.",
                "Pause e confira com o adulto se passagens e itens necessários continuam acessíveis.",
            ),
            (
                "Use o sinal tranquilo que costuma iniciar a rotina de dormir.",
                "Faça a etapa habitual de higiene ou banheiro com a ajuda adulta adequada.",
                "Escolha roupa de dormir aprovada para a casa e as condições.",
                "Faça o cuidado dental conforme as orientações atuais da família e profissionais.",
                "Escolha o momento habitual de calma, história ou conexão familiar.",
                "Termine no ambiente de sono combinado, com o adulto por perto quando necessário.",
            ),
        ),
        cue_notes=(
            "Deixe visível apenas o próximo cartão e revele outro depois que o adulto conferir a situação.",
            "Mostre o cartão atual e o seguinte sem transformar nenhum deles em prazo.",
            "Ofereça escolha somente quando as duas opções forem seguras, disponíveis e aceitas pelo adulto.",
        ),
        boundary=(
            "O planejador não conhece idade, desenvolvimento, deficiência, saúde, necessidades sensoriais, plano de cuidado, cultura, casa, estado atual ou ambiente. "
            "O adulto responsável deve adaptar, remover ou parar qualquer cartão."
        ),
        preflight=(
            "Quatro verificações antes de usar um cartão",
            "Confirme se a etapa é segura e adequada neste local e momento.",
            "Preserve acesso a comida, água, banheiro, remédios, comunicação, mobilidade e conforto.",
            "Siga orientações profissionais atuais quando aplicáveis; um cartão nunca as substitui.",
            "Pause, pule ou mude a sequência quando a criança ou a casa precisar de algo diferente.",
        ),
        sources=(
            "Contexto oficial sobre rotinas, não recomendação",
            "O CDC descreve consistência e previsibilidade como partes da estrutura familiar e diz que cada família decide quais rotinas funcionam. Isso não valida a ferramenta nem garante resultados.",
            "CDC: criar rotinas consistentes e estrutura familiar",
        ),
        webmcp=(
            "Prévia da API imperativa WebMCP do Chrome",
            "Cria de três a seis cartões familiares opcionais e revisados por adulto usando apenas escolhas limitadas. Nunca aceita nem acessa nomes, idades, horários, escolas, locais, fotos, contas, texto livre, comportamento ou registros; nunca pontua, diagnostica, monitora ou promete resultados.",
        ),
        app=(
            "Quer uma camada reutilizável para adulto e criança?",
            "Lumi Mission Planet é opcional. A página atual na App Store descreve missões de rotina em família, painel para responsáveis, dados no aparelho, sem conta ou análise de terceiros, e download grátis com desbloqueio único. Confira a página vigente para disponibilidade e recursos exatos. Estes cartões funcionam sem o app.",
            "Responsáveis: ver Lumi Mission Planet na App Store",
        ),
        faq=(
            "Dúvidas sobre cartões de rotina",
            (
                (
                    "A página coleta dados de uma criança?",
                    "Não. Só recebe escolhas limitadas da casa e nunca pede nome, idade, horário, escola, perfil ou atividade.",
                ),
                (
                    "Isto é um programa de comportamento ou plano de cuidado?",
                    "Não. São lembretes domésticos removíveis; não diagnosticam, prescrevem, monitoram nem prometem resultados.",
                ),
                (
                    "E se uma etapa não servir hoje?",
                    "O adulto responsável deve pular, trocar ou parar. Todos os cartões são opcionais.",
                ),
            ),
        ),
        footer="Só sequência revisada por adulto · sem dados infantis · sem monitoramento · sem promessa de resultado",
        inline="Planeje cartões familiares privados e revisados por adulto antes de escolher um app",
        index=(
            "Planejador privado de cartões de rotina familiar",
            "Monte uma sequência opcional sem informar dados infantis ou registrar conclusão.",
        ),
    ),
    "de-DE": _copy(
        meta=(
            "Privater Familienroutine-Kartenplaner | Ohne Kinderdaten",
            "Eine von Erwachsenen geprüfte Folge aus drei bis sechs Karten erstellen, ohne Name, Alter, Zeitplan, Schule, Verhalten oder Erledigungen eines Kindes einzugeben.",
            "Kostenlose Werkzeuge",
            "English",
            "Kostenlos · für Erwachsene · kein Kinderprofil",
            "Privater Planer für Familienroutine-Karten",
            "Haushaltszeitpunkt und Kartenformat wählen. Die Folge erscheint erst, wenn eine erwachsene Aufsicht jede Etappe als passend bestätigt.",
        ),
        badges=(
            "Kein Name, Alter oder Kinderprofil",
            "Keine Verhaltens- oder Erledigungsprotokolle",
            "Kein Konto, Upload oder Speichern",
            "Kein Ergebnis- oder Selbstständigkeitsversprechen",
        ),
        planner=(
            "Von Erwachsenen geprüfte Kartenfolge erstellen",
            "Die Karten ordnen Haushaltsschritte; sie beurteilen kein Kind, verordnen keine Betreuung und sagen Verhalten, Schlaf, Gesundheit, Lernen oder Familienergebnisse nicht voraus.",
        ),
        labels=(
            "Routinezeitpunkt",
            "Kartenanzahl",
            "Kartendarstellung",
            "Sanfter Übergangshinweis",
        ),
        options=(
            ("Morgen", "Nach Schule oder Betreuung", "Aufräumen", "Schlafengehen"),
            ("Wörter", "Große Symbole mit Text", "Symbole und Wörter"),
            (
                "Nur die nächste Karte zeigen",
                "Jetzt und danach zeigen",
                "Eine sichere begrenzte Wahl anbieten",
            ),
        ),
        adult_review=(
            "Ich beaufsichtige als erwachsene Person und habe diese Schritte für unseren Haushalt geprüft",
            "Prüfung bestätigt. Jede Karte bleibt optional; heute Unpassendes ändern oder entfernen.",
            "Erwachsenenprüfung erforderlich. Sicherheit, Zugang, Betreuungshinweise, Haushaltsbedarf und aktuelle Signale des Kindes prüfen.",
        ),
        results=(
            "Private Karten erstellen",
            "Geprüfte Karten drucken",
            "Optionale Routinekarte",
            "Darf übersprungen, pausiert oder ersetzt werden",
            "Pausenkarte: Folge stoppen und prüfen, was der Haushalt jetzt braucht.",
        ),
        steps=(
            (
                "Das im Haushalt übliche ruhige Startsignal verwenden.",
                "Von der Aufsicht bestätigte Kleidung wählen.",
                "Den üblichen Wasch- oder Betreuungsschritt mit passender Hilfe ausführen.",
                "Den geplanten Frühstücks- oder Getränkeschritt der Familie nutzen.",
                "Die erwachsene Person prüft die für den Tag nötigen Dinge.",
                "Gemeinsam zum vereinbarten Bereitschaftsort gehen.",
            ),
            (
                "Am vereinbarten Übergangsort im Haushalt ankommen.",
                "Sachen am von der Aufsicht gewählten Ort ablegen.",
                "Den üblichen Wasch- oder Betreuungsschritt mit passender Hilfe ausführen.",
                "Die geplante Essens-, Getränke- oder Ruhepause der Familie nutzen.",
                "Einen bestätigten Ruhe-, Bewegungs- oder Verbindungsschritt wählen.",
                "Die erwachsene Person kündigt an, was heute als Nächstes kommt.",
            ),
            (
                "Die erwachsene Person wählt einen kleinen sicheren Startbereich.",
                "Einige Spiel- oder Beschäftigungssachen an ihren üblichen Ort zurücklegen.",
                "Bücher oder Lernmaterial an den bestätigten Ort zurücklegen.",
                "Kleidung oder weiche Sachen an den Haushaltsplatz legen.",
                "Scharfe, schwere, kaputte oder unklare Dinge der erwachsenen Person überlassen.",
                "Gemeinsam pausieren und freie Wege sowie wichtige Dinge prüfen.",
            ),
            (
                "Das übliche ruhige Signal zum Beginn der Abendroutine verwenden.",
                "Den üblichen Wasch- oder Toilettenschritt mit passender Hilfe ausführen.",
                "Für Haushalt und Bedingungen bestätigte Schlafkleidung wählen.",
                "Zahnpflege nach aktuellen familiären und fachlichen Hinweisen durchführen.",
                "Den üblichen ruhigen Verbindungs-, Geschichten- oder Entspannungsschritt wählen.",
                "Mit der vereinbarten Schlafumgebung enden; Aufsicht bleibt bei Bedarf in der Nähe.",
            ),
        ),
        cue_notes=(
            "Nur die nächste Karte sichtbar lassen; eine weitere erst nach Prüfung der Situation zeigen.",
            "Aktuelle und folgende Karte zeigen, ohne daraus eine Frist zu machen.",
            "Nur wählen lassen, wenn beide Möglichkeiten sicher, verfügbar und von der Aufsicht akzeptiert sind.",
        ),
        boundary=(
            "Der Planer kennt Alter, Entwicklung, Behinderung, Gesundheit, sensorische Bedürfnisse, Betreuungsplan, Kultur, Haushalt, aktuellen Zustand und Umgebung nicht. "
            "Die erwachsene Aufsicht muss jede Karte anpassen, entfernen oder stoppen."
        ),
        preflight=(
            "Vier Prüfungen vor einer Karte",
            "Bestätigen, dass der Schritt hier und jetzt sicher und passend ist.",
            "Zugang zu Essen, Wasser, Toilette, Medizin, Kommunikation, Mobilität und Komfort erhalten.",
            "Wo relevant aktuelle fachliche Betreuungshinweise befolgen; eine Karte ersetzt sie nie.",
            "Folge pausieren, überspringen oder ändern, wenn Kind oder Haushalt etwas anderes brauchen.",
        ),
        sources=(
            "Amtlicher Routinenkontext, keine Empfehlung",
            "Die CDC beschreibt Beständigkeit und Vorhersehbarkeit als Teile der Haushaltsstruktur und sagt, Familien entscheiden selbst, welche Routinen passen. Das bestätigt weder dieses Werkzeug noch ein Ergebnis.",
            "CDC: beständige Routinen und Haushaltsstruktur schaffen",
        ),
        webmcp=(
            "Vorschau der imperativen Chrome-WebMCP-API",
            "Erstellt nur aus begrenzten Auswahlwerten drei bis sechs optionale, von Erwachsenen geprüfte Routinekarten. Nimmt niemals Namen, Alter, Pläne, Schulen, Orte, Fotos, Konten, Freitext, Verhalten oder Protokolle an und greift nicht darauf zu; bewertet, diagnostiziert, überwacht und verspricht nichts.",
        ),
        app=(
            "Eine optionale wiederverwendbare Ebene für Erwachsene und Kinder?",
            "Lumi Mission Planet ist optional. Der aktuelle App-Store-Eintrag beschreibt gemeinsame Routinen, ein Eltern-Dashboard, Daten auf dem Gerät, kein Konto oder Drittanbieter-Analyse sowie kostenlosen Download mit einmaliger Freischaltung. Verfügbarkeit und genaue Funktionen im aktuellen Eintrag prüfen. Diese Karten funktionieren ohne App.",
            "Für Erwachsene: Lumi Mission Planet im App Store",
        ),
        faq=(
            "Fragen zu Routinekarten",
            (
                (
                    "Sammelt die Seite Daten über ein Kind?",
                    "Nein. Sie nimmt nur begrenzte Haushaltsauswahlen an und fragt nie nach Name, Alter, Plan, Schule, Profil oder Aktivität.",
                ),
                (
                    "Ist dies ein Verhaltensprogramm oder Betreuungsplan?",
                    "Nein. Es sind entfernbare Haushaltsimpulse; sie diagnostizieren, verordnen, überwachen und versprechen nichts.",
                ),
                (
                    "Was, wenn ein Schritt heute nicht passt?",
                    "Die erwachsene Aufsicht überspringt, ersetzt oder stoppt ihn. Jede Karte ist optional.",
                ),
            ),
        ),
        footer="Nur erwachsenengeprüfte Folge · keine Kinderdaten · kein Tracking · kein Ergebnisversprechen",
        inline="Vor der App-Wahl private, erwachsenengeprüfte Familienroutine-Karten planen",
        index=(
            "Privater Familienroutine-Kartenplaner",
            "Optionale Haushaltsfolge ohne Kinderdaten oder Erledigungsprotokoll erstellen.",
        ),
    ),
    "fr-FR": _copy(
        meta=(
            "Planificateur privé de cartes de routine familiale | Sans données d’enfant",
            "Créez une séquence de trois à six cartes validée par un adulte sans saisir nom, âge, emploi du temps, école, comportement ou activité de l’enfant.",
            "Outils gratuits",
            "English",
            "Gratuit · destiné aux adultes · aucun profil enfant",
            "Planificateur privé de cartes de routine familiale",
            "Choisissez un moment du foyer et un format. La séquence apparaît seulement après confirmation par l’adulte responsable.",
        ),
        badges=(
            "Aucun nom, âge ou profil enfant",
            "Aucun suivi du comportement ou des étapes",
            "Aucun compte, envoi ou stockage",
            "Aucune promesse de résultat ou d’autonomie",
        ),
        planner=(
            "Composer une séquence vérifiée par un adulte",
            "Les cartes ordonnent des étapes domestiques ; elles n’évaluent pas l’enfant, ne prescrivent pas de soins et ne prédisent ni comportement, sommeil, santé, apprentissage ou résultat familial.",
        ),
        labels=(
            "Moment de la routine",
            "Nombre de cartes",
            "Présentation",
            "Repère de transition doux",
        ),
        options=(
            ("Matin", "Après l’école ou la garde", "Rangement", "Coucher"),
            ("Mots", "Grandes icônes avec texte", "Icônes et mots"),
            (
                "Montrer seulement la carte suivante",
                "Montrer maintenant et après",
                "Proposer un choix limité et sûr",
            ),
        ),
        adult_review=(
            "Je suis l’adulte responsable et j’ai vérifié que ces étapes conviennent à ce foyer",
            "Vérification adulte confirmée. Chaque carte reste facultative ; modifiez ou retirez ce qui ne convient pas aujourd’hui.",
            "Une vérification adulte est requise. Contrôlez sécurité, accès, consignes de soin, besoins du foyer et signaux actuels de l’enfant.",
        ),
        results=(
            "Créer les cartes privées",
            "Imprimer les cartes vérifiées",
            "Carte de routine facultative",
            "Peut être sautée, interrompue ou remplacée",
            "Carte pause : arrêtez la séquence et vérifiez ce dont le foyer a besoin maintenant.",
        ),
        steps=(
            (
                "Utilisez le repère calme qui ouvre habituellement la journée du foyer.",
                "Choisissez des vêtements validés par l’adulte responsable.",
                "Effectuez l’étape habituelle de toilette ou de soin avec l’aide adulte adaptée.",
                "Suivez l’étape de petit-déjeuner ou boisson prévue par la famille.",
                "Laissez l’adulte vérifier les affaires nécessaires pour la journée.",
                "Rejoignez avec l’adulte le point convenu pour être prêt.",
            ),
            (
                "Rejoignez l’espace de transition convenu dans le foyer.",
                "Posez les affaires à l’endroit choisi par l’adulte.",
                "Effectuez l’étape habituelle de toilette ou de soin avec l’aide adaptée.",
                "Prenez la pause repas, boisson ou repos prévue par la famille.",
                "Choisissez l’étape calme, motrice ou relationnelle validée par l’adulte.",
                "Laissez l’adulte annoncer ce qui vient ensuite aujourd’hui.",
            ),
            (
                "Laissez l’adulte choisir une petite zone sûre pour commencer.",
                "Rangez quelques jouets ou objets d’activité à leur place habituelle.",
                "Rangez livres ou matériel d’apprentissage à l’endroit validé.",
                "Placez vêtements ou objets souples à l’endroit prévu dans le foyer.",
                "Laissez à l’adulte les objets coupants, lourds, cassés ou incertains.",
                "Faites une pause et vérifiez ensemble que les passages et objets nécessaires restent accessibles.",
            ),
            (
                "Utilisez le repère calme qui ouvre habituellement la routine du coucher.",
                "Effectuez l’étape habituelle de toilette avec l’aide adulte adaptée.",
                "Choisissez une tenue de nuit validée pour le foyer et les conditions.",
                "Effectuez les soins dentaires selon les consignes familiales et professionnelles actuelles.",
                "Choisissez le moment habituel de calme, histoire ou lien familial.",
                "Terminez dans l’environnement de sommeil convenu, avec l’adulte à proximité si nécessaire.",
            ),
        ),
        cue_notes=(
            "Gardez seulement la prochaine carte visible ; révélez-en une autre après contrôle de la situation par l’adulte.",
            "Montrez la carte actuelle et la suivante sans en faire des échéances.",
            "Proposez un choix uniquement si les deux options sont sûres, disponibles et acceptées par l’adulte.",
        ),
        boundary=(
            "Le planificateur ignore âge, développement, handicap, santé, besoins sensoriels, plan de soins, culture, foyer, état actuel et environnement. "
            "L’adulte responsable doit adapter, retirer ou arrêter chaque carte."
        ),
        preflight=(
            "Quatre contrôles avant une carte",
            "Confirmez que l’étape est sûre et adaptée ici et maintenant.",
            "Préservez l’accès à nourriture, eau, toilettes, médicaments, communication, mobilité et confort.",
            "Suivez les consignes professionnelles actuelles lorsqu’elles s’appliquent ; une carte ne les remplace jamais.",
            "Interrompez, sautez ou modifiez la séquence si l’enfant ou le foyer a besoin d’autre chose.",
        ),
        sources=(
            "Contexte officiel sur les routines, sans recommandation",
            "Les CDC présentent cohérence et prévisibilité comme des éléments de la structure familiale et indiquent que chaque famille choisit ses routines. Cela ne valide pas l’outil et ne garantit aucun résultat.",
            "CDC : créer des routines cohérentes et une structure familiale",
        ),
        webmcp=(
            "Aperçu de l’API WebMCP impérative de Chrome",
            "Crée trois à six cartes familiales facultatives vérifiées par un adulte à partir de choix limités. N’accepte ni n’accède jamais aux noms, âges, horaires, écoles, lieux, photos, comptes, texte libre, comportements ou activités ; n’évalue, ne diagnostique, ne surveille et ne promet aucun résultat.",
        ),
        app=(
            "Envie d’une couche réutilisable pour adulte et enfant ?",
            "Lumi Mission Planet est facultatif. Sa fiche App Store actuelle décrit des missions de routine en famille, un tableau de bord pour adultes, des données sur l’appareil, sans compte ni analyse tierce, et un téléchargement gratuit avec déverrouillage unique. Consultez la fiche actuelle pour les fonctions et disponibilités exactes. Ces cartes fonctionnent sans l’app.",
            "Adultes : voir Lumi Mission Planet sur l’App Store",
        ),
        faq=(
            "Questions sur les cartes de routine",
            (
                (
                    "La page recueille-t-elle des données sur un enfant ?",
                    "Non. Elle reçoit seulement des choix limités du foyer et ne demande jamais nom, âge, emploi du temps, école, profil ou activité.",
                ),
                (
                    "Est-ce un programme comportemental ou un plan de soins ?",
                    "Non. Ce sont des repères domestiques amovibles ; ils ne diagnostiquent, ne prescrivent, ne surveillent et ne promettent rien.",
                ),
                (
                    "Et si une étape ne convient pas aujourd’hui ?",
                    "L’adulte responsable doit la sauter, la remplacer ou l’arrêter. Chaque carte est facultative.",
                ),
            ),
        ),
        footer="Séquence vérifiée par un adulte uniquement · aucune donnée enfant · aucun suivi · aucun résultat promis",
        inline="Planifier des cartes familiales privées vérifiées par un adulte avant de choisir une app",
        index=(
            "Planificateur privé de cartes de routine familiale",
            "Créez une séquence facultative sans saisir de données enfant ni suivre les étapes.",
        ),
    ),
    "ja": _copy(
        meta=(
            "子どもの情報を入れない家族ルーティンカード作成",
            "子どもの名前、年齢、予定、園や学校、行動、達成記録を入力せず、大人が確認した3〜6枚の生活カードを作ります。",
            "無料ツール",
            "English",
            "無料・保護者向け・子どもプロフィールなし",
            "プライベートな家族ルーティンカード作成",
            "家庭の場面と表示形式を選択。見守る大人が各手順を確認した後だけ、飛ばせる順番カードを表示します。",
        ),
        badges=(
            "名前・年齢・子どもプロフィール不要",
            "行動や達成の記録なし",
            "アカウント・送信・保存なし",
            "成果や自立を保証しない",
        ),
        planner=(
            "大人が確認したカードの流れを作る",
            "カードは家庭の手順を並べるだけです。子どもを評価せず、ケアを指示せず、行動・睡眠・健康・学習・家庭の成果を予測しません。",
        ),
        labels=(
            "生活の場面",
            "カード枚数",
            "カード表示",
            "穏やかな切り替え方",
        ),
        options=(
            ("朝", "帰宅後", "片づけ", "就寝前"),
            ("文字", "大きな絵と文字", "絵と文字"),
            (
                "次の1枚だけ見せる",
                "今と次を見せる",
                "安全な2択を1つ示す",
            ),
        ),
        adult_review=(
            "見守る大人として、この家庭に合う手順か確認しました",
            "大人の確認済みです。すべて任意です。今日に合わないカードは変更または削除してください。",
            "大人の確認が必要です。安全、必要なアクセス、ケアの指示、家庭の事情、今の子どもの様子を確かめてください。",
        ),
        results=(
            "非公開カードを作成",
            "確認済みカードを印刷",
            "任意の生活カード",
            "飛ばす・休む・入れ替えることができます",
            "休憩カード：流れを止め、家庭に今必要なことを大人が確認します。",
        ),
        steps=(
            (
                "家庭でいつも使う穏やかな朝の合図から始めます。",
                "見守る大人が確認した服を選びます。",
                "家庭でいつも行う洗面や身支度を、必要な大人の手助けとともに進めます。",
                "家庭で決めた朝食または飲み物の手順に進みます。",
                "その日に必要な持ち物を大人が確認します。",
                "見守る大人と一緒に、家庭で決めた準備完了の場所へ移ります。",
            ),
            (
                "家庭で決めた帰宅後の切り替え場所へ行きます。",
                "持ち物を大人が決めた場所に置きます。",
                "いつもの洗面やケアを、必要な手助けとともに進めます。",
                "家庭で予定した食事、飲み物、休憩の時間を取ります。",
                "大人が確認した静かな時間、体を動かす時間、ふれあいの時間から選びます。",
                "今日この後にすることを大人が伝えます。",
            ),
            (
                "大人が小さく安全な範囲を1つ選びます。",
                "おもちゃや遊び道具を少しだけ、いつもの場所へ戻します。",
                "本や学習用品を大人が確認した場所へ戻します。",
                "衣類や柔らかい物を家庭で決めた場所へ置きます。",
                "鋭い物、重い物、壊れた物、判断に迷う物は大人に任せます。",
                "一緒に休み、通り道と必要な物が使える状態か確認します。",
            ),
            (
                "家庭でいつも使う穏やかな就寝前の合図から始めます。",
                "いつもの洗面やトイレの手順を、必要な大人の手助けとともに進めます。",
                "家庭とその日の環境に合う寝間着を大人と選びます。",
                "家庭と専門家の現在の案内に沿って歯のケアを行います。",
                "家庭でいつも行う静かなふれあい、読み聞かせ、落ち着く時間から選びます。",
                "家庭で決めた睡眠環境に整え、必要に応じて大人がそばにいます。",
            ),
        ),
        cue_notes=(
            "次の1枚だけを見せ、状況を大人が確認してから次を出します。",
            "今のカードと次のカードを見せますが、締め切りとして扱いません。",
            "どちらも安全で実行でき、大人が認めた場合だけ選択肢を示します。",
        ),
        boundary=(
            "このツールは、年齢、発達、障害、健康、感覚面の必要、ケア計画、文化、家庭、今の状態、環境を知りません。"
            "見守る大人がすべてのカードを調整、削除、中止してください。"
        ),
        preflight=(
            "カードを使う前の4項目",
            "今いる場所と時点で、安全かつ適切な手順か確認します。",
            "食事、水分、トイレ、薬、連絡、移動、安心に必要なアクセスを妨げません。",
            "必要な場面では現在の専門的なケア案内を優先し、カードで置き換えません。",
            "子どもや家庭が別のことを必要としたら、休止、スキップ、変更します。",
        ),
        sources=(
            "公的なルーティン情報（推奨を意味しません）",
            "CDCは家庭の構造に一貫性と予測可能性が含まれると説明し、どのルーティンが合うかは家庭が決めるとしています。本ツールの有効性や成果を保証するものではありません。",
            "CDC：一貫したルーティンと家庭の構造",
        ),
        webmcp=(
            "Chrome WebMCP imperative API プレビュー",
            "画面上の限られた選択肢だけから、大人が確認する任意の家族生活カードを3〜6枚作ります。子どもの名前、年齢、予定、園や学校、場所、写真、アカウント、自由入力、行動、達成記録を受け取らずアクセスもしません。採点、診断、監視、成果保証も行いません。",
        ),
        app=(
            "親子で繰り返し使える仕組みも必要ですか？",
            "Lumi Mission Planetは任意です。現在のApp Store掲載情報では、親子で使う生活ミッション、保護者向け画面、端末内データ、アカウントや第三者解析なし、無料ダウンロードと買い切り解除を案内しています。正確な提供状況と機能は最新の掲載情報をご確認ください。このカードはアプリなしで使えます。",
            "保護者の方：App StoreでLumi Mission Planetを見る",
        ),
        faq=(
            "家族ルーティンカードの質問",
            (
                (
                    "子どもの情報を収集しますか？",
                    "いいえ。家庭の限られた選択肢だけを受け取り、名前、年齢、予定、園や学校、プロフィール、活動は一切尋ねません。",
                ),
                (
                    "行動プログラムやケア計画ですか？",
                    "いいえ。取り外せる家庭用の順番提示であり、診断、指示、監視、成果保証は行いません。",
                ),
                (
                    "今日合わない手順があったら？",
                    "見守る大人が飛ばす、入れ替える、中止する判断をしてください。すべて任意です。",
                ),
            ),
        ),
        footer="大人が確認した順番のみ・子どもの情報なし・追跡なし・成果保証なし",
        inline="アプリを選ぶ前に、大人が確認する非公開の家族ルーティンカードを作る",
        index=(
            "家族ルーティンカード作成",
            "子どもの情報や達成記録を入力せず、飛ばせる家庭の順番カードを作ります。",
        ),
    ),
    "ko": _copy(
        meta=(
            "아동 정보를 받지 않는 가족 루틴 카드 플래너",
            "아이의 이름, 나이, 일정, 학교, 행동, 완료 기록을 입력하지 않고 보호자가 확인한 3~6장의 생활 카드를 만듭니다.",
            "무료 도구",
            "English",
            "무료 · 보호자용 · 아동 프로필 없음",
            "비공개 가족 루틴 카드 플래너",
            "가정 상황과 카드 형식을 고르세요. 보호자가 모든 단계를 확인한 뒤에만 건너뛸 수 있는 순서가 표시됩니다.",
        ),
        badges=(
            "이름·나이·아동 프로필 없음",
            "행동·완료 추적 없음",
            "계정·전송·저장 없음",
            "결과·독립성 보장 없음",
        ),
        planner=(
            "보호자가 확인한 카드 순서 만들기",
            "카드는 집안 순서만 정리합니다. 아이를 평가하거나 돌봄을 처방하지 않으며 행동, 수면, 건강, 학습, 가족의 결과를 예측하지 않습니다.",
        ),
        labels=(
            "생활 상황",
            "카드 수",
            "카드 표시",
            "부드러운 전환 안내",
        ),
        options=(
            ("아침", "하원·하교 후", "정리", "잠자리"),
            ("글자", "큰 그림과 글자", "그림과 글자"),
            (
                "다음 카드만 보여 주기",
                "지금과 다음을 보여 주기",
                "안전한 제한 선택지 하나 제시",
            ),
        ),
        adult_review=(
            "보호하는 성인으로서 이 단계가 우리 집에 맞는지 확인했습니다",
            "보호자 확인이 끝났습니다. 모든 카드는 선택 사항이며 오늘 맞지 않으면 바꾸거나 빼세요.",
            "보호자 확인이 필요합니다. 안전, 필요한 접근, 돌봄 지침, 가정 상황, 아이의 현재 신호를 살펴보세요.",
        ),
        results=(
            "비공개 카드 만들기",
            "확인한 카드 인쇄",
            "선택 생활 카드",
            "건너뛰기·멈추기·바꾸기 가능",
            "멈춤 카드: 순서를 중단하고 지금 가족에게 무엇이 필요한지 확인하세요.",
        ),
        steps=(
            (
                "가정에서 평소 사용하는 차분한 아침 시작 신호를 사용하세요.",
                "보호자가 확인한 옷을 고르세요.",
                "평소 씻기나 돌봄 단계를 필요한 성인 도움과 함께 진행하세요.",
                "가족이 계획한 아침 식사나 음료 단계로 넘어가세요.",
                "오늘 필요한 물건은 성인이 확인하세요.",
                "보호자와 함께 가정에서 정한 준비 장소로 이동하세요.",
            ),
            (
                "가정에서 정한 귀가 후 전환 장소로 가세요.",
                "소지품을 보호자가 정한 곳에 두세요.",
                "평소 씻기나 돌봄 단계를 필요한 도움과 함께 진행하세요.",
                "가족이 계획한 음식, 음료, 휴식 시간을 가지세요.",
                "보호자가 확인한 조용한 시간, 움직임, 교감 단계 중 하나를 고르세요.",
                "오늘 다음에 할 일을 성인이 미리 알려 주세요.",
            ),
            (
                "보호자가 작고 안전한 한 구역을 정해 시작하세요.",
                "장난감이나 활동 물건 몇 개를 평소 자리로 돌려놓으세요.",
                "책이나 학습 물건을 보호자가 확인한 장소에 두세요.",
                "옷이나 부드러운 물건을 가정에서 정한 곳에 두세요.",
                "날카롭거나 무겁거나 깨졌거나 판단하기 어려운 물건은 성인에게 맡기세요.",
                "함께 멈춰 통로와 필요한 물건을 계속 이용할 수 있는지 확인하세요.",
            ),
            (
                "가정에서 평소 사용하는 차분한 잠자리 시작 신호를 사용하세요.",
                "평소 씻기나 화장실 단계를 필요한 성인 도움과 함께 진행하세요.",
                "가정과 환경에 맞는 잠옷을 보호자와 고르세요.",
                "가족과 전문가의 현재 안내에 따라 치아 관리를 하세요.",
                "평소의 차분한 교감, 이야기, 안정을 위한 단계 중 하나를 고르세요.",
                "가정에서 정한 수면 환경으로 마치고 필요하면 성인이 가까이 있으세요.",
            ),
        ),
        cue_notes=(
            "다음 카드 한 장만 보이고 보호자가 현재 상황을 확인한 뒤 다른 카드를 보여 주세요.",
            "현재와 다음 카드를 보여 주되 어느 쪽도 마감 시간으로 취급하지 마세요.",
            "두 선택 모두 안전하고 가능하며 보호자가 허용할 때만 선택지를 주세요.",
        ),
        boundary=(
            "이 도구는 아이의 나이, 발달, 장애, 건강, 감각적 필요, 돌봄 계획, 문화, 가정, 현재 상태, 환경을 알지 못합니다. "
            "보호자가 모든 카드를 조정하거나 빼거나 중단해야 합니다."
        ),
        preflight=(
            "카드 사용 전 네 가지 확인",
            "지금 이 장소와 순간에 안전하고 알맞은 단계인지 확인하세요.",
            "음식, 물, 화장실, 약, 의사소통, 이동, 편안함에 필요한 접근을 막지 마세요.",
            "해당하는 경우 현재 전문 돌봄 지침을 우선하고 카드로 대신하지 마세요.",
            "아이 또는 가족에게 다른 것이 필요하면 순서를 멈추거나 건너뛰거나 바꾸세요.",
        ),
        sources=(
            "공식 루틴 정보이며 추천을 뜻하지 않음",
            "CDC는 일관성과 예측 가능성을 가정 구조의 일부로 설명하고 어떤 루틴이 맞는지는 각 가족이 정한다고 안내합니다. 이 도구의 효과나 결과를 보장하는 내용은 아닙니다.",
            "CDC: 일관된 루틴과 가정 구조 만들기",
        ),
        webmcp=(
            "Chrome 명령형 WebMCP API 미리보기",
            "화면의 제한된 선택지만으로 보호자가 확인하는 선택형 가족 생활 카드 3~6장을 만듭니다. 아이 이름, 나이, 일정, 학교, 장소, 사진, 계정, 자유 입력, 행동, 완료 기록을 받거나 접근하지 않으며 채점, 진단, 감시, 결과 보장을 하지 않습니다.",
        ),
        app=(
            "보호자와 아이가 반복해서 쓸 수 있는 방식도 필요하다면",
            "Lumi Mission Planet은 선택 사항입니다. 현재 App Store 설명은 보호자와 아이가 함께 쓰는 생활 미션, 보호자 화면, 기기 내 데이터, 계정 및 제3자 분석 없음, 무료 다운로드와 일회성 잠금 해제를 안내합니다. 정확한 제공 여부와 기능은 최신 설명을 확인하세요. 이 카드는 앱 없이도 쓸 수 있습니다.",
            "보호자: App Store에서 Lumi Mission Planet 보기",
        ),
        faq=(
            "가족 루틴 카드 질문",
            (
                (
                    "아이 정보를 수집하나요?",
                    "아니요. 제한된 가정 선택지만 받고 이름, 나이, 일정, 학교, 프로필, 활동을 묻지 않습니다.",
                ),
                (
                    "행동 프로그램이나 돌봄 계획인가요?",
                    "아니요. 뺄 수 있는 가정용 순서 안내이며 진단, 처방, 감시, 결과 보장을 하지 않습니다.",
                ),
                (
                    "오늘 맞지 않는 단계가 있으면 어떻게 하나요?",
                    "보호자가 건너뛰거나 바꾸거나 중단하세요. 모든 카드는 선택 사항입니다.",
                ),
            ),
        ),
        footer="보호자가 확인한 순서만 사용 · 아동 정보 없음 · 추적 없음 · 결과 보장 없음",
        inline="앱을 고르기 전에 보호자가 확인하는 비공개 가족 루틴 카드 계획하기",
        index=(
            "비공개 가족 루틴 카드 플래너",
            "아동 정보나 완료 기록 없이 건너뛸 수 있는 가정 순서를 만듭니다.",
        ),
    ),
    "zh-Hant": _copy(
        meta=(
            "私密家庭作息卡規劃器｜不填孩子資料",
            "不用輸入孩子姓名、年齡、時間表、學校、行為或完成紀錄，由大人確認後建立 3–6 張家庭作息卡。",
            "免費工具",
            "English",
            "免費・家長使用・不建立孩子檔案",
            "私密家庭作息卡規劃器",
            "選擇家庭情境與卡片形式；只有陪同大人確認每一步適合後，才顯示可跳過的順序卡。",
        ),
        badges=(
            "不填姓名、年齡或孩子檔案",
            "不追蹤行為或完成狀態",
            "無帳號、上傳或儲存",
            "不保證成果或獨立能力",
        ),
        planner=(
            "建立由大人確認的卡片順序",
            "卡片只整理家庭步驟；不評估孩子、不提供照護處方，也不預測行為、睡眠、健康、學習或家庭成果。",
        ),
        labels=(
            "作息情境",
            "卡片數量",
            "卡片形式",
            "溫和轉場提示",
        ),
        options=(
            ("早晨", "放學或托育返家後", "收拾整理", "睡前"),
            ("文字", "大圖示加文字", "圖示與文字"),
            (
                "只顯示下一張",
                "顯示現在與下一張",
                "提供一組安全的有限選擇",
            ),
        ),
        adult_review=(
            "我是陪同大人，已確認這些步驟適合目前家庭",
            "已完成大人檢查。每張卡都只是選用；今天不適合的內容請更換或移除。",
            "卡片出現前必須由大人檢查安全、必要使用權、照護指示、家庭需求與孩子目前訊號。",
        ),
        results=(
            "建立私密卡片",
            "列印已確認卡片",
            "選用作息卡",
            "可以跳過、暫停或更換",
            "暫停卡：停止目前順序，由大人確認家庭現在真正需要什麼。",
        ),
        steps=(
            (
                "使用家中平常的溫和早晨開始提示。",
                "選擇已由陪同大人確認的衣物。",
                "依家庭平常方式完成清潔或照護步驟，並由大人提供適當協助。",
                "進行家人原本規劃的早餐或飲水步驟。",
                "由大人檢查今天需要攜帶的物品。",
                "和陪同大人一起前往家中約定的準備位置。",
            ),
            (
                "抵達家中約定的返家轉場位置。",
                "把隨身物品放到大人選定的位置。",
                "依平常方式完成清潔或照護步驟，並取得適當協助。",
                "進行家人原本規劃的飲食、飲水或休息片刻。",
                "選擇大人核准的安靜、活動或親子連結步驟。",
                "由大人預告今天接下來的安排。",
            ),
            (
                "由大人選擇一小塊安全區域開始。",
                "把少量玩具或活動用品放回平常位置。",
                "把書本或學習用品放回大人確認的位置。",
                "把衣物或柔軟物品放到家中原定位置。",
                "尖銳、沉重、破損或無法判斷的物品交給大人處理。",
                "一起暫停，檢查走道與必要物品仍可正常使用。",
            ),
            (
                "使用家中平常的溫和睡前開始提示。",
                "依平常方式完成清潔或如廁步驟，並由大人提供適當協助。",
                "選擇適合家庭與當下環境、已由大人確認的睡衣。",
                "依家庭與專業人員目前指引完成牙齒照護。",
                "選擇家中平常的安靜陪伴、故事或沉澱步驟。",
                "回到家庭約定的睡眠環境，必要時由陪同大人在附近支持。",
            ),
        ),
        cue_notes=(
            "只讓下一張卡保持可見；大人確認當下狀況後才顯示另一張。",
            "同時顯示目前與下一張卡，但不把任何一張當成期限。",
            "只有兩個選項都安全、可行且大人同意時，才提供選擇。",
        ),
        boundary=(
            "本規劃器不知道孩子的年齡、發展、障礙、健康、感官需求、照護計畫、文化、家庭、當下狀態或環境。"
            "陪同大人必須視需要調整、移除或停止每一張卡。"
        ),
        preflight=(
            "使用卡片前的四項檢查",
            "確認這一步在目前地點與時刻安全且適合。",
            "保留飲食、飲水、如廁、藥物、溝通、行動與舒適所需的使用權。",
            "適用時遵循目前專業照護指引；卡片永遠不能取代指引。",
            "孩子或家庭需要不同安排時，立即暫停、跳過或更換順序。",
        ),
        sources=(
            "官方作息背景，並非推薦",
            "CDC 把一致性與可預期性列為家庭結構的一部分，也說每個家庭自行決定適合的作息；這不代表 CDC 認可本工具，也不保證任何成果。",
            "CDC：建立一致作息與家庭結構",
        ),
        webmcp=(
            "Chrome imperative WebMCP API 預覽",
            "只用畫面上的有限選項建立 3–6 張由大人確認的選用家庭作息卡；不接收或存取孩子姓名、年齡、時間表、學校、位置、照片、帳號、自由文字、行為或完成紀錄，也不評分、診斷、監看或承諾成果。",
        ),
        app=(
            "需要可重複使用的親子作息層？",
            "Lumi 任務星球是選用項目。目前 App Store 頁面描述親子共同使用的作息任務、家長後台、資料留在裝置、不需帳號或第三方分析，以及免費下載與一次性解鎖。確切功能與供應狀態請查看目前頁面；這些卡片不安裝 App 也能使用。",
            "家長：前往 App Store 查看 Lumi 任務星球",
        ),
        faq=(
            "家庭作息卡常見問題",
            (
                (
                    "這個頁面會收集孩子資料嗎？",
                    "不會。只接收有限家庭選項，完全不詢問姓名、年齡、時間表、學校、檔案或活動紀錄。",
                ),
                (
                    "這是行為方案或照護計畫嗎？",
                    "不是。這只是可移除的家庭順序提示，不診斷、不開立建議、不監看，也不承諾成果。",
                ),
                (
                    "某一步今天不適合怎麼辦？",
                    "由陪同大人直接跳過、更換或停止；每張卡都只是選用。",
                ),
            ),
        ),
        footer="只用大人確認的順序・不收孩子資料・不追蹤・不保證成果",
        inline="選擇 App 前，先規劃由大人確認的私密家庭作息卡",
        index=(
            "私密家庭作息卡規劃器",
            "不填孩子資料或完成紀錄，建立可跳過的家庭順序卡。",
        ),
    ),
    "zh-Hans": _copy(
        meta=(
            "私密家庭作息卡规划器｜不填孩子资料",
            "不用输入孩子姓名、年龄、时间表、学校、行为或完成记录，由成人确认后建立 3–6 张家庭作息卡。",
            "免费工具",
            "English",
            "免费・家长使用・不建立孩子档案",
            "私密家庭作息卡规划器",
            "选择家庭情境和卡片形式；只有陪同成人确认每一步合适后，才显示可跳过的顺序卡。",
        ),
        badges=(
            "不填姓名、年龄或孩子档案",
            "不跟踪行为或完成状态",
            "无账号、上传或存储",
            "不保证成果或独立能力",
        ),
        planner=(
            "建立由成人确认的卡片顺序",
            "卡片只整理家庭步骤；不评估孩子、不提供照护处方，也不预测行为、睡眠、健康、学习或家庭成果。",
        ),
        labels=(
            "作息情境",
            "卡片数量",
            "卡片形式",
            "温和过渡提示",
        ),
        options=(
            ("早晨", "放学或托育回家后", "收拾整理", "睡前"),
            ("文字", "大图标加文字", "图标和文字"),
            (
                "只显示下一张",
                "显示现在和下一张",
                "提供一组安全的有限选择",
            ),
        ),
        adult_review=(
            "我是陪同成人，已确认这些步骤适合当前家庭",
            "已完成成人检查。每张卡都只是可选；今天不合适的内容请更换或删除。",
            "卡片出现前必须由成人检查安全、必要使用权、照护指引、家庭需求和孩子当前信号。",
        ),
        results=(
            "建立私密卡片",
            "打印已确认卡片",
            "可选作息卡",
            "可以跳过、暂停或更换",
            "暂停卡：停止当前顺序，由成人确认家庭现在真正需要什么。",
        ),
        steps=(
            (
                "使用家中平常的温和早晨开始提示。",
                "选择已由陪同成人确认的衣物。",
                "按家庭平常方式完成清洁或照护步骤，并由成人提供适当帮助。",
                "进行家人原本安排的早餐或饮水步骤。",
                "由成人检查今天需要携带的物品。",
                "和陪同成人一起前往家中约定的准备位置。",
            ),
            (
                "到达家中约定的回家过渡位置。",
                "把随身物品放到成人选定的位置。",
                "按平常方式完成清洁或照护步骤，并获得适当帮助。",
                "进行家人原本安排的饮食、饮水或休息片刻。",
                "选择成人批准的安静、活动或亲子连接步骤。",
                "由成人预告今天接下来的安排。",
            ),
            (
                "由成人选择一小块安全区域开始。",
                "把少量玩具或活动用品放回平常位置。",
                "把书本或学习用品放回成人确认的位置。",
                "把衣物或柔软物品放到家中原定位置。",
                "尖锐、沉重、破损或无法判断的物品交给成人处理。",
                "一起暂停，检查通道和必要物品仍可正常使用。",
            ),
            (
                "使用家中平常的温和睡前开始提示。",
                "按平常方式完成清洁或如厕步骤，并由成人提供适当帮助。",
                "选择适合家庭和当前环境、已由成人确认的睡衣。",
                "按家庭和专业人员当前指引完成牙齿护理。",
                "选择家中平常的安静陪伴、故事或放松步骤。",
                "回到家庭约定的睡眠环境，必要时由陪同成人在附近支持。",
            ),
        ),
        cue_notes=(
            "只让下一张卡保持可见；成人确认当前情况后才显示另一张。",
            "同时显示当前和下一张卡，但不把任何一张当成期限。",
            "只有两个选项都安全、可行且成人同意时，才提供选择。",
        ),
        boundary=(
            "本规划器不知道孩子的年龄、发展、残障、健康、感官需求、照护计划、文化、家庭、当前状态或环境。"
            "陪同成人必须按需要调整、删除或停止每一张卡。"
        ),
        preflight=(
            "使用卡片前的四项检查",
            "确认这一步在当前地点和时刻安全且合适。",
            "保留饮食、饮水、如厕、药物、沟通、行动和舒适所需的使用权。",
            "适用时遵循当前专业照护指引；卡片永远不能代替指引。",
            "孩子或家庭需要不同安排时，立即暂停、跳过或更换顺序。",
        ),
        sources=(
            "官方作息背景，并非推荐",
            "CDC 把一致性和可预期性列为家庭结构的一部分，也说明每个家庭自行决定合适的作息；这不代表 CDC 认可本工具，也不保证任何成果。",
            "CDC：建立一致作息和家庭结构",
        ),
        webmcp=(
            "Chrome imperative WebMCP API 预览",
            "只用页面上的有限选项建立 3–6 张由成人确认的可选家庭作息卡；不接收或访问孩子姓名、年龄、时间表、学校、位置、照片、账号、自由文本、行为或完成记录，也不评分、诊断、监测或承诺成果。",
        ),
        app=(
            "需要可重复使用的亲子作息层？",
            "Lumi Mission Planet 是可选项目。目前 App Store 页面描述亲子共同使用的作息任务、家长后台、数据留在设备、不需账号或第三方分析，以及免费下载和一次性解锁。具体功能和供应状态请查看当前页面；这些卡片不安装 App 也能使用。",
            "家长：前往 App Store 查看 Lumi Mission Planet",
        ),
        faq=(
            "家庭作息卡常见问题",
            (
                (
                    "这个页面会收集孩子资料吗？",
                    "不会。只接收有限家庭选项，完全不询问姓名、年龄、时间表、学校、档案或活动记录。",
                ),
                (
                    "这是行为方案或照护计划吗？",
                    "不是。这只是可删除的家庭顺序提示，不诊断、不开立建议、不监测，也不承诺成果。",
                ),
                (
                    "某一步今天不合适怎么办？",
                    "由陪同成人直接跳过、更换或停止；每张卡都只是可选。",
                ),
            ),
        ),
        footer="只用成人确认的顺序・不收孩子资料・不跟踪・不保证成果",
        inline="选择 App 前，先规划由成人确认的私密家庭作息卡",
        index=(
            "私密家庭作息卡规划器",
            "不填孩子资料或完成记录，建立可跳过的家庭顺序卡。",
        ),
    ),
    "vi": _copy(
        meta=(
            "Trình lập thẻ nếp sinh hoạt gia đình riêng tư | Không dữ liệu trẻ",
            "Tạo chuỗi ba đến sáu thẻ nếp sinh hoạt do phụ huynh duyệt mà không nhập tên, tuổi, lịch, trường, hành vi hay hồ sơ hoàn thành của trẻ.",
            "Công cụ miễn phí",
            "English",
            "Miễn phí · dành cho phụ huynh · không hồ sơ trẻ",
            "Trình lập thẻ nếp sinh hoạt gia đình riêng tư",
            "Chọn bối cảnh gia đình và định dạng thẻ. Trang chỉ trả về chuỗi thẻ có thể bỏ qua và gỡ bỏ sau khi người lớn xác nhận từng bước phù hợp.",
        ),
        badges=(
            "Không tên, tuổi hay hồ sơ trẻ",
            "Không theo dõi hành vi hay hoàn thành",
            "Không tài khoản, tải lên hay lưu trữ",
            "Không hứa hẹn kết quả hay tự lập",
        ),
        planner=(
            "Tạo chuỗi thẻ do người lớn duyệt",
            "Các thẻ này sắp xếp các bước trong nhà; chúng không đánh giá trẻ, không kê đơn chăm sóc và không dự đoán hành vi, giấc ngủ, sức khỏe, học tập hay kết quả gia đình.",
        ),
        labels=(
            "Bối cảnh nếp sinh hoạt",
            "Số lượng thẻ",
            "Cách trình bày thẻ",
            "Gợi ý chuyển tiếp nhẹ nhàng",
        ),
        options=(
            (
                "Buổi sáng",
                "Sau giờ học hoặc trông trẻ",
                "Dọn dẹp",
                "Giờ đi ngủ",
            ),
            (
                "Chữ",
                "Biểu tượng lớn kèm nhãn",
                "Biểu tượng và chữ",
            ),
            (
                "Chỉ hiện thẻ tiếp theo",
                "Hiện thẻ bây giờ và tiếp theo",
                "Đưa ra một lựa chọn an toàn có giới hạn",
            ),
        ),
        adult_review=(
            "Tôi là người lớn giám sát và đã kiểm tra các bước đã chọn cho gia đình này",
            "Đã xác nhận người lớn duyệt. Giữ mọi thẻ là tùy chọn và thay đổi hoặc gỡ bỏ bất cứ gì không phù hợp hôm nay.",
            "Cần người lớn duyệt trước khi thẻ xuất hiện. Kiểm tra an toàn, khả năng tiếp cận, hướng dẫn chăm sóc, nhu cầu gia đình và tín hiệu hiện tại của trẻ.",
        ),
        results=(
            "Tạo thẻ riêng tư",
            "In các thẻ đã duyệt",
            "Thẻ nếp sinh hoạt tùy chọn",
            "Có thể bỏ qua, tạm dừng hoặc thay thế",
            "Thẻ tạm dừng: dừng chuỗi và kiểm tra gia đình cần gì lúc này.",
        ),
        steps=(
            (
                "Dùng tín hiệu khởi đầu bình tĩnh quen thuộc của gia đình.",
                "Chọn quần áo mà người lớn giám sát đã chấp thuận.",
                "Hoàn thành bước rửa hoặc chăm sóc quen thuộc với sự trợ giúp phù hợp của người lớn.",
                "Dùng bước ăn sáng hoặc uống nước đã lên kế hoạch của gia đình.",
                "Để người lớn kiểm tra các vật dụng cần cho ngày hôm đó.",
                "Đi đến điểm sẵn sàng đã thống nhất cùng người lớn giám sát.",
            ),
            (
                "Đến điểm chuyển tiếp đã thống nhất của gia đình.",
                "Đặt đồ đạc vào nơi người lớn giám sát đã chọn.",
                "Dùng bước rửa hoặc chăm sóc quen thuộc với sự trợ giúp phù hợp.",
                "Dùng bước ăn, uống hoặc nghỉ đã lên kế hoạch của gia đình.",
                "Chọn bước yên tĩnh, vận động hoặc gắn kết đã được người lớn chấp thuận.",
                "Để người lớn xem trước điều gì đến tiếp theo hôm nay.",
            ),
            (
                "Để người lớn chọn một khu vực nhỏ, an toàn để bắt đầu.",
                "Trả vài món đồ chơi hoặc vật dụng về chỗ quen thuộc.",
                "Trả sách hoặc học liệu về nơi người lớn chấp thuận.",
                "Đặt quần áo hoặc đồ mềm vào nơi gia đình mong đợi.",
                "Để người lớn xử lý vật sắc, nặng, vỡ hoặc chưa chắc chắn.",
                "Cùng tạm dừng và kiểm tra lối đi cùng vật dụng cần thiết vẫn tiếp cận được.",
            ),
            (
                "Dùng tín hiệu bắt đầu giờ ngủ bình tĩnh quen thuộc của gia đình.",
                "Hoàn thành bước rửa hoặc vệ sinh quen thuộc với sự trợ giúp phù hợp của người lớn.",
                "Chọn quần áo ngủ phù hợp với gia đình và điều kiện.",
                "Chăm sóc răng theo hướng dẫn hiện tại của gia đình và chuyên môn.",
                "Chọn bước gắn kết yên tĩnh, kể chuyện hoặc dỗ ngủ quen thuộc của gia đình.",
                "Kết thúc với thiết lập giấc ngủ đã thống nhất và người lớn giám sát ở gần khi cần.",
            ),
        ),
        cue_notes=(
            "Chỉ giữ một thẻ tiếp theo hiển thị; chỉ hiện thẻ khác sau khi người lớn kiểm tra tình huống hiện tại.",
            "Hiện thẻ hiện tại và thẻ kế tiếp mà không coi thẻ nào là hạn chót.",
            "Chỉ đưa ra lựa chọn khi cả hai phương án đều an toàn, sẵn có và được người lớn giám sát chấp nhận.",
        ),
        boundary=(
            "Trình lập kế hoạch không bao giờ biết tuổi, sự phát triển, khuyết tật, sức khỏe, nhu cầu giác quan, kế hoạch chăm sóc, văn hóa, gia đình, trạng thái hiện tại hay môi trường của trẻ. "
            "Người lớn giám sát phải điều chỉnh, gỡ bỏ hoặc dừng mọi thẻ khi cần."
        ),
        preflight=(
            "Bốn điều cần kiểm trước khi dùng một thẻ",
            "Xác nhận bước đó an toàn và phù hợp ở nơi và thời điểm hiện tại.",
            "Giữ khả năng tiếp cận thức ăn, nước, nhà vệ sinh, thuốc, liên lạc, di chuyển và sự thoải mái.",
            "Dùng hướng dẫn chăm sóc chuyên môn hiện hành khi áp dụng; một thẻ không bao giờ thay thế nó.",
            "Tạm dừng, bỏ qua hoặc thay đổi chuỗi bất cứ khi nào trẻ hoặc gia đình cần điều khác.",
        ),
        sources=(
            "Bối cảnh nếp sinh hoạt chính thức, không phải sự chứng thực",
            "CDC mô tả sự nhất quán và tính dự đoán được là một phần của cấu trúc gia đình và nói rằng mỗi gia đình tự quyết định nếp nào phù hợp nhất. Hướng dẫn đó không xác nhận công cụ này hay bảo đảm kết quả.",
            "CDC: tạo nếp sinh hoạt nhất quán và cấu trúc gia đình",
        ),
        webmcp=(
            "Bản xem trước API mệnh lệnh WebMCP của Chrome",
            "Tạo ba đến sáu thẻ nếp sinh hoạt gia đình tùy chọn do phụ huynh duyệt, chỉ từ các lựa chọn hiển thị có giới hạn. Không bao giờ nhận hay truy cập tên, tuổi, lịch, trường, vị trí, ảnh, tài khoản, văn bản tự do, hành vi hay hồ sơ hoàn thành của trẻ; không bao giờ chấm điểm, chẩn đoán, theo dõi hay hứa hẹn kết quả.",
        ),
        app=(
            "Muốn một lớp nếp sinh hoạt cha mẹ–con tùy chọn, dùng lại được?",
            "Lumi Mission Planet là tùy chọn. Trang App Store hiện tại mô tả nhiệm vụ nếp sinh hoạt cha mẹ–con, bảng điều khiển cho phụ huynh, dữ liệu trên thiết bị, không tài khoản hay phân tích của bên thứ ba, và tải xuống miễn phí kèm mở khóa một lần. Hãy xem trang hiện tại để biết tình trạng và tính năng chính xác. Các thẻ in này hoạt động mà không cần app.",
            "Phụ huynh: xem Lumi Mission Planet trên App Store",
        ),
        faq=(
            "Câu hỏi về thẻ nếp sinh hoạt gia đình",
            (
                (
                    "Trang này có thu thập thông tin về trẻ không?",
                    "Không. Nó chỉ nhận các lựa chọn gia đình có giới hạn và không bao giờ hỏi tên, tuổi, lịch, trường, hồ sơ hay bản ghi hoạt động.",
                ),
                (
                    "Các thẻ có phải chương trình hành vi hay kế hoạch chăm sóc không?",
                    "Không. Đó là các gợi ý chuỗi gia đình có thể gỡ bỏ và không chẩn đoán, kê đơn, theo dõi hay hứa hẹn kết quả.",
                ),
                (
                    "Nếu một bước không phù hợp hôm nay thì sao?",
                    "Người lớn giám sát nên bỏ qua, thay thế hoặc dừng nó. Mọi thẻ đều là tùy chọn.",
                ),
            ),
        ),
        footer="Chỉ chuỗi do phụ huynh duyệt · không dữ liệu trẻ · không theo dõi · không hứa kết quả",
        inline="Lập thẻ nếp sinh hoạt gia đình riêng tư do phụ huynh duyệt trước khi chọn app",
        index=(
            "Trình lập thẻ nếp sinh hoạt gia đình riêng tư",
            "Tạo chuỗi gia đình có thể bỏ qua mà không nhập dữ liệu trẻ hay theo dõi hoàn thành.",
        ),
    ),
    "th": _copy(
        meta=(
            "ตัววางแผนการ์ดกิจวัตรครอบครัวแบบส่วนตัว | ไม่มีข้อมูลเด็ก",
            "สร้างลำดับการ์ดกิจวัตรสามถึงหกใบที่ผู้ปกครองตรวจสอบ โดยไม่กรอกชื่อ อายุ ตารางเวลา โรงเรียน พฤติกรรม หรือบันทึกการทำเสร็จของเด็ก",
            "เครื่องมือฟรี",
            "English",
            "ฟรี · สำหรับผู้ปกครอง · ไม่มีโปรไฟล์เด็ก",
            "ตัววางแผนการ์ดกิจวัตรครอบครัวแบบส่วนตัว",
            "เลือกบริบทของครอบครัวและรูปแบบการ์ด หน้าเว็บจะคืนลำดับการ์ดที่ข้ามและนำออกได้ หลังจากผู้ใหญ่ยืนยันว่าทุกขั้นตอนเหมาะสมแล้วเท่านั้น",
        ),
        badges=(
            "ไม่มีชื่อ อายุ หรือโปรไฟล์เด็ก",
            "ไม่ติดตามพฤติกรรมหรือการทำเสร็จ",
            "ไม่มีบัญชี อัปโหลด หรือจัดเก็บ",
            "ไม่รับประกันผลลัพธ์หรือการพึ่งตนเอง",
        ),
        planner=(
            "สร้างลำดับการ์ดที่ผู้ใหญ่ตรวจสอบ",
            "การ์ดเหล่านี้จัดระเบียบขั้นตอนในบ้าน ไม่ได้ประเมินเด็ก ไม่สั่งการดูแล และไม่ทำนายพฤติกรรม การนอน สุขภาพ การเรียนรู้ หรือผลลัพธ์ของครอบครัว",
        ),
        labels=(
            "บริบทกิจวัตร",
            "จำนวนการ์ด",
            "การแสดงการ์ด",
            "สัญญาณเปลี่ยนผ่านอย่างนุ่มนวล",
        ),
        options=(
            (
                "ตอนเช้า",
                "หลังเลิกเรียนหรือหลังรับเลี้ยง",
                "เก็บกวาด",
                "เวลานอน",
            ),
            (
                "คำ",
                "ไอคอนขนาดใหญ่พร้อมป้ายกำกับ",
                "ไอคอนและคำ",
            ),
            (
                "แสดงเฉพาะการ์ดถัดไป",
                "แสดงตอนนี้และถัดไป",
                "เสนอทางเลือกที่ปลอดภัยและมีขอบเขตหนึ่งอย่าง",
            ),
        ),
        adult_review=(
            "ฉันเป็นผู้ใหญ่ที่ดูแลและได้ตรวจสอบขั้นตอนที่เลือกสำหรับครอบครัวนี้แล้ว",
            "ยืนยันการตรวจสอบของผู้ใหญ่แล้ว ให้ทุกการ์ดเป็นทางเลือกและเปลี่ยนหรือนำสิ่งที่ไม่เหมาะสมวันนี้ออก",
            "ต้องมีการตรวจสอบของผู้ใหญ่ก่อนการ์ดจะปรากฏ ตรวจสอบความปลอดภัย การเข้าถึง แนวทางการดูแล ความต้องการของครอบครัว และสัญญาณปัจจุบันของเด็ก",
        ),
        results=(
            "สร้างการ์ดส่วนตัว",
            "พิมพ์การ์ดที่ตรวจสอบแล้ว",
            "การ์ดกิจวัตรแบบเลือกได้",
            "อาจข้าม หยุดชั่วคราว หรือแทนที่ได้",
            "การ์ดหยุด: หยุดลำดับและตรวจสอบว่าครอบครัวต้องการอะไรตอนนี้",
        ),
        steps=(
            (
                "ใช้สัญญาณเริ่มต้นอย่างสงบที่ครอบครัวใช้ประจำ",
                "เลือกเสื้อผ้าที่ผู้ใหญ่ที่ดูแลอนุมัติแล้ว",
                "ทำขั้นตอนล้างหรือดูแลที่ทำประจำพร้อมความช่วยเหลือที่เหมาะสมจากผู้ใหญ่",
                "ใช้ขั้นตอนอาหารเช้าหรือเครื่องดื่มที่ครอบครัววางแผนไว้",
                "ให้ผู้ใหญ่ตรวจสิ่งของที่ต้องใช้ในวันนั้น",
                "ไปยังจุดพร้อมที่ครอบครัวตกลงกันพร้อมผู้ใหญ่ที่ดูแล",
            ),
            (
                "มาถึงจุดเปลี่ยนผ่านที่ครอบครัวตกลงกัน",
                "วางสัมภาระในที่ที่ผู้ใหญ่ที่ดูแลเลือกไว้",
                "ทำขั้นตอนล้างหรือดูแลที่ทำประจำพร้อมความช่วยเหลือที่เหมาะสม",
                "ทำขั้นตอนอาหาร เครื่องดื่ม หรือพักที่ครอบครัววางแผนไว้",
                "เลือกขั้นตอนเงียบ เคลื่อนไหว หรือเชื่อมสัมพันธ์ที่ผู้ใหญ่อนุมัติ",
                "ให้ผู้ใหญ่ดูตัวอย่างว่าอะไรจะมาถัดไปในวันนี้",
            ),
            (
                "ให้ผู้ใหญ่เลือกพื้นที่เล็กและปลอดภัยหนึ่งจุดเพื่อเริ่ม",
                "นำของเล่นหรืออุปกรณ์กิจกรรมไม่กี่ชิ้นกลับไปที่เดิม",
                "นำหนังสือหรือสื่อการเรียนกลับไปที่ที่ผู้ใหญ่อนุมัติ",
                "วางเสื้อผ้าหรือของนุ่มในที่ที่ครอบครัวคาดหวัง",
                "ให้ผู้ใหญ่จัดการของมีคม หนัก แตก หรือไม่แน่ใจ",
                "หยุดพักด้วยกันและตรวจว่าทางเดินและสิ่งของที่จำเป็นยังเข้าถึงได้",
            ),
            (
                "ใช้สัญญาณเริ่มเวลานอนอย่างสงบที่ครอบครัวใช้ประจำ",
                "ทำขั้นตอนล้างหรือเข้าห้องน้ำที่ทำประจำพร้อมความช่วยเหลือที่เหมาะสมจากผู้ใหญ่",
                "เลือกชุดนอนที่เหมาะกับครอบครัวและสภาพอากาศ",
                "ดูแลฟันตามแนวทางปัจจุบันของครอบครัวและผู้เชี่ยวชาญ",
                "เลือกขั้นตอนเชื่อมสัมพันธ์เงียบ เล่านิทาน หรือกล่อมนอนที่ครอบครัวทำประจำ",
                "จบด้วยการจัดที่นอนที่ตกลงกันและมีผู้ใหญ่ที่ดูแลอยู่ใกล้เมื่อจำเป็น",
            ),
        ),
        cue_notes=(
            "แสดงการ์ดถัดไปเพียงใบเดียว เปิดเผยใบอื่นหลังจากผู้ใหญ่ตรวจสถานการณ์ปัจจุบันแล้วเท่านั้น",
            "แสดงการ์ดปัจจุบันและใบถัดไปโดยไม่ถือว่าใบใดเป็นกำหนดเส้นตาย",
            "เสนอทางเลือกเฉพาะเมื่อทั้งสองตัวเลือกปลอดภัย มีให้ และผู้ใหญ่ที่ดูแลยอมรับได้",
        ),
        boundary=(
            "ตัววางแผนไม่เคยรู้ อายุ พัฒนาการ ความพิการ สุขภาพ ความต้องการทางประสาทสัมผัส แผนการดูแล วัฒนธรรม ครอบครัว สภาพปัจจุบัน หรือสภาพแวดล้อมของเด็ก "
            "ผู้ใหญ่ที่ดูแลต้องปรับ นำออก หรือหยุดทุกการ์ดตามความจำเป็น"
        ),
        preflight=(
            "สี่ข้อควรตรวจก่อนใช้การ์ด",
            "ยืนยันว่าขั้นตอนปลอดภัยและเหมาะสมในสถานที่และช่วงเวลาปัจจุบัน",
            "รักษาการเข้าถึงอาหาร น้ำ ห้องน้ำ ยา การสื่อสาร การเคลื่อนไหว และความสบาย",
            "ใช้แนวทางการดูแลของผู้เชี่ยวชาญปัจจุบันเมื่อเกี่ยวข้อง การ์ดไม่มีวันแทนที่มัน",
            "หยุด ข้าม หรือเปลี่ยนลำดับเมื่อใดก็ตามที่เด็กหรือครอบครัวต้องการสิ่งที่ต่างออกไป",
        ),
        sources=(
            "บริบทกิจวัตรทางการ ไม่ใช่การรับรอง",
            "CDC อธิบายความสม่ำเสมอและการคาดเดาได้ว่าเป็นส่วนหนึ่งของโครงสร้างครอบครัว และระบุว่าแต่ละครอบครัวตัดสินใจเองว่ากิจวัตรใดเหมาะที่สุด แนวทางนั้นไม่ได้รับรองเครื่องมือนี้หรือรับประกันผลลัพธ์",
            "CDC: การสร้างกิจวัตรที่สม่ำเสมอและโครงสร้างครอบครัว",
        ),
        webmcp=(
            "ตัวอย่าง API เชิงคำสั่ง WebMCP ของ Chrome",
            "สร้างการ์ดกิจวัตรครอบครัวที่ผู้ปกครองตรวจสอบสามถึงหกใบแบบเลือกได้ จากตัวเลือกที่มองเห็นและมีขอบเขตเท่านั้น ไม่รับหรือเข้าถึงชื่อ อายุ ตารางเวลา โรงเรียน ตำแหน่ง ภาพถ่าย บัญชี ข้อความอิสระ พฤติกรรม หรือบันทึกการทำเสร็จของเด็ก ไม่ให้คะแนน วินิจฉัย ติดตาม หรือรับประกันผลลัพธ์",
        ),
        app=(
            "อยากได้เลเยอร์กิจวัตรพ่อแม่–ลูกแบบเลือกได้ที่ใช้ซ้ำได้ไหม?",
            "Lumi Mission Planet เป็นทางเลือก หน้า App Store ปัจจุบันอธิบายภารกิจกิจวัตรพ่อแม่–ลูก แดชบอร์ดสำหรับผู้ปกครอง ข้อมูลบนอุปกรณ์ ไม่มีบัญชีหรือการวิเคราะห์จากบุคคลที่สาม และดาวน์โหลดฟรีพร้อมปลดล็อกครั้งเดียว โปรดดูหน้าปัจจุบันเพื่อความพร้อมและฟีเจอร์ที่แน่นอน การ์ดพิมพ์เหล่านี้ทำงานได้โดยไม่ต้องใช้แอป",
            "ผู้ปกครอง: ดู Lumi Mission Planet บน App Store",
        ),
        faq=(
            "คำถามเกี่ยวกับการ์ดกิจวัตรครอบครัว",
            (
                (
                    "หน้านี้เก็บข้อมูลเกี่ยวกับเด็กไหม?",
                    "ไม่ มันรับเพียงตัวเลือกของครอบครัวที่มีขอบเขต และไม่เคยถามชื่อ อายุ ตารางเวลา โรงเรียน โปรไฟล์ หรือบันทึกกิจกรรม",
                ),
                (
                    "การ์ดเป็นโปรแกรมพฤติกรรมหรือแผนการดูแลไหม?",
                    "ไม่ มันคือคำแนะนำลำดับในบ้านที่นำออกได้ และไม่วินิจฉัย สั่งการ ติดตาม หรือรับประกันผล",
                ),
                (
                    "ถ้าขั้นตอนไม่เหมาะกับวันนี้ทำอย่างไร?",
                    "ผู้ใหญ่ที่ดูแลควรข้าม แทนที่ หรือหยุดมัน ทุกการ์ดเป็นทางเลือก",
                ),
            ),
        ),
        footer="เฉพาะลำดับที่ผู้ปกครองตรวจสอบ · ไม่มีข้อมูลเด็ก · ไม่ติดตาม · ไม่รับประกันผล",
        inline="วางแผนการ์ดกิจวัตรครอบครัวส่วนตัวที่ผู้ปกครองตรวจสอบก่อนเลือกแอป",
        index=(
            "ตัววางแผนการ์ดกิจวัตรครอบครัวแบบส่วนตัว",
            "สร้างลำดับในบ้านที่ข้ามได้โดยไม่กรอกข้อมูลเด็กหรือติดตามการทำเสร็จ",
        ),
    ),
    "id": _copy(
        meta=(
            "Perencana Kartu Rutinitas Keluarga Pribadi | Tanpa Data Anak",
            "Buat urutan tiga hingga enam kartu rutinitas yang ditinjau orang tua tanpa memasukkan nama, usia, jadwal, sekolah, perilaku, atau catatan penyelesaian anak.",
            "Alat gratis",
            "English",
            "Gratis · untuk orang tua · tanpa profil anak",
            "Perencana kartu rutinitas keluarga pribadi",
            "Pilih konteks rumah tangga dan format kartu. Halaman mengembalikan urutan kartu yang dapat dilewati dan dihapus hanya setelah orang dewasa memastikan setiap langkah sesuai.",
        ),
        badges=(
            "Tanpa nama, usia, atau profil anak",
            "Tanpa pelacakan perilaku atau penyelesaian",
            "Tanpa akun, unggahan, atau penyimpanan",
            "Tanpa janji hasil atau kemandirian",
        ),
        planner=(
            "Bangun urutan kartu yang ditinjau orang dewasa",
            "Kartu ini menata langkah rumah tangga; kartu tidak menilai anak, tidak meresepkan perawatan, dan tidak memprediksi perilaku, tidur, kesehatan, belajar, atau hasil keluarga.",
        ),
        labels=(
            "Konteks rutinitas",
            "Jumlah kartu",
            "Penyajian kartu",
            "Isyarat transisi lembut",
        ),
        options=(
            (
                "Pagi",
                "Sepulang sekolah atau penitipan",
                "Beres-beres",
                "Waktu tidur",
            ),
            (
                "Kata",
                "Ikon besar dengan label",
                "Ikon dan kata",
            ),
            (
                "Tampilkan hanya kartu berikutnya",
                "Tampilkan sekarang dan berikutnya",
                "Tawarkan satu pilihan aman yang terbatas",
            ),
        ),
        adult_review=(
            "Saya orang dewasa pengawas dan telah memeriksa langkah terpilih untuk rumah tangga ini",
            "Tinjauan orang dewasa dikonfirmasi. Jaga setiap kartu tetap opsional dan ubah atau hapus apa pun yang tidak sesuai hari ini.",
            "Tinjauan orang dewasa diperlukan sebelum kartu muncul. Periksa keamanan, akses, panduan perawatan, kebutuhan rumah tangga, dan isyarat anak saat ini.",
        ),
        results=(
            "Buat kartu pribadi",
            "Cetak kartu yang ditinjau",
            "Kartu rutinitas opsional",
            "Dapat dilewati, dijeda, atau diganti",
            "Kartu jeda: hentikan urutan dan periksa apa yang dibutuhkan rumah tangga sekarang.",
        ),
        steps=(
            (
                "Gunakan isyarat awal yang tenang seperti biasa di rumah.",
                "Pilih pakaian yang telah disetujui orang dewasa pengawas.",
                "Selesaikan langkah cuci atau perawatan biasa dengan bantuan orang dewasa yang sesuai.",
                "Gunakan langkah sarapan atau minum yang direncanakan keluarga.",
                "Biarkan orang dewasa memeriksa barang yang dibutuhkan hari itu.",
                "Menuju titik siap yang disepakati keluarga bersama orang dewasa pengawas.",
            ),
            (
                "Tiba di titik transisi yang disepakati rumah tangga.",
                "Letakkan barang di tempat yang dipilih orang dewasa pengawas.",
                "Gunakan langkah cuci atau perawatan biasa dengan bantuan yang sesuai.",
                "Ambil jeda makan, minum, atau istirahat yang direncanakan keluarga.",
                "Pilih langkah tenang, gerak, atau kedekatan yang disetujui orang dewasa.",
                "Biarkan orang dewasa mengintip apa yang berikutnya hari ini.",
            ),
            (
                "Biarkan orang dewasa memilih satu area kecil dan aman untuk mulai.",
                "Kembalikan beberapa mainan atau alat aktivitas ke tempat biasanya.",
                "Kembalikan buku atau bahan belajar ke tempat yang disetujui orang dewasa.",
                "Letakkan pakaian atau barang lembut di tempat yang diharapkan rumah tangga.",
                "Biarkan orang dewasa menangani benda tajam, berat, pecah, atau tak pasti.",
                "Berhenti sejenak bersama dan periksa jalur serta barang yang dibutuhkan tetap dapat diakses.",
            ),
            (
                "Gunakan isyarat mulai tidur yang tenang seperti biasa di rumah.",
                "Selesaikan langkah cuci atau kamar mandi biasa dengan bantuan orang dewasa yang sesuai.",
                "Pilih pakaian tidur yang sesuai untuk rumah tangga dan kondisi.",
                "Rawat gigi sesuai panduan keluarga dan profesional saat ini.",
                "Pilih langkah kedekatan tenang, cerita, atau menenangkan yang biasa di keluarga.",
                "Akhiri dengan pengaturan tidur yang disepakati dan orang dewasa pengawas di dekat bila perlu.",
            ),
        ),
        cue_notes=(
            "Tampilkan hanya satu kartu berikutnya; ungkap kartu lain hanya setelah orang dewasa memeriksa situasi saat ini.",
            "Tampilkan kartu saat ini dan berikutnya tanpa memperlakukan keduanya sebagai tenggat.",
            "Tawarkan pilihan hanya bila kedua opsi aman, tersedia, dan dapat diterima orang dewasa pengawas.",
        ),
        boundary=(
            "Perencana tidak pernah tahu usia, perkembangan, disabilitas, kesehatan, kebutuhan sensorik, rencana perawatan, budaya, rumah tangga, kondisi saat ini, atau lingkungan anak. "
            "Orang dewasa pengawas harus menyesuaikan, menghapus, atau menghentikan setiap kartu sesuai kebutuhan."
        ),
        preflight=(
            "Empat pemeriksaan sebelum memakai kartu",
            "Pastikan langkah aman dan sesuai di tempat dan momen saat ini.",
            "Jaga akses ke makanan, air, kamar mandi, obat, komunikasi, mobilitas, dan kenyamanan.",
            "Gunakan panduan perawatan profesional terkini bila berlaku; kartu tak pernah menggantikannya.",
            "Jeda, lewati, atau ubah urutan kapan pun anak atau rumah tangga membutuhkan hal berbeda.",
        ),
        sources=(
            "Konteks rutinitas resmi, bukan dukungan",
            "CDC menjelaskan konsistensi dan keterdugaan sebagai bagian dari struktur rumah tangga dan menyatakan setiap keluarga memutuskan rutinitas mana yang paling cocok. Panduan itu tidak memvalidasi alat ini atau menjamin hasil.",
            "CDC: menciptakan rutinitas konsisten dan struktur rumah tangga",
        ),
        webmcp=(
            "Pratinjau API imperatif WebMCP Chrome",
            "Buat tiga hingga enam kartu rutinitas keluarga opsional yang ditinjau orang tua hanya dari pilihan terlihat yang terbatas. Jangan pernah menerima atau mengakses nama, usia, jadwal, sekolah, lokasi, foto, akun, teks bebas, perilaku, atau catatan penyelesaian anak; jangan pernah menilai, mendiagnosis, memantau, atau menjanjikan hasil.",
        ),
        app=(
            "Ingin lapisan rutinitas orang tua–anak opsional yang dapat dipakai ulang?",
            "Lumi Mission Planet bersifat opsional. Halaman App Store-nya saat ini menjelaskan misi rutinitas orang tua–anak, dasbor orang tua, data di perangkat, tanpa akun atau analitik pihak ketiga, dan unduhan gratis dengan buka kunci sekali bayar. Periksa halaman terkini untuk ketersediaan dan fitur pastinya. Kartu cetak ini bekerja tanpa aplikasi.",
            "Orang tua: lihat Lumi Mission Planet di App Store",
        ),
        faq=(
            "Pertanyaan kartu rutinitas keluarga",
            (
                (
                    "Apakah halaman ini mengumpulkan informasi tentang anak?",
                    "Tidak. Ia hanya menerima pilihan rumah tangga terbatas dan tak pernah meminta nama, usia, jadwal, sekolah, profil, atau catatan aktivitas.",
                ),
                (
                    "Apakah kartu ini program perilaku atau rencana perawatan?",
                    "Tidak. Itu petunjuk urutan rumah tangga yang dapat dihapus dan tidak mendiagnosis, meresepkan, memantau, atau menjanjikan hasil.",
                ),
                (
                    "Bagaimana jika sebuah langkah tidak tepat hari ini?",
                    "Orang dewasa pengawas sebaiknya melewati, mengganti, atau menghentikannya. Setiap kartu bersifat opsional.",
                ),
            ),
        ),
        footer="Hanya urutan yang ditinjau orang tua · tanpa data anak · tanpa pelacakan · tanpa janji hasil",
        inline="Rencanakan kartu rutinitas keluarga pribadi yang ditinjau orang tua sebelum memilih aplikasi",
        index=(
            "Perencana Kartu Rutinitas Keluarga Pribadi",
            "Buat urutan rumah tangga yang dapat dilewati tanpa memasukkan data anak atau melacak penyelesaian.",
        ),
    ),
    "tr": _copy(
        meta=(
            "Özel Aile Rutin Kartı Planlayıcısı | Çocuk Verisi Yok",
            "Bir çocuğun adını, yaşını, programını, okulunu, davranışını veya tamamlama kaydını girmeden ebeveyn onaylı üç ila altı rutin kartından oluşan bir sıra oluşturun.",
            "Ücretsiz araçlar",
            "English",
            "Ücretsiz · ebeveyne yönelik · çocuk profili yok",
            "Özel aile rutin kartı planlayıcısı",
            "Bir ev bağlamı ve kart biçimi seçin. Sayfa, yalnızca bir yetişkin her adımın uygun olduğunu onayladıktan sonra kaldırılabilir ve atlanabilir bir kart sırası döndürür.",
        ),
        badges=(
            "Ad, yaş veya çocuk profili yok",
            "Davranış veya tamamlama takibi yok",
            "Hesap, yükleme veya depolama yok",
            "Sonuç veya bağımsızlık vaadi yok",
        ),
        planner=(
            "Yetişkin onaylı bir kart sırası oluştur",
            "Bu kartlar ev adımlarını düzenler; bir çocuğu değerlendirmez, bakım reçete etmez ve davranış, uyku, sağlık, öğrenme veya aile sonuçlarını tahmin etmez.",
        ),
        labels=(
            "Rutin bağlamı",
            "Kart sayısı",
            "Kart sunumu",
            "Nazik geçiş ipucu",
        ),
        options=(
            (
                "Sabah",
                "Okuldan veya bakımdan sonra",
                "Toparlanma",
                "Yatma zamanı",
            ),
            (
                "Kelimeler",
                "Etiketli büyük simgeler",
                "Simgeler ve kelimeler",
            ),
            (
                "Yalnızca sonraki kartı göster",
                "Şimdiyi ve sonrakini göster",
                "Güvenli ve sınırlı bir seçenek sun",
            ),
        ),
        adult_review=(
            "Gözeten yetişkin benim ve bu ev için seçilen adımları kontrol ettim",
            "Yetişkin incelemesi onaylandı. Her kartı isteğe bağlı tutun ve bugün uygun olmayan her şeyi değiştirin veya kaldırın.",
            "Kartlar görünmeden önce yetişkin incelemesi gerekir. Güvenliği, erişimi, bakım rehberliğini, ev ihtiyaçlarını ve çocuğun mevcut ipuçlarını kontrol edin.",
        ),
        results=(
            "Özel kartlar oluştur",
            "İncelenen kartları yazdır",
            "İsteğe bağlı rutin kartı",
            "Atlanabilir, duraklatılabilir veya değiştirilebilir",
            "Duraklat kartı: sırayı durdurun ve evin şimdi neye ihtiyacı olduğunu kontrol edin.",
        ),
        steps=(
            (
                "Evin her zamanki sakin başlangıç ipucunu kullanın.",
                "Gözeten yetişkinin onayladığı kıyafeti seçin.",
                "Uygun yetişkin yardımıyla evin her zamanki yıkanma veya bakım adımını tamamlayın.",
                "Ailenin planladığı kahvaltı veya içecek adımını kullanın.",
                "Yetişkinin gün için gereken eşyaları kontrol etmesine izin verin.",
                "Gözeten yetişkinle ailenin kararlaştırdığı hazır noktasına geçin.",
            ),
            (
                "Evin kararlaştırdığı geçiş noktasına varın.",
                "Eşyaları gözeten yetişkinin seçtiği yere koyun.",
                "Uygun yardımla evin her zamanki yıkanma veya bakım adımını kullanın.",
                "Ailenin planladığı yemek, içecek veya dinlenme molasını alın.",
                "Yetişkinin onayladığı sakin, hareket veya bağ kurma adımını seçin.",
                "Yetişkinin bugün sırada ne olduğuna göz atmasına izin verin.",
            ),
            (
                "Yetişkinin başlamak için küçük ve güvenli bir alan seçmesine izin verin.",
                "Birkaç oyuncağı veya etkinlik eşyasını her zamanki yerine koyun.",
                "Kitapları veya öğrenme malzemelerini yetişkinin onayladığı yere koyun.",
                "Kıyafet veya yumuşak eşyaları evin beklediği yere koyun.",
                "Keskin, ağır, kırık veya belirsiz eşyaları yetişkinin ele almasına izin verin.",
                "Birlikte durun ve yolların ve gereken eşyaların erişilebilir kaldığını kontrol edin.",
            ),
            (
                "Evin her zamanki sakin yatma başlangıç ipucunu kullanın.",
                "Uygun yetişkin yardımıyla her zamanki yıkanma veya tuvalet adımını tamamlayın.",
                "Ev ve koşullar için onaylanmış uyku kıyafetini seçin.",
                "Diş bakımını mevcut aile ve profesyonel rehberliğe göre tamamlayın.",
                "Ailenin her zamanki sakin bağ kurma, hikâye veya yatıştırma adımını seçin.",
                "Evin kararlaştırdığı uyku düzeniyle ve gerektiğinde yakında gözeten bir yetişkinle bitirin.",
            ),
        ),
        cue_notes=(
            "Yalnızca bir sonraki kartı görünür tutun; başka bir kartı ancak yetişkin mevcut durumu kontrol ettikten sonra gösterin.",
            "Mevcut ve sonraki kartı ikisini de son tarih gibi görmeden gösterin.",
            "Yalnızca her iki seçenek güvenli, mevcut ve gözeten yetişkin için kabul edilebilir olduğunda seçenek sunun.",
        ),
        boundary=(
            "Planlayıcı çocuğun yaşını, gelişimini, engelini, sağlığını, duyusal ihtiyaçlarını, bakım planını, kültürünü, evini, mevcut durumunu veya ortamını asla bilmez. "
            "Gözeten yetişkin her kartı gerektiğinde uyarlamalı, kaldırmalı veya durdurmalıdır."
        ),
        preflight=(
            "Bir kartı kullanmadan önce dört kontrol",
            "Adımın mevcut yer ve anda güvenli ve uygun olduğunu doğrulayın.",
            "Yiyecek, su, tuvalet, ilaç, iletişim, hareket ve rahatlığa erişimi koruyun.",
            "Geçerli olduğunda güncel profesyonel bakım rehberliğini kullanın; bir kart onu asla geçersiz kılmaz.",
            "Çocuk veya ev farklı bir şeye ihtiyaç duyduğunda sırayı duraklatın, atlayın veya değiştirin.",
        ),
        sources=(
            "Resmi rutin bağlamı, bir onay değil",
            "CDC, tutarlılık ve öngörülebilirliği ev yapısının parçaları olarak tanımlar ve hangi rutinlerin en iyi işlediğine ailelerin karar verdiğini söyler. Bu rehberlik bu aracı doğrulamaz veya bir sonucu garanti etmez.",
            "CDC: tutarlı rutinler ve ev yapısı oluşturmak",
        ),
        webmcp=(
            "Chrome zorunlu WebMCP API önizlemesi",
            "Yalnızca sınırlı görünür seçeneklerden üç ila altı isteğe bağlı ebeveyn onaylı aile rutin kartı oluşturun. Çocuğun adını, yaşını, programını, okulunu, konumunu, fotoğraflarını, hesaplarını, serbest metnini, davranışını veya tamamlama kayıtlarını asla almayın veya bunlara erişmeyin; asla puanlamayın, teşhis koymayın, izlemeyin veya bir sonuç vaat etmeyin.",
        ),
        app=(
            "İsteğe bağlı, yeniden kullanılabilir bir ebeveyn–çocuk rutin katmanı ister misiniz?",
            "Lumi Mission Planet isteğe bağlıdır. Mevcut App Store sayfası ebeveyn–çocuk rutin görevlerini, bir ebeveyn panosunu, cihazdaki verileri, hesap veya üçüncü taraf analitiği olmadığını ve tek seferlik kilit açmalı ücretsiz indirmeyi tanımlar. Kesin kullanılabilirlik ve özellikler için güncel sayfaya bakın. Bu yazdırılabilir kartlar uygulama olmadan çalışır.",
            "Ebeveynler: Lumi Mission Planet'i App Store'da görüntüleyin",
        ),
        faq=(
            "Aile rutin kartı soruları",
            (
                (
                    "Bu sayfa bir çocuk hakkında bilgi topluyor mu?",
                    "Hayır. Yalnızca sınırlı ev seçimlerini kabul eder ve asla ad, yaş, program, okul, profil veya etkinlik kaydı istemez.",
                ),
                (
                    "Kartlar bir davranış programı veya bakım planı mı?",
                    "Hayır. Bunlar kaldırılabilir ev sıra ipuçlarıdır ve teşhis koymaz, reçete etmez, izlemez veya sonuç vaat etmez.",
                ),
                (
                    "Bir adım bugün doğru değilse ne olur?",
                    "Gözeten yetişkin onu atlamalı, değiştirmeli veya durdurmalıdır. Her kart isteğe bağlıdır.",
                ),
            ),
        ),
        footer="Yalnızca ebeveyn onaylı sıra · çocuk verisi yok · takip yok · sonuç vaadi yok",
        inline="Bir uygulama seçmeden önce özel, ebeveyn onaylı aile rutin kartları planlayın",
        index=(
            "Özel Aile Rutin Kartı Planlayıcısı",
            "Çocuk verisi girmeden veya tamamlamayı izlemeden atlanabilir bir ev sırası oluşturun.",
        ),
    ),
    "hi": _copy(
        meta=(
            "निजी पारिवारिक दिनचर्या कार्ड योजनाकार | बच्चों का डेटा नहीं",
            "बच्चे का नाम, उम्र, समय-सारणी, स्कूल, व्यवहार या पूर्णता रिकॉर्ड दर्ज किए बिना अभिभावक-स्वीकृत तीन से छह दिनचर्या कार्डों का क्रम बनाएँ।",
            "मुफ़्त उपकरण",
            "English",
            "मुफ़्त · अभिभावकों के लिए · कोई बाल-प्रोफ़ाइल नहीं",
            "निजी पारिवारिक दिनचर्या कार्ड योजनाकार",
            "एक घरेलू संदर्भ और कार्ड प्रारूप चुनें। पृष्ठ तभी हटाने-योग्य और छोड़ने-योग्य कार्ड क्रम देता है जब एक वयस्क पुष्टि कर दे कि हर चरण उपयुक्त है।",
        ),
        badges=(
            "कोई नाम, उम्र या बाल-प्रोफ़ाइल नहीं",
            "कोई व्यवहार या पूर्णता ट्रैकिंग नहीं",
            "कोई खाता, अपलोड या संग्रहण नहीं",
            "कोई परिणाम या स्वतंत्रता वादा नहीं",
        ),
        planner=(
            "वयस्क-स्वीकृत कार्ड क्रम बनाएँ",
            "ये कार्ड घरेलू चरणों को व्यवस्थित करते हैं; वे किसी बच्चे का मूल्यांकन नहीं करते, देखभाल निर्धारित नहीं करते और व्यवहार, नींद, स्वास्थ्य, सीखने या पारिवारिक परिणामों का अनुमान नहीं लगाते।",
        ),
        labels=(
            "दिनचर्या संदर्भ",
            "कार्ड संख्या",
            "कार्ड प्रस्तुति",
            "सौम्य संक्रमण संकेत",
        ),
        options=(
            (
                "सुबह",
                "स्कूल या देखभाल के बाद",
                "समेटना",
                "सोने का समय",
            ),
            (
                "शब्द",
                "लेबल वाले बड़े चिह्न",
                "चिह्न और शब्द",
            ),
            (
                "केवल अगला कार्ड दिखाएँ",
                "अभी और अगला दोनों दिखाएँ",
                "एक सुरक्षित, सीमित विकल्प दें",
            ),
        ),
        adult_review=(
            "देखरेख करने वाला वयस्क मैं हूँ और मैंने इस घर के लिए चुने गए चरण जाँच लिए हैं",
            "वयस्क समीक्षा पुष्ट। हर कार्ड को वैकल्पिक रखें और जो भी आज उपयुक्त न हो उसे बदलें या हटा दें।",
            "कार्ड दिखने से पहले वयस्क समीक्षा आवश्यक है। सुरक्षा, पहुँच, देखभाल मार्गदर्शन, घर की ज़रूरतें और बच्चे के वर्तमान संकेत जाँचें।",
        ),
        results=(
            "निजी कार्ड बनाएँ",
            "समीक्षित कार्ड प्रिंट करें",
            "वैकल्पिक दिनचर्या कार्ड",
            "छोड़ा, रोका या बदला जा सकता है",
            "विराम कार्ड: क्रम रोकें और देखें कि घर को अभी क्या चाहिए।",
        ),
        steps=(
            (
                "घर का सामान्य शांत आरंभ-संकेत उपयोग करें।",
                "देखरेख करने वाले वयस्क द्वारा स्वीकृत कपड़े चुनें।",
                "उचित वयस्क सहायता से घर का सामान्य धुलाई या देखभाल चरण पूरा करें।",
                "परिवार द्वारा नियोजित नाश्ता या पेय चरण उपयोग करें।",
                "वयस्क को दिन के लिए ज़रूरी सामान जाँचने दें।",
                "देखरेख करने वाले वयस्क के साथ परिवार के तय तैयार-बिंदु पर पहुँचें।",
            ),
            (
                "घर के तय संक्रमण-बिंदु पर पहुँचें।",
                "सामान वहीं रखें जहाँ देखरेख करने वाले वयस्क ने चुना है।",
                "उचित सहायता से घर का सामान्य धुलाई या देखभाल चरण उपयोग करें।",
                "परिवार द्वारा नियोजित भोजन, पेय या विश्राम लें।",
                "वयस्क-स्वीकृत शांत, गतिविधि या जुड़ाव चरण चुनें।",
                "वयस्क को देखने दें कि आज आगे क्या है।",
            ),
            (
                "वयस्क को शुरू करने के लिए छोटा और सुरक्षित क्षेत्र चुनने दें।",
                "कुछ खिलौने या गतिविधि-सामान उनकी सामान्य जगह पर रखें।",
                "किताबें या सीखने की सामग्री वयस्क-स्वीकृत स्थान पर रखें।",
                "कपड़े या मुलायम चीज़ें वहाँ रखें जहाँ घर अपेक्षा करता है।",
                "नुकीली, भारी, टूटी या अस्पष्ट चीज़ें वयस्क को सँभालने दें।",
                "साथ रुककर जाँचें कि रास्ते और ज़रूरी सामान पहुँच में हैं।",
            ),
            (
                "घर का सामान्य शांत सोने का आरंभ-संकेत उपयोग करें।",
                "उचित वयस्क सहायता से सामान्य धुलाई या शौचालय चरण पूरा करें।",
                "घर और परिस्थितियों के लिए स्वीकृत सोने के कपड़े चुनें।",
                "मौजूदा पारिवारिक और पेशेवर मार्गदर्शन के अनुसार दंत देखभाल पूरी करें।",
                "परिवार का सामान्य शांत जुड़ाव, कहानी या सुकून चरण चुनें।",
                "घर की तय नींद-व्यवस्था के साथ समाप्त करें और आवश्यकता होने पर देखरेख करने वाला वयस्क पास रहे।",
            ),
        ),
        cue_notes=(
            "केवल अगला कार्ड दिखाई देता रखें; कोई और कार्ड तभी दिखाएँ जब वयस्क वर्तमान स्थिति जाँच ले।",
            "वर्तमान और अगला कार्ड दोनों दिखाएँ, पर किसी को भी समय-सीमा की तरह न लें।",
            "विकल्प केवल तभी दें जब दोनों विकल्प सुरक्षित, उपलब्ध और देखरेख करने वाले वयस्क को स्वीकार्य हों।",
        ),
        boundary=(
            "योजनाकार बच्चे की उम्र, विकास, विकलांगता, स्वास्थ्य, संवेदी ज़रूरतें, देखभाल योजना, संस्कृति, घर, वर्तमान स्थिति या परिवेश कभी नहीं जानता। "
            "देखरेख करने वाले वयस्क को हर कार्ड आवश्यकतानुसार अनुकूलित करना, हटाना या रोकना चाहिए।"
        ),
        preflight=(
            "कार्ड उपयोग से पहले चार जाँचें",
            "पुष्टि करें कि चरण वर्तमान स्थान और क्षण में सुरक्षित और उपयुक्त है।",
            "भोजन, पानी, शौचालय, दवा, संवाद, गतिविधि और आराम तक पहुँच बनाए रखें।",
            "लागू होने पर वर्तमान पेशेवर देखभाल मार्गदर्शन का पालन करें; कोई कार्ड उसे कभी नहीं बदलता।",
            "जब बच्चे या घर को कुछ अलग चाहिए हो तो क्रम रोकें, छोड़ें या बदलें।",
        ),
        sources=(
            "आधिकारिक दिनचर्या संदर्भ, कोई समर्थन नहीं",
            "CDC निरंतरता और पूर्वानुमेयता को घरेलू संरचना के हिस्से बताता है और कहता है कि कौन-सी दिनचर्या सबसे अच्छी चलती है, यह परिवार तय करते हैं। यह मार्गदर्शन इस उपकरण को प्रमाणित नहीं करता और न किसी परिणाम की गारंटी देता है।",
            "CDC: सुसंगत दिनचर्याएँ और घरेलू संरचना बनाना",
        ),
        webmcp=(
            "Chrome अनिवार्य WebMCP API पूर्वावलोकन",
            "केवल सीमित दृश्य विकल्पों से तीन से छह वैकल्पिक अभिभावक-स्वीकृत पारिवारिक दिनचर्या कार्ड बनाएँ। बच्चे का नाम, उम्र, समय-सारणी, स्कूल, स्थान, फ़ोटो, खाते, मुक्त टेक्स्ट, व्यवहार या पूर्णता रिकॉर्ड कभी न लें और न उन तक पहुँचें; कभी स्कोर, निदान, निगरानी या परिणाम का वादा न करें।",
        ),
        app=(
            "एक वैकल्पिक, पुन:प्रयोज्य अभिभावक–बच्चा दिनचर्या परत चाहिए?",
            "Lumi Mission Planet वैकल्पिक है। वर्तमान App Store पृष्ठ अभिभावक–बच्चा दिनचर्या मिशनों, अभिभावक डैशबोर्ड, ऑन-डिवाइस डेटा, बिना खाते या तृतीय-पक्ष विश्लेषण और एक-बार अनलॉक वाले मुफ़्त डाउनलोड का वर्णन करता है। सटीक उपलब्धता और विशेषताओं के लिए वर्तमान पृष्ठ देखें। ये प्रिंट-योग्य कार्ड ऐप के बिना भी काम करते हैं।",
            "अभिभावक: App Store पर Lumi Mission Planet देखें",
        ),
        faq=(
            "पारिवारिक दिनचर्या कार्ड प्रश्न",
            (
                (
                    "क्या यह पृष्ठ बच्चे के बारे में जानकारी एकत्र करता है?",
                    "नहीं। यह केवल सीमित घरेलू विकल्प लेता है और कभी नाम, उम्र, समय-सारणी, स्कूल, प्रोफ़ाइल या गतिविधि रिकॉर्ड नहीं माँगता।",
                ),
                (
                    "क्या कार्ड कोई व्यवहार कार्यक्रम या देखभाल योजना हैं?",
                    "नहीं। ये हटाने-योग्य घरेलू क्रम-संकेत हैं और ये निदान, निर्धारण, निगरानी या परिणाम का वादा नहीं करते।",
                ),
                (
                    "यदि कोई चरण आज उपयुक्त न हो तो?",
                    "देखरेख करने वाला वयस्क उसे छोड़े, बदले या रोके। हर कार्ड वैकल्पिक है।",
                ),
            ),
        ),
        footer="केवल अभिभावक-स्वीकृत क्रम · कोई बाल-डेटा नहीं · कोई ट्रैकिंग नहीं · कोई परिणाम वादा नहीं",
        inline="कोई ऐप चुनने से पहले निजी, अभिभावक-स्वीकृत पारिवारिक दिनचर्या कार्ड योजना बनाएँ",
        index=(
            "निजी पारिवारिक दिनचर्या कार्ड योजनाकार",
            "बाल-डेटा दर्ज किए या पूर्णता ट्रैक किए बिना छोड़ने-योग्य घरेलू क्रम बनाएँ।",
        ),
    ),
    "ms": _copy(
        meta=(
            "Perancang Kad Rutin Keluarga Peribadi | Tiada Data Kanak-kanak",
            "Bina urutan tiga hingga enam kad rutin yang diluluskan ibu bapa tanpa memasukkan nama, umur, jadual, sekolah, tingkah laku atau rekod penyiapan kanak-kanak.",
            "Alat percuma",
            "English",
            "Percuma · untuk ibu bapa · tiada profil kanak-kanak",
            "Perancang kad rutin keluarga peribadi",
            "Pilih konteks rumah dan format kad. Halaman ini hanya memulangkan urutan kad yang boleh dibuang dan dilangkau selepas orang dewasa mengesahkan setiap langkah sesuai.",
        ),
        badges=(
            "Tiada nama, umur atau profil kanak-kanak",
            "Tiada penjejakan tingkah laku atau penyiapan",
            "Tiada akaun, muat naik atau storan",
            "Tiada janji hasil atau kebebasan",
        ),
        planner=(
            "Bina urutan kad yang diluluskan orang dewasa",
            "Kad ini menyusun langkah rumah; ia tidak menilai kanak-kanak, tidak menetapkan penjagaan dan tidak meramalkan tingkah laku, tidur, kesihatan, pembelajaran atau hasil keluarga.",
        ),
        labels=(
            "Konteks rutin",
            "Bilangan kad",
            "Persembahan kad",
            "Isyarat peralihan lembut",
        ),
        options=(
            (
                "Pagi",
                "Selepas sekolah atau jagaan",
                "Mengemas",
                "Waktu tidur",
            ),
            (
                "Perkataan",
                "Ikon besar berlabel",
                "Ikon dan perkataan",
            ),
            (
                "Tunjuk kad seterusnya sahaja",
                "Tunjuk sekarang dan seterusnya",
                "Beri satu pilihan selamat dan terhad",
            ),
        ),
        adult_review=(
            "Saya orang dewasa yang menyelia dan telah menyemak langkah yang dipilih untuk rumah ini",
            "Semakan dewasa disahkan. Kekalkan setiap kad sebagai pilihan dan ubah atau buang apa-apa yang tidak sesuai hari ini.",
            "Semakan dewasa diperlukan sebelum kad dipaparkan. Semak keselamatan, akses, panduan penjagaan, keperluan rumah dan isyarat semasa kanak-kanak.",
        ),
        results=(
            "Bina kad peribadi",
            "Cetak kad yang disemak",
            "Kad rutin pilihan",
            "Boleh dilangkau, dijeda atau diubah",
            "Kad jeda: hentikan urutan dan semak apa yang rumah perlukan sekarang.",
        ),
        steps=(
            (
                "Guna isyarat mula tenang seperti biasa di rumah.",
                "Pilih pakaian yang diluluskan orang dewasa yang menyelia.",
                "Selesaikan langkah mandi atau penjagaan biasa dengan bantuan dewasa yang sesuai.",
                "Guna langkah sarapan atau minuman yang dirancang keluarga.",
                "Biarkan orang dewasa menyemak barang yang diperlukan untuk hari itu.",
                "Bergerak ke titik sedia yang dipersetujui keluarga bersama orang dewasa yang menyelia.",
            ),
            (
                "Tiba di titik peralihan yang dipersetujui rumah.",
                "Letakkan barang di tempat yang dipilih orang dewasa yang menyelia.",
                "Guna langkah mandi atau penjagaan biasa dengan bantuan yang sesuai.",
                "Ambil makanan, minuman atau rehat yang dirancang keluarga.",
                "Pilih langkah tenang, pergerakan atau ikatan yang diluluskan orang dewasa.",
                "Biarkan orang dewasa melihat apa yang seterusnya hari ini.",
            ),
            (
                "Biarkan orang dewasa memilih kawasan kecil dan selamat untuk bermula.",
                "Letakkan beberapa mainan atau barang aktiviti di tempat biasanya.",
                "Letakkan buku atau bahan pembelajaran di tempat yang diluluskan orang dewasa.",
                "Letakkan pakaian atau barang lembut di tempat yang dijangka rumah.",
                "Biarkan orang dewasa mengendalikan barang tajam, berat, pecah atau tidak pasti.",
                "Berhenti bersama dan semak laluan serta barang penting kekal boleh dicapai.",
            ),
            (
                "Guna isyarat mula tidur tenang seperti biasa di rumah.",
                "Selesaikan langkah mandi atau tandas biasa dengan bantuan dewasa yang sesuai.",
                "Pilih pakaian tidur yang diluluskan untuk rumah dan keadaan.",
                "Selesaikan penjagaan gigi mengikut panduan keluarga dan profesional semasa.",
                "Pilih langkah ikatan, cerita atau penenangan tenang seperti biasa keluarga.",
                "Akhiri dengan susunan tidur yang dipersetujui rumah dan orang dewasa yang menyelia berdekatan jika perlu.",
            ),
        ),
        cue_notes=(
            "Kekalkan hanya kad seterusnya kelihatan; tunjukkan kad lain hanya selepas orang dewasa menyemak keadaan semasa.",
            "Tunjukkan kad semasa dan seterusnya tanpa menganggap kedua-duanya sebagai tarikh akhir.",
            "Beri pilihan hanya apabila kedua-dua pilihan selamat, tersedia dan boleh diterima oleh orang dewasa yang menyelia.",
        ),
        boundary=(
            "Perancang ini tidak pernah mengetahui umur, perkembangan, ketidakupayaan, kesihatan, keperluan deria, pelan penjagaan, budaya, rumah, keadaan semasa atau persekitaran kanak-kanak. "
            "Orang dewasa yang menyelia mesti menyesuaikan, membuang atau menghentikan setiap kad mengikut keperluan."
        ),
        preflight=(
            "Empat semakan sebelum menggunakan kad",
            "Sahkan langkah itu selamat dan sesuai di tempat dan waktu semasa.",
            "Kekalkan akses kepada makanan, air, tandas, ubat, komunikasi, pergerakan dan keselesaan.",
            "Ikut panduan penjagaan profesional semasa apabila berkenaan; kad tidak sekali-kali mengatasinya.",
            "Jeda, langkau atau ubah urutan apabila kanak-kanak atau rumah memerlukan sesuatu yang berbeza.",
        ),
        sources=(
            "Konteks rutin rasmi, bukan sokongan",
            "CDC menerangkan konsistensi dan kebolehramalan sebagai sebahagian struktur rumah dan menyatakan keluarga yang menentukan rutin mana paling berkesan. Panduan ini tidak mengesahkan alat ini atau menjamin sebarang hasil.",
            "CDC: membina rutin konsisten dan struktur rumah",
        ),
        webmcp=(
            "Pratonton API imperatif WebMCP Chrome",
            "Bina tiga hingga enam kad rutin keluarga pilihan yang diluluskan ibu bapa daripada pilihan kelihatan yang terhad sahaja. Jangan sekali-kali mengambil atau mengakses nama, umur, jadual, sekolah, lokasi, foto, akaun, teks bebas, tingkah laku atau rekod penyiapan kanak-kanak; jangan sekali-kali menskor, mendiagnosis, memantau atau menjanjikan hasil.",
        ),
        app=(
            "Mahukan lapisan rutin ibu bapa–anak yang boleh diguna semula?",
            "Lumi Mission Planet adalah pilihan. Halaman App Store semasa menerangkan misi rutin ibu bapa–anak, papan pemuka ibu bapa, data pada peranti, tiada akaun atau analitik pihak ketiga, dan muat turun percuma dengan buka kunci sekali. Rujuk halaman semasa untuk ketersediaan dan ciri tepat. Kad boleh cetak ini berfungsi tanpa aplikasi.",
            "Ibu bapa: lihat Lumi Mission Planet di App Store",
        ),
        faq=(
            "Soalan kad rutin keluarga",
            (
                (
                    "Adakah halaman ini mengumpul maklumat tentang kanak-kanak?",
                    "Tidak. Ia hanya menerima pilihan rumah yang terhad dan tidak sekali-kali meminta nama, umur, jadual, sekolah, profil atau rekod aktiviti.",
                ),
                (
                    "Adakah kad ini program tingkah laku atau pelan penjagaan?",
                    "Tidak. Ia isyarat urutan rumah yang boleh dibuang dan tidak mendiagnosis, menetapkan, memantau atau menjanjikan hasil.",
                ),
                (
                    "Bagaimana jika sesuatu langkah tidak sesuai hari ini?",
                    "Orang dewasa yang menyelia harus melangkau, mengubah atau menghentikannya. Setiap kad adalah pilihan.",
                ),
            ),
        ),
        footer="Urutan yang diluluskan ibu bapa sahaja · tiada data kanak-kanak · tiada penjejakan · tiada janji hasil",
        inline="Rancang kad rutin keluarga peribadi yang diluluskan ibu bapa sebelum memilih aplikasi",
        index=(
            "Perancang Kad Rutin Keluarga Peribadi",
            "Bina urutan rumah yang boleh dilangkau tanpa memasukkan data kanak-kanak atau menjejak penyiapan.",
        ),
    ),
    "ru": _copy(
        meta=(
            "Приватный планировщик карточек семейных рутин | Без данных ребёнка",
            "Составьте последовательность из трёх–шести одобренных родителем карточек рутин, не вводя имя ребёнка, возраст, расписание, школу, поведение или записи о выполнении.",
            "Бесплатные инструменты",
            "English",
            "Бесплатно · для родителей · без профиля ребёнка",
            "Приватный планировщик карточек семейных рутин",
            "Выберите домашний контекст и формат карточек. Страница возвращает удаляемую и пропускаемую последовательность карточек только после того, как взрослый подтвердит уместность каждого шага.",
        ),
        badges=(
            "Без имени, возраста и профиля ребёнка",
            "Без отслеживания поведения и выполнения",
            "Без аккаунтов, загрузок и хранения",
            "Без обещаний результата или самостоятельности",
        ),
        planner=(
            "Составить одобренную взрослым последовательность карточек",
            "Эти карточки упорядочивают домашние шаги; они не оценивают ребёнка, не назначают уход и не предсказывают поведение, сон, здоровье, обучение или семейные результаты.",
        ),
        labels=(
            "Контекст рутины",
            "Число карточек",
            "Вид карточек",
            "Мягкая подсказка перехода",
        ),
        options=(
            (
                "Утро",
                "После школы или сада",
                "Уборка",
                "Перед сном",
            ),
            (
                "Слова",
                "Крупные значки с подписями",
                "Значки и слова",
            ),
            (
                "Показывать только следующую карточку",
                "Показывать текущую и следующую",
                "Дать безопасный ограниченный выбор",
            ),
        ),
        adult_review=(
            "Я — присматривающий взрослый и проверил(а) выбранные для этого дома шаги",
            "Проверка взрослым подтверждена. Держите каждую карточку необязательной и меняйте или убирайте всё, что сегодня не подходит.",
            "Перед показом карточек нужна проверка взрослым. Проверьте безопасность, доступ, рекомендации по уходу, нужды дома и текущие сигналы ребёнка.",
        ),
        results=(
            "Создать приватные карточки",
            "Распечатать проверенные карточки",
            "Необязательная карточка рутины",
            "Можно пропустить, поставить на паузу или изменить",
            "Карточка паузы: остановите последовательность и посмотрите, что дому нужно сейчас.",
        ),
        steps=(
            (
                "Используйте привычный спокойный стартовый сигнал дома.",
                "Выберите одежду, одобренную присматривающим взрослым.",
                "Выполните привычное умывание или уход с уместной помощью взрослого.",
                "Используйте запланированный семьёй шаг завтрака или напитка.",
                "Пусть взрослый проверит вещи, нужные на день.",
                "Перейдите к согласованной семьёй точке готовности вместе с присматривающим взрослым.",
            ),
            (
                "Придите к согласованной домом точке перехода.",
                "Положите вещи туда, куда выбрал присматривающий взрослый.",
                "Используйте привычное умывание или уход с уместной помощью.",
                "Сделайте запланированный семьёй перерыв на еду, питьё или отдых.",
                "Выберите одобренный взрослым шаг покоя, движения или близости.",
                "Пусть взрослый посмотрит, что сегодня дальше.",
            ),
            (
                "Пусть взрослый выберет маленькую безопасную зону для начала.",
                "Положите несколько игрушек или вещей для занятий на их обычное место.",
                "Уберите книги или учебные материалы в одобренное взрослым место.",
                "Положите одежду или мягкие вещи туда, где их ждёт дом.",
                "Острые, тяжёлые, сломанные или непонятные вещи пусть возьмёт взрослый.",
                "Остановитесь вместе и проверьте, что проходы и нужные вещи доступны.",
            ),
            (
                "Используйте привычный спокойный сигнал начала сна.",
                "Выполните привычное умывание или туалет с уместной помощью взрослого.",
                "Выберите одобренную для дома и условий одежду для сна.",
                "Выполните уход за зубами по текущим семейным и профессиональным рекомендациям.",
                "Выберите привычный спокойный шаг близости, истории или убаюкивания.",
                "Завершите согласованным домом порядком сна, при необходимости с присматривающим взрослым рядом.",
            ),
        ),
        cue_notes=(
            "Держите видимой только следующую карточку; показывайте другую лишь после того, как взрослый проверит текущую ситуацию.",
            "Показывайте текущую и следующую карточки, не превращая ни одну из них в дедлайн.",
            "Давайте выбор только тогда, когда оба варианта безопасны, доступны и приемлемы для присматривающего взрослого.",
        ),
        boundary=(
            "Планировщик никогда не знает возраст ребёнка, развитие, инвалидность, здоровье, сенсорные потребности, план ухода, культуру, дом, текущее состояние или окружение. "
            "Присматривающий взрослый должен адаптировать, убирать или останавливать каждую карточку по мере необходимости."
        ),
        preflight=(
            "Четыре проверки перед использованием карточки",
            "Убедитесь, что шаг безопасен и уместен в текущем месте и моменте.",
            "Сохраняйте доступ к еде, воде, туалету, лекарствам, общению, движению и комфорту.",
            "Следуйте актуальным профессиональным рекомендациям по уходу, где они применимы; карточка никогда их не отменяет.",
            "Ставьте на паузу, пропускайте или меняйте последовательность, когда ребёнку или дому нужно другое.",
        ),
        sources=(
            "Официальный контекст рутин, а не одобрение",
            "CDC описывает последовательность и предсказуемость как части домашней структуры и отмечает, что именно семьи решают, какие рутины работают лучше. Эти рекомендации не подтверждают этот инструмент и не гарантируют результат.",
            "CDC: построение стабильных рутин и домашней структуры",
        ),
        webmcp=(
            "Предварительная версия императивного API WebMCP в Chrome",
            "Составьте три–шесть необязательных одобренных родителем карточек семейных рутин только из ограниченных видимых вариантов. Никогда не принимайте и не запрашивайте имя ребёнка, возраст, расписание, школу, местоположение, фото, аккаунты, свободный текст, поведение или записи о выполнении; никогда не оценивайте, не диагностируйте, не отслеживайте и не обещайте результат.",
        ),
        app=(
            "Нужен необязательный многоразовый слой рутин «родитель–ребёнок»?",
            "Lumi Mission Planet — по желанию. Текущая страница App Store описывает миссии рутин «родитель–ребёнок», родительскую панель, данные на устройстве, отсутствие аккаунтов и сторонней аналитики, бесплатную загрузку с разовой разблокировкой. Точную доступность и функции смотрите на актуальной странице. Эти печатные карточки работают и без приложения.",
            "Родителям: открыть Lumi Mission Planet в App Store",
        ),
        faq=(
            "Вопросы о карточках семейных рутин",
            (
                (
                    "Собирает ли эта страница сведения о ребёнке?",
                    "Нет. Она принимает только ограниченные домашние выборы и никогда не запрашивает имя, возраст, расписание, школу, профиль или записи активности.",
                ),
                (
                    "Это поведенческая программа или план ухода?",
                    "Нет. Это удаляемые домашние подсказки порядка; они не диагностируют, не назначают, не отслеживают и не обещают результат.",
                ),
                (
                    "Что делать, если шаг сегодня не подходит?",
                    "Присматривающий взрослый должен пропустить, изменить или остановить его. Каждая карточка необязательна.",
                ),
            ),
        ),
        footer="Только одобренная родителем последовательность · без данных ребёнка · без отслеживания · без обещаний результата",
        inline="Спланируйте приватные, одобренные родителем карточки семейных рутин, прежде чем выбирать приложение",
        index=(
            "Приватный планировщик карточек семейных рутин",
            "Составьте пропускаемую домашнюю последовательность без ввода данных ребёнка и отслеживания выполнения.",
        ),
    ),
}


STYLE = r"""
:root{--ink:#253047;--muted:#697287;--line:#e4e0d9;--paper:#fffdf8;--bg:#f6f2ea;--navy:#263651;--sky:#dceef7;--mint:#dff1e7;--coral:#ef816c;--gold:#f4c96b;--shadow:0 22px 60px rgba(39,54,81,.13)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 85% 0,#fff9df 0,var(--bg) 48%,#e7eef2 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#325f7d}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#263651f5;color:#fff;box-shadow:0 9px 28px rgba(26,40,62,.18)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{color:#fff;text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px;text-align:center}.eyebrow,.badge{display:inline-flex;border:1px solid #d8e1e5;background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--navy);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,253,248,.98);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--navy);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,button{font:inherit}select{width:100%;min-height:46px;border:1px solid #cfd7d9;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid #d9c9b6;border-radius:14px;padding:11px 13px;background:#fff8e8;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--navy),#467694);color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(38,54,81,.22)}.button.secondary{background:#fff;color:var(--navy);border:1px solid #bdcbd3;box-shadow:none}.button:disabled{cursor:not-allowed;opacity:.48}
.review-note{background:#fff4d9;border:1px solid #ead5a2;border-radius:16px;padding:13px 15px;margin:16px 0 0;white-space:nowrap;overflow-x:auto}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin-top:22px}.routine-card{min-height:190px;border:1px solid #d9d5ca;border-radius:18px;padding:18px;background:var(--paper);display:flex;flex-direction:column;min-width:0;position:relative;overflow:hidden}.routine-card:before{content:"";position:absolute;inset:0 0 auto;height:7px;background:linear-gradient(90deg,var(--coral),var(--gold),#72a99c)}.routine-card strong,.routine-card span,.routine-card small{display:block;white-space:nowrap;overflow-x:auto}.routine-card strong{font-size:12px;color:#657084;text-transform:uppercase;letter-spacing:.05em;margin-top:6px}.routine-card .icon{font-size:34px;margin:13px 0 7px}.routine-card .step{font-weight:790}.routine-card small{margin-top:auto;padding-top:15px;color:var(--muted)}.routine-card.compact .icon{font-size:48px}.routine-card.words .icon{display:none}.cue{grid-column:1/-1;background:var(--sky);border-color:#c4dce8;min-height:auto}.pause{background:var(--mint);border-color:#c5ddcf;min-height:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ol,.card ul{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fffdf8,#edf5f2)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--navy);color:#fff;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}}
@media(max-width:560px){.controls,.cards{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.actions,.app-card,.footer,.faq{display:none!important}body{background:#fff}.planner,.card{box-shadow:none}.routine-card{break-inside:avoid}.cards{grid-template-columns:repeat(2,1fr)}}
"""


SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("routine-config").textContent);
  const form = document.getElementById("routine-planner");
  const fields = {
    context: document.getElementById("context"),
    card_count: document.getElementById("card-count"),
    presentation: document.getElementById("presentation"),
    transition_cue: document.getElementById("transition-cue"),
    adult_reviewed: document.getElementById("adult-reviewed")
  };
  const cards = document.getElementById("routine-cards");
  const reviewNote = document.getElementById("review-note");
  const printButton = document.getElementById("print-cards");

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

  function integerValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const rule = config.inputSchema.properties[name];
    if (!Number.isInteger(value) || value < rule.minimum || value > rule.maximum) {
      throw new RangeError(`${name} is outside the supported range.`);
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
    const context = enumValue(input, "context");
    const cardCount = integerValue(input, "card_count");
    const presentation = enumValue(input, "presentation");
    const transitionCue = enumValue(input, "transition_cue");
    const adultReviewed = booleanValue(input, "adult_reviewed");
    const selected = {
      context,
      context_label: config.labels.context[context],
      card_count: cardCount,
      presentation,
      presentation_label: config.labels.presentation[presentation],
      transition_cue: transitionCue,
      transition_cue_label: config.labels.transition[transitionCue],
      adult_reviewed: adultReviewed
    };
    if (!adultReviewed) {
      return {
        status: "adult_review_required",
        selected_preferences: selected,
        cards: [],
        transition_note: "",
        adult_review_note: config.adultReviewNo,
        boundary: config.boundary
      };
    }
    const cards = config.contextSteps[context].slice(0, cardCount).map(
      (text, index) => ({
        position: index + 1,
        icon: config.cardIcons[context][index],
        text,
        optional: true,
        may_skip_pause_or_replace: true
      })
    );
    return {
      status: "adult_review_confirmed",
      selected_preferences: selected,
      cards,
      transition_note: config.cueNotes[transitionCue],
      pause_card: config.pauseCard,
      adult_review_note: config.adultReviewYes,
      boundary: config.boundary,
      not_behavior_care_health_sleep_or_learning_advice: true,
      no_outcome_or_independence_guarantee: true
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

  function cardMarkup(card, presentation) {
    const className = presentation === "words" ? "words" :
      presentation === "icons-with-labels" ? "compact" : "";
    return `<article class="routine-card ${className}">` +
      `<strong>${config.cardLabel} ${card.position}</strong>` +
      `<span class="icon" aria-hidden="true">${card.icon}</span>` +
      `<span class="step">${card.text}</span>` +
      `<small>${config.skipLabel}</small></article>`;
  }

  function render() {
    const result = plan({
      context: fields.context.value,
      card_count: Number(fields.card_count.value),
      presentation: fields.presentation.value,
      transition_cue: fields.transition_cue.value,
      adult_reviewed: fields.adult_reviewed.checked
    });
    reviewNote.textContent = result.adult_review_note;
    const confirmed = result.status === "adult_review_confirmed";
    printButton.disabled = !confirmed;
    if (!confirmed) {
      cards.replaceChildren();
      return;
    }
    cards.innerHTML = result.cards.map(
      (card) => cardMarkup(card, result.selected_preferences.presentation)
    ).join("") +
      `<article class="routine-card cue"><strong>${config.transitionLabel}</strong>` +
      `<span class="step">${result.transition_note}</span></article>` +
      `<article class="routine-card pause"><span class="step">${result.pause_card}</span>` +
      `<small>${result.boundary}</small></article>`;
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_family_routine_cards",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_parent_reviewed_family_routine_cards",
          child_names_ages_schedules_schools_profiles_not_received: true,
          no_behavior_completion_location_photo_account_or_free_text: true,
          no_upload_storage_monitoring_scoring_diagnosis_or_prediction: true,
          plan,
          adult_preflight: config.preflightSteps,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_lumi_mission_planet = config.optionalApp;
        }
        return JSON.stringify(result);
      }
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
  for (const [name, field] of Object.entries(fields)) {
    field.addEventListener("change", () => {
      if (name !== "adult_reviewed") {
        fields.adult_reviewed.checked = false;
      }
      render();
    });
  }
  printButton.addEventListener("click", () => {
    if (fields.adult_reviewed.checked) window.print();
  });
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
            "context": {
                "type": "string",
                "enum": list(CONTEXTS),
                "description": t["context_label"],
            },
            "card_count": {
                "type": "integer",
                "minimum": min(CARD_COUNTS),
                "maximum": max(CARD_COUNTS),
                "description": t["count_label"],
            },
            "presentation": {
                "type": "string",
                "enum": list(PRESENTATIONS),
                "description": t["presentation_label"],
            },
            "transition_cue": {
                "type": "string",
                "enum": list(TRANSITION_CUES),
                "description": t["transition_label"],
            },
            "adult_reviewed": {
                "type": "boolean",
                "description": t["adult_review_label"],
            },
        },
        "required": [
            "context",
            "card_count",
            "presentation",
            "transition_cue",
            "adult_reviewed",
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
    preflight_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["preflight_steps"]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_family_routine_{locale.lower()}")
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
            "context": t["context_options"],
            "presentation": t["presentation_options"],
            "transition": t["transition_options"],
        },
        "contextSteps": t["context_steps"],
        "cardIcons": CARD_ICONS,
        "cueNotes": t["cue_notes"],
        "adultReviewYes": t["adult_review_yes"],
        "adultReviewNo": t["adult_review_no"],
        "cardLabel": t["card_label"],
        "skipLabel": t["skip_label"],
        "transitionLabel": t["transition_label"],
        "pauseCard": t["pause_card"],
        "boundary": t["boundary"],
        "preflightSteps": t["preflight_steps"],
        "toolDescription": t["webmcp_description"],
        "freePlanner": {
            "label": t["heading"],
            "url": url,
            "boundary": t["planner_intro"],
        },
        "officialSources": [
            {"label": t["source_label"], "url": CDC_ROUTINES}
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
        "applicationCategory": "LifestyleApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "featureList": [t["planner"], *t["badges"]],
        "citation": [CDC_ROUTINES],
        "audience": {"@type": "PeopleAudience", "suggestedMinAge": 18},
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
    count_options = "".join(
        f'<option value="{count}">{count}</option>' for count in CARD_COUNTS
    )
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
<form id="routine-planner"><div class="controls">
<div class="field"><label for="context">{html.escape(t["context_label"])}</label><select id="context">{options(t["context_options"])}</select></div>
<div class="field"><label for="card-count">{html.escape(t["count_label"])}</label><select id="card-count">{count_options}</select></div>
<div class="field"><label for="presentation">{html.escape(t["presentation_label"])}</label><select id="presentation">{options(t["presentation_options"])}</select></div>
<div class="field"><label for="transition-cue">{html.escape(t["transition_label"])}</label><select id="transition-cue">{options(t["transition_options"])}</select></div>
</div><label class="toggle"><input id="adult-reviewed" type="checkbox">{html.escape(t["adult_review_label"])}</label><div class="actions"><button class="button" type="submit">{html.escape(t["update"])}</button><button class="button secondary" id="print-cards" type="button" disabled>{html.escape(t["print"])}</button></div></form>
<p class="review-note" id="review-note"></p><div class="cards" id="routine-cards"></div></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["preflight_title"])}</h2><ol>{preflight_items}</ol></article><article class="card"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><p><a href="{CDC_ROUTINES}" rel="noopener">{html.escape(t["source_label"])}</a></p><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="routine-config">{config_json}</script>
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
        r'private-daily-checklist-planner">.*?</article>)',
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
    "best-kids-routine-app.html",
    "best-chore-and-routine-app-for-kids.html",
)
INBOUND_LINK_CLASS = "family-routine-card-planner-inline-link"
_LUMI_MISSION_CTA = re.compile(
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
            f'data-family-routine-card-planner-link="1" href="{canonical(locale)}" '
            f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
        )
        for slug in TARGET_ANSWER_SLUGS:
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _LUMI_MISSION_CTA.search(text)
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
        print(f"family routine card planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()

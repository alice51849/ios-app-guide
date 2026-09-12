"""Native editorial framing for unpublished Western/Romance surface builds."""

from western_romance_copy import ENGLISH_LOCALES, LOCALES, language_variant

COPY = {
    "en": {
        "persona_title": "Who is {name} for?",
        "persona_intro": "Start with the task you want to complete, then check whether the workflow and purchase model suit you.",
        "alternatives": "Workflow alternatives",
        "comparison": "Compare this dedicated app with {method}. If your existing approach meets the need, you may not need another app. This is a comparison of workflows, not a test or ranking of competing products.",
        "feed_title": "Lumi Studio app guides",
        "feed_description": "Product-specific tasks, purchase models and guides from the app publisher.",
        "disclosure": "First-party guide by Lumi Studio, the app publisher. This is not an independent ranking, a review of competitors or a claim of local market research. Product descriptions can be shared across English variants. Check availability and current terms in your App Store.",
        "back": "App guide", "faq": "Questions", "guide": "Read the guide",
        "store": "View {name} on the App Store", "purchase": "Purchase model",
        "methods": ("paper notes and checklists", "a spreadsheet", "a manual document workflow", "printed learning materials", "your device settings", "browser bookmarks", "a photography service", "a presentation editor", "a desktop archive tool", "a sound recording", "a paper planner"),
    },
    "fr-CA": {
        "persona_title": "À qui s'adresse {name}?",
        "persona_intro": "Partez de la tâche à accomplir, puis vérifiez si les fonctions et le modèle d'achat répondent à vos besoins.",
        "alternatives": "Autres façons de faire",
        "comparison": "Comparez cette application avec cette méthode : {method}. Si votre façon de faire actuelle répond au besoin, une application de plus n'est peut-être pas nécessaire. Il s'agit d'une comparaison de méthodes, pas d'un test ni d'un classement de produits concurrents.",
        "feed_title": "Guides des applications Lumi Studio",
        "feed_description": "Tâches, modèles d'achat et guides propres à chaque application, préparés par son éditeur.",
        "disclosure": "Guide préparé par Lumi Studio, le créateur des applications présentées. Ce n'est ni un classement indépendant, ni un test de concurrents, ni une étude du marché local. Vérifiez la disponibilité et les conditions actuelles dans votre App Store.",
        "back": "Guide des applications", "faq": "Questions", "guide": "Lire le guide",
        "store": "Voir {name} dans l'App Store", "purchase": "Modèle d'achat",
        "methods": ("des notes et listes sur papier", "une feuille de calcul", "une gestion manuelle des documents", "du matériel pédagogique imprimé", "les réglages de votre appareil", "les favoris du navigateur", "un service de photographie", "un logiciel de présentation", "un outil d'archives sur ordinateur", "un enregistrement sonore", "un agenda papier"),
    },
    "fr-FR": {
        "persona_title": "À qui s'adresse {name} ?",
        "persona_intro": "Partez de la tâche à accomplir, puis vérifiez si le fonctionnement et le modèle d'achat correspondent à vos besoins.",
        "alternatives": "D'autres façons de faire",
        "comparison": "Comparez cette application avec cette méthode : {method}. Si votre méthode actuelle répond au besoin, une application supplémentaire n'est peut-être pas nécessaire. Il s'agit d'une comparaison de méthodes, pas d'un test ni d'un classement de produits concurrents.",
        "feed_title": "Guides des applications Lumi Studio",
        "feed_description": "Tâches, modèles d'achat et guides propres à chaque application, rédigés par son éditeur.",
        "disclosure": "Guide rédigé par Lumi Studio, l'éditeur des applications présentées. Ce n'est ni un classement indépendant, ni un test de concurrents, ni une étude du marché local. Vérifiez la disponibilité et les conditions actuelles dans votre App Store.",
        "back": "Guide des applications", "faq": "Questions", "guide": "Lire le guide",
        "store": "Voir {name} sur l'App Store", "purchase": "Modèle d'achat",
        "methods": ("des notes et listes sur papier", "un tableur", "une gestion manuelle des documents", "des supports pédagogiques imprimés", "les réglages de votre appareil", "les favoris du navigateur", "un service de photographie", "un logiciel de présentation", "un outil d'archives sur ordinateur", "un enregistrement sonore", "un agenda papier"),
    },
    "es-ES": {
        "persona_title": "¿Para quién es {name}?",
        "persona_intro": "Empieza por la tarea que quieres realizar y comprueba si el funcionamiento y el modelo de compra encajan contigo.",
        "alternatives": "Otras formas de hacerlo",
        "comparison": "Compara esta aplicación con esta opción: {method}. Si tu método actual cubre la necesidad, puede que no necesites otra aplicación. Esta es una comparación de formas de trabajar, no una prueba ni una clasificación de productos competidores.",
        "feed_title": "Guías de aplicaciones de Lumi Studio",
        "feed_description": "Tareas, modelos de compra y guías de cada aplicación, redactadas por su editor.",
        "disclosure": "Guía de Lumi Studio, el editor de las aplicaciones presentadas. No es una clasificación independiente, una prueba de competidores ni un estudio del mercado local. Comprueba la disponibilidad y las condiciones actuales en tu App Store.",
        "back": "Guía de aplicaciones", "faq": "Preguntas", "guide": "Leer la guía",
        "store": "Ver {name} en el App Store", "purchase": "Modelo de compra",
        "methods": ("notas y listas en papel", "una hoja de cálculo", "la gestión manual de documentos", "material de aprendizaje impreso", "los ajustes del dispositivo", "los marcadores del navegador", "un servicio de fotografía", "un editor de presentaciones", "una herramienta de archivos comprimidos en el ordenador", "una grabación de sonido", "una agenda de papel"),
    },
    "es-MX": {
        "persona_title": "¿Para quién es {name}?",
        "persona_intro": "Empieza por la tarea que quieres realizar y revisa si las funciones y el modelo de compra se ajustan a lo que necesitas.",
        "alternatives": "Otras maneras de hacerlo",
        "comparison": "Compara esta app con esta opción: {method}. Si tu método actual cubre la necesidad, quizá no necesites otra app. Esta es una comparación de maneras de trabajar, no una prueba ni una clasificación de productos competidores.",
        "feed_title": "Guías de apps de Lumi Studio",
        "feed_description": "Tareas, modelos de compra y guías de cada app, preparadas por su editor.",
        "disclosure": "Guía de Lumi Studio, el editor de las apps presentadas. No es una clasificación independiente, una prueba de competidores ni un estudio del mercado local. Revisa la disponibilidad y las condiciones actuales en tu App Store.",
        "back": "Guía de apps", "faq": "Preguntas", "guide": "Leer la guía",
        "store": "Ver {name} en App Store", "purchase": "Modelo de compra",
        "methods": ("notas y listas en papel", "una hoja de cálculo", "la gestión manual de documentos", "material de aprendizaje impreso", "la configuración del dispositivo", "los favoritos del navegador", "un servicio de fotografía", "un editor de presentaciones", "una herramienta de archivos comprimidos en la computadora", "una grabación de sonido", "una agenda de papel"),
    },
    "pt-BR": {
        "persona_title": "Para quem é o {name}?",
        "persona_intro": "Comece pela tarefa que você precisa realizar e confira se os recursos e o modelo de compra fazem sentido para você.",
        "alternatives": "Outras formas de fazer",
        "comparison": "Compare este app com esta opção: {method}. Se o seu método atual atende à necessidade, talvez você não precise de outro app. Esta é uma comparação de formas de trabalhar, não um teste nem um ranking de produtos concorrentes.",
        "feed_title": "Guias de apps da Lumi Studio",
        "feed_description": "Tarefas, modelos de compra e guias de cada app, preparados pelo próprio desenvolvedor.",
        "disclosure": "Guia da Lumi Studio, responsável pelos apps apresentados. Não é um ranking independente, um teste de concorrentes nem uma pesquisa do mercado local. Confira a disponibilidade e as condições atuais na sua App Store.",
        "back": "Guia de apps", "faq": "Perguntas", "guide": "Ler o guia",
        "store": "Ver {name} na App Store", "purchase": "Modelo de compra",
        "methods": ("anotações e listas em papel", "uma planilha", "a organização manual de documentos", "materiais de estudo impressos", "as configurações do aparelho", "os favoritos do navegador", "um serviço de fotografia", "um editor de apresentações", "uma ferramenta de arquivos compactados no computador", "uma gravação de áudio", "uma agenda de papel"),
    },
    "pt-PT": {
        "persona_title": "A quem se destina o {name}?",
        "persona_intro": "Comece pela tarefa que pretende realizar e confirme se as funcionalidades e o modelo de compra correspondem ao que precisa.",
        "alternatives": "Outras formas de realizar a tarefa",
        "comparison": "Compare esta aplicação com esta opção: {method}. Se a sua forma de trabalhar já responde à necessidade, pode não precisar de outra aplicação. Esta é uma comparação de métodos, não um teste nem uma classificação de produtos concorrentes.",
        "feed_title": "Guias de aplicações da Lumi Studio",
        "feed_description": "Tarefas, modelos de compra e guias de cada aplicação, preparados pelo respetivo editor.",
        "disclosure": "Guia da Lumi Studio, o editor das aplicações apresentadas. Não é uma classificação independente, um teste de concorrentes nem um estudo do mercado local. Confirme a disponibilidade e as condições atuais na sua App Store.",
        "back": "Guia de aplicações", "faq": "Perguntas", "guide": "Ler o guia",
        "store": "Ver {name} na App Store", "purchase": "Modelo de compra",
        "methods": ("notas e listas em papel", "uma folha de cálculo", "a organização manual de documentos", "materiais de aprendizagem impressos", "as definições do dispositivo", "os marcadores do navegador", "um serviço de fotografia", "um editor de apresentações", "uma ferramenta de ficheiros comprimidos no computador", "uma gravação de som", "uma agenda em papel"),
    },
}

METHOD_GROUPS = (
    ("aibriefpack", "mochi", "mochidonestamp", "notesstudio100", "sononote"),
    ("caldaily", "gmoney", "gmoneylite", "hourstag", "hourstaglite", "moneytag"),
    ("cvdesk", "maskmyfile", "scanto"),
    ("aim990", "aim990plus", "dailymate", "dailymatelite", "lumibopomofo", "lumibopomofopro", "lumiletters", "lumiletterspro", "lumimath", "lumimathpro", "wordmate", "wordmatelite"),
    ("battai", "lockhour", "lumiweather", "picclear", "shotinbox", "wifiaid", "wifiaidlite"),
    ("savetag",),
    ("photocream", "snapport", "snapportlite", "unblurry"),
    ("onepageppt",),
    ("zipbox",),
    ("sereno",),
    ("cyca", "lumimission", "lumimissionpro", "tripbee", "tripbeelite", "tripplanet"),
)
METHOD_BY_APP = {key: index for index, keys in enumerate(METHOD_GROUPS) for key in keys}


def for_locale(locale):
    if locale not in LOCALES:
        raise ValueError(f"Unsupported Western surface locale: {locale}")
    return COPY[language_variant(locale)]


def alternative_method(key, locale):
    return for_locale(locale)["methods"][METHOD_BY_APP[key]]


def editorial_scope(locale):
    return (
        "shared_English_product_copy_not_local_market_research"
        if locale in ENGLISH_LOCALES
        else "native_product_copy_not_local_market_research"
    )

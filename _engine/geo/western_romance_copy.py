"""Reviewed Western/Romance outreach only; never write this copy to ASC.

English descriptions describe shared product functionality, not country-specific
research or availability. Region labels identify the requested language variant.
"""

from __future__ import annotations

import re
import unicodedata

LOCALES = (
    "en-AU", "en-CA", "en-GB", "en-US", "fr-CA", "fr-FR",
    "es-ES", "es-MX", "pt-BR", "pt-PT",
)
ENGLISH_LOCALES = frozenset(LOCALES[:4])

PURCHASE = {
    "en": (
        "Paid download: one purchase includes the full app, with no additional in-app purchases or subscription.",
        "Start with the free features and their stated limits. An optional one-time in-app purchase unlocks the full experience; there is no subscription.",
    ),
    "fr-CA": (
        "Application payante au téléchargement : un seul achat comprend toutes les fonctions, sans achat intégré supplémentaire ni abonnement.",
        "Les fonctions de base sont gratuites, avec les limites indiquées. Un achat intégré unique permet de déverrouiller l'expérience complète, sans abonnement.",
    ),
    "fr-FR": (
        "Application payante au téléchargement : un achat donne accès à l'ensemble des fonctionnalités, sans achat intégré supplémentaire ni abonnement.",
        "Les fonctions de base sont gratuites, dans les limites indiquées. Un achat intégré unique permet de débloquer l'expérience complète, sans abonnement.",
    ),
    "es-ES": (
        "La aplicación se paga al descargarla. Una compra incluye todas las funciones, sin compras adicionales dentro de la aplicación ni suscripción.",
        "Las funciones básicas son gratuitas, con los límites indicados. Una compra única dentro de la aplicación desbloquea la experiencia completa, sin suscripción.",
    ),
    "es-MX": (
        "La app se paga al descargarla. Una sola compra incluye todas las funciones, sin compras adicionales dentro de la app ni suscripción.",
        "Las funciones básicas son gratis, con los límites indicados. Una compra única dentro de la app desbloquea la experiencia completa, sin suscripción.",
    ),
    "pt-BR": (
        "O app é pago no download. Uma compra inclui todos os recursos, sem compras adicionais no app nem assinatura.",
        "Os recursos básicos são gratuitos, com os limites informados. Uma compra única opcional no app desbloqueia a experiência completa, sem assinatura.",
    ),
    "pt-PT": (
        "A aplicação é paga ao descarregar. Um único pagamento inclui todas as funcionalidades, sem compras adicionais na aplicação nem subscrição.",
        "As funcionalidades de base são gratuitas, com os limites indicados. Um pagamento único opcional na aplicação desbloqueia a experiência completa, sem subscrição.",
    ),
}

PT_PT_UI = {
    "what": "O que é {name}?",
    "feat": "Funcionalidades principais",
    "price": "Modelo de compra",
    "faq": "Perguntas frequentes",
    "dl": "Descarregar",
    "get": "Ver {name} na App Store",
    "is": "{name} é uma aplicação para iOS.",
    "ptxt": PURCHASE["pt-PT"][1],
    "dir_dir": "Diretório de aplicações",
    "dir_lead": "Guias do editor sobre funcionalidades, modelos de compra e utilização das aplicações.",
    "catalog": "Ver o catálogo de aplicações",
}
PT_PT_QUESTIONS = (
    "Que aplicação permite trabalhar com {kw}?",
    "Como usar uma aplicação para {kw}?",
    "O que procurar numa aplicação para {kw}?",
)
PT_PT_ANSWER = "{name} permite explorar esta tarefa: {sub}. Consulte as funcionalidades e o modelo de compra antes de descarregar."

IDENTITIES = {
    "lumiletters": "Lumi Letters Lite",
    "lumiletterspro": "Lumi Letters Pro",
    "lumibopomofopro": "Lumi Bopomofo Pro",
    "lumimathpro": "Lumi Math Pro",
    "lumimissionpro": "Lumi Mission Planet Pro",
    "tripplanet": "Trip Planet: Kids Quest",
    "tripbee": "TripBee Pro",
    "photocream": "PhotoCream Pro",
    "picclear": "PicClear Pro",
    "unblurry": "Unblurry Pro",
    "zipbox": "Zipbox",
}

# Headline, product-specific explanation, and native task terms.
PT_PT_COPY = {
    "aibriefpack": (
        "Ficheiros e notas num contexto claro",
        "O AI Brief reúne capturas de ecrã, ficheiros, notas e documentos num contexto preparado para um assistente de inteligência artificial.\n\nReveja as fontes, os factos e os dados pessoais antes de copiar ou exportar o resultado. A escolha do que enviar para outro serviço continua a ser sua; a aplicação não garante anonimato.",
        "contexto, ficheiros, notas, documentos, capturas de ecrã, fontes, dados pessoais, inteligência artificial",
    ),
    "aim990": (
        "Prática diária de compreensão oral e escrita",
        "O Aim990 ajuda a preparar o TOEIC com exercícios de compreensão oral e escrita, revisão das áreas mais difíceis e acompanhamento da evolução.\n\nA prática cronometrada permite trabalhar o ritmo de resposta. Não há garantia de pontuação nem de resultados num prazo fixo. TOEIC é uma marca registada da ETS; o Aim990 não é um produto oficial da ETS.",
        "preparação TOEIC, inglês, compreensão oral, compreensão escrita, revisão, exercícios, ritmo de resposta, evolução",
    ),
    "aim990plus": (
        "Decisões claras sob pressão de tempo",
        "O Aim990 Plus propõe exercícios de compreensão oral e escrita em inglês, com atenção ao tempo disponível para decidir.\n\nPratique, reveja as respostas e identifique o que precisa de trabalhar a seguir. É uma aplicação paga independente, com todas as ferramentas incluídas; não promete uma pontuação nem um resultado no exame.",
        "inglês, compreensão oral, compreensão escrita, exercícios, tempo de resposta, revisão, preparação, aprendizagem",
    ),
    "battai": (
        "Perceba as fontes dos dados da bateria",
        "O BattAI distingue leituras disponibilizadas pelo iOS, estimativas calculadas e dados introduzidos por si.\n\nConsulte o nível de bateria, o estado de carga e a evolução dos registos, com a fonte e os limites de cada indicador. As estimativas não são medições de diagnóstico nem substituem a informação técnica da Apple.",
        "bateria, nível de carga, estimativas, registos, fontes, limites, evolução, dispositivo",
    ),
    "caldaily": (
        "Cálculos com um histórico que faz sentido",
        "O CalDaily guarda os cálculos e permite dar um nome aos resultados para os encontrar mais tarde.\n\nUse as ferramentas de unidades, descontos, divisão de contas, datas ou empréstimos quando precisar. O histórico e o widget ajudam a retomar o raciocínio sem voltar a escrever tudo.",
        "calculadora, histórico, unidades, descontos, divisão de contas, datas, empréstimos, widget",
    ),
    "cvdesk": (
        "Prepare e reveja o seu currículo",
        "O CV Desk ajuda a organizar um currículo, escolher um modelo e rever a sua estrutura antes de o enviar.\n\nAs verificações de compatibilidade com sistemas de recrutamento servem de orientação, não de garantia de seleção, entrevista ou emprego. Reveja sempre os dados e a versão final.",
        "currículo, modelos, candidatura, experiência, competências, recrutamento, revisão, documento",
    ),
    "cyca": (
        "Um registo pessoal do seu ciclo",
        "O Cyca ajuda a registar o período, os sintomas e as observações do dia a dia para acompanhar o ciclo ao longo do tempo.\n\nAs previsões são estimativas baseadas nos registos, não um diagnóstico nem um método contracetivo. Em caso de dúvida sobre a saúde, procure aconselhamento clínico.",
        "ciclo menstrual, período, sintomas, registos, observações, calendário, estimativas, bem-estar",
    ),
    "dailymate": (
        "Aprenda línguas com frases completas",
        "O DailyMate organiza a aprendizagem em frases completas para situações de viagem, trabalho e conversas do dia a dia.\n\nEscolha um tema, ouça os exemplos e pratique ao seu ritmo. A edição paga inclui a experiência completa, com o widget e a utilização no Apple Watch.",
        "línguas, frases, conversação, compreensão oral, viagem, trabalho, prática, vocabulário",
    ),
    "dailymatelite": (
        "Prepare-se para a próxima conversa",
        "O DailyMate Lite ajuda a praticar frases e diálogos para quando chegar a sua vez de falar.\n\nEscolha uma situação, ouça e repita, depois reveja o que ainda custa a recordar. Pode explorar a experiência gratuita antes de decidir se precisa do conteúdo completo.",
        "línguas, diálogos, frases, conversação, ouvir, repetir, situações, prática",
    ),
    "gmoney": (
        "Despesas, orçamento e conversão de moedas",
        "O G+Money reúne o registo de despesas, o orçamento e a conversão de moedas para perceber para onde vai o dinheiro.\n\nOrganize os movimentos e consulte os totais ao seu ritmo. As taxas de câmbio são valores de referência; o valor aplicado por um banco ou cartão pode ser diferente.",
        "despesas, orçamento, moedas, câmbio, movimentos, totais, poupança, finanças pessoais",
    ),
    "gmoneylite": (
        "Despesas de viagem na sua moeda",
        "O G+Money Lite regista despesas na moeda local e mostra o respetivo valor na moeda que escolher.\n\nOrganize os gastos da viagem e consulte as taxas guardadas quando não houver ligação. As taxas são referências, não uma promessa do câmbio aplicado pelo banco. A versão gratuita tem limites de viagens e registos.",
        "despesas de viagem, moeda local, câmbio, orçamento, viagens, registos, conversão, taxas",
    ),
    "hourstag": (
        "Veja as despesas em horas de trabalho",
        "O HoursTag converte o valor das despesas registadas em horas de trabalho, a partir do rendimento definido por si.\n\nClassifique os gastos, reveja o histórico e acompanhe objetivos com uma perspetiva sobre o tempo necessário para os pagar. Os resultados dependem dos valores que introduzir.",
        "despesas, horas de trabalho, rendimento, gastos, histórico, objetivos, orçamento, tempo",
    ),
    "hourstaglite": (
        "Perceba o tempo que uma compra custa",
        "O HoursTag Lite transforma um preço em horas de trabalho com base no rendimento que indicar.\n\nUse a conversão antes de uma compra para comparar prioridades. É uma forma de refletir sobre uma decisão, não aconselhamento financeiro nem uma promessa de poupança.",
        "preço, horas de trabalho, rendimento, compras, prioridades, conversão, orçamento, poupança",
    ),
    "lockhour": (
        "Reserve tempo para se concentrar",
        "O LockHour Pro ajuda a definir períodos de concentração e a limitar as aplicações que interrompem o trabalho ou o estudo.\n\nEscolha as aplicações e o tempo da sessão, depois reveja o que funciona no seu dia. A ferramenta apoia a rotina; não garante produtividade nem trata dificuldades de atenção.",
        "concentração, bloquear aplicações, estudo, trabalho, sessões, tempo de ecrã, rotina, distrações",
    ),
    "lumibopomofo": (
        "Primeiros sinais e sons do mandarim",
        "O Lumi Bopomofo apresenta o zhuyin, o sistema de sinais usado para aprender a pronúncia do mandarim em Taiwan.\n\nAs crianças ouvem os sons, seguem os traços e experimentam jogos curtos. O sinal ㄅ e três utilizações do comboio estão disponíveis gratuitamente; os restantes conteúdos exigem o desbloqueio por um adulto.",
        "bopomofo, zhuyin, mandarim, pronúncia, sinais, escrita, sons, crianças",
    ),
    "lumibopomofopro": (
        "Todos os 37 sinais do bopomofo",
        "O Lumi Bopomofo Pro inclui o percurso completo dos 37 sinais do zhuyin para explorar a pronúncia do mandarim.\n\nAs atividades combinam audição, associação, escrita e prática dos tons. A edição Pro já inclui o conteúdo completo e funciona sem ligação à internet e sem publicidade.",
        "bopomofo, zhuyin, mandarim, pronúncia, tons, escrita, audição, crianças",
    ),
    "lumiletters": (
        "As primeiras letras inglesas, a brincar",
        "O Lumi Letters Lite ajuda a reconhecer letras inglesas, ouvir os seus sons e praticar a escrita com o dedo.\n\nA letra A pode ser praticada gratuitamente. As restantes letras continuam visíveis para explorar; a sua utilização exige um pagamento único autorizado por um adulto.",
        "alfabeto inglês, letras, sons, escrita, crianças, maiúsculas, minúsculas, aprendizagem",
    ),
    "lumiletterspro": (
        "O alfabeto inglês completo",
        "O Lumi Letters Pro inclui as 26 letras inglesas, os seus nomes e sons, com atividades para reconhecer e escrever maiúsculas e minúsculas.\n\nSiga a ordem dos traços e pratique com jogos. A edição Pro inclui o alfabeto completo, sem ligação à internet e sem publicidade.",
        "alfabeto inglês, letras, sons, escrita, maiúsculas, minúsculas, jogos, crianças",
    ),
    "lumimath": (
        "Descubra os números através do jogo",
        "O Lumi Math Planet apresenta números e pequenas atividades de matemática num mundo de exploração para crianças.\n\nConte, compare e pratique ao seu ritmo. A experiência gratuita mantém os conteúdos adicionais visíveis para explorar antes do desbloqueio por um adulto.",
        "números, contar, comparar, matemática, crianças, jogos, prática, aprendizagem",
    ),
    "lumimathpro": (
        "A aventura matemática completa",
        "O Lumi Math Pro inclui a edição completa das atividades de números, cálculo e desafios de raciocínio para crianças.\n\nA criança pratica ao seu ritmo e regressa aos exercícios que quer rever. A edição Pro já inclui todos os conteúdos, sem ligação à internet e sem publicidade.",
        "matemática, números, cálculo, raciocínio, crianças, exercícios, jogos, revisão",
    ),
    "lumimission": (
        "Pequenas tarefas para a rotina das crianças",
        "O Lumi Mission Planet transforma lavar os dentes, arrumar brinquedos e preparar a hora de dormir em pequenas missões.\n\nAs estrelas e recompensas valorizam o esforço. A família pode experimentar a rotina gratuita e explorar os conteúdos adicionais antes do desbloqueio por um adulto.",
        "rotina infantil, tarefas, hábitos, recompensas, lavar os dentes, arrumar, hora de dormir, família",
    ),
    "lumimissionpro": (
        "Todas as missões e recompensas da rotina",
        "O Lumi Mission Planet Pro inclui as missões, recompensas e definições completas para a rotina da família.\n\nLavar os dentes, vestir-se, arrumar brinquedos e preparar a hora de dormir tornam-se pequenas tarefas espaciais. Esta é a edição paga Pro, com todo o conteúdo incluído desde a compra.",
        "rotina infantil, missões, recompensas, hábitos, vestir, arrumar, hora de dormir, família",
    ),
    "lumiweather": (
        "Meteorologia para os planos em família",
        "O Lumi Weather apresenta previsões meteorológicas e informação útil para decidir o que levar ou vestir numa saída com crianças.\n\nConsulte chuva, temperatura, vento e radiação ultravioleta. As previsões podem mudar; confirme os avisos oficiais quando houver condições meteorológicas adversas.",
        "meteorologia, previsão, chuva, temperatura, vento, radiação ultravioleta, crianças, saídas",
    ),
    "maskmyfile": (
        "Retire os dados pessoais da cópia a partilhar",
        "O Mask My File ajuda a encontrar e rever dados pessoais antes de partilhar imagens, documentos e ficheiros de texto.\n\nEscolha o que quer remover ou ocultar de forma permanente e verifique a nova cópia. A deteção pode falhar, pelo que a revisão final é essencial. Mantenha o original e confirme que tem autorização para partilhar os dados que permanecerem.",
        "dados pessoais, documentos, imagens, ocultação permanente, revisão, cópia, partilha, privacidade",
    ),
    "mochi": (
        "Listas simples para um dia mais tranquilo",
        "O Mochi organiza tarefas e listas de verificação sem transformar cada compromisso num projeto complicado.\n\nAnote o que precisa de fazer, reveja as prioridades e assinale o que já ficou concluído. Serve para compras, estudo, pequenas rotinas ou a preparação de uma viagem.",
        "tarefas, listas, prioridades, compras, estudo, rotinas, viagem, organização",
    ),
    "mochidonestamp": (
        "Recorde quando fez cada tarefa",
        "O Mochi DoneStamp regista a última vez que concluiu uma tarefa, como regar uma planta ou trocar os lençóis.\n\nUm toque deixa a data guardada e o histórico ajuda a perceber o ritmo de cada atividade. É um registo do que aconteceu, não apenas uma lista do que falta fazer.",
        "última vez, tarefas concluídas, datas, histórico, plantas, casa, rotinas, registos",
    ),
    "moneytag": (
        "Cada projeto com as suas contas",
        "O MoneyTag organiza receitas, despesas e o resultado de cada projeto, com etiquetas para analisar os registos em conjunto.\n\nSepare atividades, procure movimentos e reveja os totais antes de tomar decisões. As contas refletem os dados introduzidos e não substituem aconselhamento contabilístico.",
        "projetos, receitas, despesas, resultado, etiquetas, movimentos, totais, contas",
    ),
    "notesstudio100": (
        "Cadernos, escrita à mão e documentos",
        "O 100 Notes Studio reúne escrita à mão, texto, anotações em PDF e gravações associadas às páginas.\n\nEscolha entre os estilos de caderno, trabalhe em páginas fixas ou numa superfície contínua e organize o material de estudo. A pré-visualização permite conhecer os estilos antes de escolher o que pretende usar.",
        "cadernos, escrita à mão, apontamentos, PDF, anotações, páginas, gravações, estudo",
    ),
    "onepageppt": (
        "Transforme as notas num diapositivo",
        "O OnePage PPT ajuda a condensar um conjunto de notas num único diapositivo, com uma hierarquia visual clara.\n\nOrganize o conteúdo, ajuste a apresentação e reveja o resultado antes de o exportar. É uma ferramenta para preparar a sua mensagem, não uma garantia de que a audiência a vai compreender.",
        "diapositivo, apresentação, notas, conteúdo, hierarquia, mensagem, exportar, organização",
    ),
    "photocream": (
        "Fotografias com carácter de película",
        "O PhotoCream Pro reúne filtros inspirados em película, grão, efeitos de luz e ferramentas para ajustar fotografias.\n\nExperimente diferentes acabamentos e reveja a imagem antes de guardar. O resultado depende da fotografia original e das escolhas de edição.",
        "fotografia, película, filtros, grão, luz, edição, câmara, efeitos",
    ),
    "picclear": (
        "Reveja fotografias antes de libertar espaço",
        "O PicClear Pro encontra fotografias semelhantes, duplicados e vídeos grandes para ajudar a rever a fototeca.\n\nA análise e a pré-visualização são gratuitas; as ações de limpeza exigem o desbloqueio indicado na aplicação. Confirme os elementos selecionados antes de autorizar uma eliminação.",
        "fotografias, duplicados, vídeos, fototeca, espaço, pré-visualização, revisão, limpeza",
    ),
    "savetag": (
        "Guarde ligações e volte a encontrá-las",
        "O SaveTag reúne ligações guardadas, notas e etiquetas para encontrar mais tarde o que chamou a sua atenção.\n\nGuarde a partir do menu Partilhar, procure por tema e retome os conteúdos por ler. A organização ajuda a evitar que as ligações fiquem dispersas por conversas e capturas de ecrã.",
        "ligações, guardar para depois, etiquetas, notas, pesquisa, leitura, partilhar, organização",
    ),
    "scanto": (
        "Digitalize e organize os documentos",
        "O ScanTo Pro digitaliza documentos, reconhece texto e permite organizar e procurar os ficheiros guardados.\n\nReveja os limites da página e o texto reconhecido antes de guardar ou partilhar. A proteção com Face ID ajuda a controlar o acesso aos documentos na aplicação.",
        "digitalizar, documentos, reconhecimento de texto, ficheiros, pesquisa, PDF, revisão, Face ID",
    ),
    "sereno": (
        "Sons e ruído para descansar ou concentrar-se",
        "O Sereno permite combinar sons de chuva, mar e ruído para criar um ambiente de descanso ou concentração.\n\nAjuste cada som e use o temporizador para terminar a reprodução gradualmente. É uma ferramenta sonora, não um tratamento para insónia, zumbidos ou dificuldades de atenção.",
        "sons, chuva, mar, ruído branco, descanso, concentração, temporizador, mistura",
    ),
    "shotinbox": (
        "Encontre e trate as capturas de ecrã",
        "O ShotInbox AI organiza capturas de ecrã e ajuda a encontrar texto, ligações e ações úteis sem perder o contexto.\n\nAs 50 capturas mais recentes incluem a experiência de base gratuita. Reveja as sugestões antes de abrir uma ligação, criar um lembrete ou eliminar uma imagem. A aplicação não elimina fotografias automaticamente.",
        "capturas de ecrã, organização, texto, ligações, lembretes, pesquisa, categorias, revisão",
    ),
    "snapport": (
        "Prepare uma fotografia para documentos",
        "O Snapport ajuda a enquadrar fotografias para documentos, ajustar o fundo e preparar folhas de impressão.\n\nEscolha o formato e confirme sempre os requisitos atuais da entidade que recebe o documento. A utilização de um modelo não garante a aceitação da fotografia.",
        "fotografia para documentos, fotografia tipo passe, enquadramento, fundo, impressão, formatos, passaporte, requisitos",
    ),
    "snapportlite": (
        "Experimente preparar a fotografia para documentos",
        "O Snapport Lite apresenta ferramentas de enquadramento, fundo e impressão para preparar fotografias para documentos.\n\nExplore a experiência gratuita e reveja os limites antes de guardar ou exportar. Confirme os requisitos da entidade destinatária; a aplicação não garante a aceitação da fotografia.",
        "fotografia para documentos, fotografia tipo passe, enquadramento, fundo, impressão, formatos, pré-visualização, requisitos",
    ),
    "sononote": (
        "Passe da gravação às notas",
        "O Sono Note reúne gravação de voz, transcrição e organização de notas para retomar uma conversa ou uma ideia.\n\nReveja o texto reconhecido e as tarefas sugeridas antes de os usar ou partilhar. O reconhecimento pode cometer erros, sobretudo com ruído ou várias pessoas a falar.",
        "gravação, voz, transcrição, notas, tarefas, revisão, conversas, ideias",
    ),
    "tripbee": (
        "O plano completo da sua viagem",
        "O TripBee Pro organiza voos, alojamento, atividades e notas num plano diário de viagem.\n\nConsulte os detalhes de cada dia e prepare a bagagem com a informação no mesmo lugar. Esta é a edição paga Pro, distinta da aplicação TripBee Lite.",
        "viagem, itinerário, voos, alojamento, atividades, bagagem, notas, plano diário",
    ),
    "tripbeelite": (
        "Uma viagem, com tudo organizado",
        "O TripBee Lite organiza uma viagem de cada vez, com voos, alojamento, atividades e notas numa sequência diária.\n\nA versão gratuita guarda uma viagem ativa. O desbloqueio opcional permite guardar mais viagens e usar as restantes funções indicadas na aplicação.",
        "viagem, itinerário, voos, alojamento, atividades, notas, plano diário, organização",
    ),
    "tripplanet": (
        "Missões para descobrir a viagem em família",
        "O Trip Planet: Kids Quest transforma a viagem em família em pequenas missões para as crianças.\n\nOs adultos preparam a viagem e as crianças completam tarefas no avião, no hotel, no restaurante e durante as visitas. Recompensas e recordações acompanham a aventura; os pagamentos e as ligações externas são protegidos por uma verificação parental.",
        "viagem em família, crianças, missões, recompensas, avião, hotel, visitas, recordações",
    ),
    "unblurry": (
        "Ajuste a nitidez e compare o resultado",
        "O Unblurry Pro permite ajustar a nitidez e melhorar fotografias no iPhone, com comparação antes de guardar.\n\nA melhoria depende da imagem original. Um desfocamento intenso pode persistir e os detalhes inexistentes não podem ser recuperados com fiabilidade. A gravação gratuita tem limites de qualidade e utilização.",
        "nitidez, fotografias desfocadas, melhoria de imagem, comparação, pré-visualização, qualidade, fotografias antigas, guardar",
    ),
    "wifiaid": (
        "Diagnóstico de rede com provas separadas",
        "O WiFi Aid ajuda a distinguir problemas de ligação através de verificações de rede, DNS, TCP, TLS, tempos de resposta e sinal.\n\nAnalise os resultados em conjunto e consulte os limites de cada teste. A aplicação pode ajudar a localizar a causa provável; não promete reparar o router nem aumentar a velocidade da ligação.",
        "rede, ligação, diagnóstico, DNS, tempos de resposta, sinal, testes, router",
    ),
    "wifiaidlite": (
        "Descubra o que falha na ligação",
        "O WiFi Aid Lite permite experimentar uma utilização completa de cada ferramenta de diagnóstico da ligação.\n\nFaça um teste rápido, aprofunde a análise ou verifique um sítio específico. Os resultados ajudam a comparar causas prováveis; não garantem uma reparação da rede. A utilização sem limites exige o desbloqueio opcional.",
        "rede, ligação, diagnóstico, testes, sítios, estabilidade, sinal, histórico",
    ),
    "wordmate": (
        "Vocabulário útil em 44 línguas",
        "O Wordmate organiza vocabulário em 44 línguas, com exemplos em frases e exercícios para praticar a utilização das palavras.\n\nReveja ao seu ritmo e continue com o widget ou o Apple Watch quando for conveniente. A edição paga inclui todas as línguas e níveis.",
        "vocabulário, línguas, palavras, frases, exemplos, exercícios, revisão, aprendizagem",
    ),
    "wordmatelite": (
        "Cinco palavras para praticar no dia",
        "O Wordmate Lite organiza pequenas sessões de vocabulário para os intervalos do dia.\n\nExplore palavras, exemplos e exercícios na experiência gratuita, depois decida se precisa dos conteúdos adicionais. A prática regular ajuda a rever; a aplicação não garante fluência.",
        "vocabulário, palavras, exemplos, exercícios, línguas, revisão, pequenas sessões, aprendizagem",
    ),
    "zipbox": (
        "Abra e organize ficheiros comprimidos",
        "O Zipbox abre arquivos ZIP, RAR, RAR5 e 7z, incluindo ficheiros protegidos por palavra-passe e arquivos divididos em várias partes.\n\nExtraia os ficheiros no dispositivo e crie arquivos ZIP ou 7z quando precisar. A palavra-passe correta e todas as partes do arquivo continuam a ser necessárias; não há promessa de recuperar ficheiros danificados.",
        "ficheiros comprimidos, descomprimir, ZIP, RAR, 7z, palavra-passe, várias partes, arquivos",
    ),
}


def language_variant(locale):
    return "en" if locale in ENGLISH_LOCALES else locale


def purchase_note(locale, model):
    if locale not in LOCALES:
        raise ValueError(f"Out-of-scope Western locale: {locale}")
    if model not in {"paid_upfront", "free_with_lifetime_unlock"}:
        raise ValueError(f"Unreviewed Western purchase model: {model}")
    return PURCHASE[language_variant(locale)][0 if model == "paid_upfront" else 1]


def identity(key, fallback):
    return IDENTITIES.get(key, fallback)


AIM_COPY = {
    "en": (
        "Daily listening and reading practice",
        "Aim990 supports TOEIC preparation with listening and reading exercises, work on weaker topics and progress review.\n\nPractise responding within the available time. No score or result within a fixed period is guaranteed. TOEIC is a trademark of ETS; Aim990 is not an official ETS product.",
        "TOEIC preparation, English, listening, reading, practice, review, timing, progress",
    ),
    "fr-CA": (
        "Pratique quotidienne de l'écoute et de la lecture",
        "Aim990 accompagne la préparation au TOEIC avec des exercices d'écoute et de lecture, du travail sur les points faibles et un suivi des progrès.\n\nExercez-vous à répondre dans le temps disponible. Aucun score ni résultat dans un délai précis n'est garanti. TOEIC est une marque d'ETS; Aim990 n'est pas un produit officiel d'ETS.",
        "préparation TOEIC, anglais, écoute, lecture, exercices, révision, temps de réponse, progrès",
    ),
    "fr-FR": (
        "Pratique quotidienne de l'écoute et de la lecture",
        "Aim990 accompagne la préparation au TOEIC avec des exercices de compréhension orale et écrite, un travail ciblé sur les points faibles et un suivi des progrès.\n\nEntraînez-vous à répondre dans le temps imparti. Aucun score ni résultat dans un délai précis n'est garanti. TOEIC est une marque d'ETS ; Aim990 n'est pas un produit officiel d'ETS.",
        "préparation TOEIC, anglais, compréhension orale, compréhension écrite, entraînement, révision, temps de réponse, progrès",
    ),
    "es-ES": (
        "Práctica diaria de comprensión oral y escrita",
        "Aim990 ayuda a preparar el TOEIC con ejercicios de comprensión oral y escrita, trabajo en los puntos débiles y revisión del progreso.\n\nPractica cómo responder dentro del tiempo disponible. No se garantiza una puntuación ni un resultado en un plazo fijo. TOEIC es una marca de ETS; Aim990 no es un producto oficial de ETS.",
        "preparación TOEIC, inglés, comprensión oral, comprensión escrita, práctica, repaso, tiempo de respuesta, progreso",
    ),
    "es-MX": (
        "Práctica diaria de escucha y lectura",
        "Aim990 apoya tu preparación para el TOEIC con ejercicios de escucha y lectura, práctica de los temas difíciles y seguimiento del avance.\n\nPractica cómo responder dentro del tiempo disponible. No se garantiza una puntuación ni un resultado en un plazo fijo. TOEIC es una marca de ETS; Aim990 no es un producto oficial de ETS.",
        "preparación TOEIC, inglés, escucha, lectura, práctica, repaso, tiempo de respuesta, avance",
    ),
    "pt-BR": (
        "Prática diária de compreensão oral e escrita",
        "O Aim990 ajuda na preparação para o TOEIC com exercícios de compreensão oral e escrita, revisão dos pontos fracos e acompanhamento do progresso.\n\nPratique como responder dentro do tempo disponível. Não há garantia de pontuação nem de resultado em um prazo fixo. TOEIC é uma marca da ETS; o Aim990 não é um produto oficial da ETS.",
        "preparação TOEIC, inglês, compreensão oral, compreensão escrita, prática, revisão, tempo de resposta, progresso",
    ),
}

UNBLURRY_COPY = {
    "en": (
        "Adjust sharpness and compare the result",
        "Unblurry Pro offers photo sharpening and enhancement on your iPhone, with a preview before saving.\n\nImprovement depends on the original image. Severe blur can remain, and missing details cannot be recovered reliably. Free saving has quality and usage limits; check them before exporting.",
        "photo sharpening, blurred photos, enhancement, preview, comparison, image quality, old photos, saving",
    ),
    "fr-CA": (
        "Ajustez la netteté et comparez le résultat",
        "Unblurry Pro permet d'ajuster la netteté et d'améliorer les photos sur iPhone, avec un aperçu avant l'enregistrement.\n\nL'amélioration dépend de l'image d'origine. Un flou important peut persister et les détails absents ne peuvent pas être récupérés de façon fiable. L'enregistrement gratuit comporte des limites de qualité et d'utilisation.",
        "netteté, photos floues, amélioration photo, aperçu, comparaison, qualité d'image, anciennes photos, enregistrement",
    ),
    "fr-FR": (
        "Réglez la netteté et comparez le résultat",
        "Unblurry Pro permet d'ajuster la netteté et d'améliorer les photos sur iPhone, avec un aperçu avant l'enregistrement.\n\nL'amélioration dépend de l'image d'origine. Un flou prononcé peut persister et les détails manquants ne peuvent pas être récupérés de manière fiable. L'enregistrement gratuit comporte des limites de qualité et d'utilisation.",
        "netteté, photos floues, amélioration photo, aperçu, comparaison, qualité d'image, anciennes photos, enregistrement",
    ),
    "es-ES": (
        "Ajusta la nitidez y compara el resultado",
        "Unblurry Pro permite ajustar la nitidez y mejorar fotos en el iPhone, con una vista previa antes de guardarlas.\n\nLa mejora depende de la imagen original. Un desenfoque intenso puede persistir y los detalles ausentes no se pueden recuperar con fiabilidad. El guardado gratuito tiene límites de calidad y uso.",
        "nitidez, fotos borrosas, mejora de fotos, vista previa, comparación, calidad de imagen, fotos antiguas, guardar",
    ),
    "es-MX": (
        "Ajusta la nitidez y compara el resultado",
        "Unblurry Pro permite ajustar la nitidez y mejorar fotos en tu iPhone, con una vista previa antes de guardarlas.\n\nLa mejora depende de la imagen original. El desenfoque intenso puede continuar y los detalles que faltan no se pueden recuperar de forma confiable. El guardado gratuito tiene límites de calidad y uso.",
        "nitidez, fotos borrosas, mejorar fotos, vista previa, comparación, calidad de imagen, fotos antiguas, guardar",
    ),
    "pt-BR": (
        "Ajuste a nitidez e compare o resultado",
        "O Unblurry Pro permite ajustar a nitidez e melhorar fotos no iPhone, com prévia antes de salvar.\n\nA melhora depende da imagem original. Um desfoque intenso pode continuar, e detalhes ausentes não podem ser recuperados de forma confiável. O salvamento gratuito tem limites de qualidade e uso.",
        "nitidez, fotos desfocadas, melhorar fotos, prévia, comparação, qualidade da imagem, fotos antigas, salvar",
    ),
}

PRO_VALUE = {
    "en": {
        "lumiletterspro": "The complete Pro edition includes all 26 English letters, their sounds and letter-writing practice.",
        "lumibopomofopro": "The complete Pro edition includes all 37 Zhuyin symbols, with listening, tracing and tone practice.",
        "lumimathpro": "The complete Pro edition includes the number activities, calculation exercises and reasoning games.",
        "lumimissionpro": "The complete Pro edition includes the routines, tasks, rewards and family settings from the start.",
    },
    "fr": {
        "lumiletterspro": "L'édition Pro complète comprend les 26 lettres anglaises, leurs sons et les activités d'écriture.",
        "lumibopomofopro": "L'édition Pro complète comprend les 37 signes du zhuyin, avec écoute, tracé et pratique des tons.",
        "lumimathpro": "L'édition Pro complète comprend les activités sur les nombres, le calcul et les jeux de raisonnement.",
        "lumimissionpro": "L'édition Pro complète comprend dès le départ les routines, tâches, récompenses et réglages familiaux.",
    },
    "es": {
        "lumiletterspro": "La edición Pro completa incluye las 26 letras inglesas, sus sonidos y actividades de escritura.",
        "lumibopomofopro": "La edición Pro completa incluye los 37 símbolos zhuyin, con escucha, trazado y práctica de tonos.",
        "lumimathpro": "La edición Pro completa incluye las actividades con números, los ejercicios de cálculo y los juegos de razonamiento.",
        "lumimissionpro": "La edición Pro completa incluye desde el principio las rutinas, tareas, recompensas y ajustes familiares.",
    },
    "pt": {
        "lumiletterspro": "A edição Pro completa inclui as 26 letras inglesas, seus sons e atividades de escrita.",
        "lumibopomofopro": "A edição Pro completa inclui os 37 símbolos zhuyin, com escuta, traçado e prática de tons.",
        "lumimathpro": "A edição Pro completa inclui as atividades com números, os exercícios de cálculo e os jogos de raciocínio.",
        "lumimissionpro": "A edição Pro completa inclui desde o início as rotinas, tarefas, recompensas e configurações da família.",
    },
}

PRO_KEYS = tuple(PRO_VALUE["en"])
PRO_HEADLINES = {
    "en": ("The complete English alphabet", "All 37 Zhuyin symbols", "Complete number and reasoning activities", "All routines, tasks and rewards"),
    "fr": ("L'alphabet anglais complet", "Les 37 signes du zhuyin", "Toutes les activités de nombres et de raisonnement", "Toutes les routines, tâches et récompenses"),
    "es": ("El alfabeto inglés completo", "Los 37 símbolos zhuyin", "Todas las actividades de números y razonamiento", "Todas las rutinas, tareas y recompensas"),
    "pt": ("O alfabeto inglês completo", "Os 37 símbolos zhuyin", "Todas as atividades com números e raciocínio", "Todas as rotinas, tarefas e recompensas"),
}


def external_values(key, locale, source, app):
    values = dict(source)
    if locale not in LOCALES:
        return values
    variant = language_variant(locale)
    values["name"] = identity(key, values.get("name") or app["name"])
    row = (
        PT_PT_COPY.get(key) if locale == "pt-PT"
        else AIM_COPY.get(variant) if key == "aim990"
        else UNBLURRY_COPY.get(variant) if key == "unblurry"
        else None
    )
    if row:
        heading, body, keywords = row
        if locale == "pt-PT":
            values["name"] = identity(key, app["name"])
        if locale in {"en-US", "en-CA"}:
            body = body.replace("Practise ", "Practice ")
        values.update(
            subtitle=heading, description=body,
            promotionalText=body.split("\n\n", 1)[0], keywords=keywords,
        )
    for field in ("subtitle", "description", "promotionalText"):
        text = values.get(field, "")
        if not isinstance(text, str):
            continue
        if key == "tripplanet":
            text = text.replace("Lumi Trip Planet: World Travel", IDENTITIES[key])
            text = text.replace("Lumi Trip Planet", IDENTITIES[key])
        if key == "shotinbox":
            text = re.sub(r"US\s*\$\s*\d+(?:[.,]\d+)?\s*[·•]?\s*", "", text)
        if key == "tripplanet" and locale == "pt-BR":
            text = re.sub(r"(?i)sem\s+(?:subscriç(?:ão|ões)|assinaturas?)", "sem assinatura", text)
        values[field] = text
    if key in PRO_KEYS and locale != "pt-PT":
        pro_value = PRO_VALUE[locale.split("-")[0]][key]
        values["subtitle"] = PRO_HEADLINES[locale.split("-")[0]][PRO_KEYS.index(key)]
        values["description"] = values["name"] + ": " + pro_value
        values["promotionalText"] = pro_value
    note = purchase_note(locale, app["purchase_model"])
    if row or key in PRO_KEYS or key in {"tripplanet", "shotinbox"}:
        values["description"] += "\n\n" + note
    keywords = values.get("keywords", "")
    if isinstance(keywords, str):
        terms = keywords.split(",")
        native_terms = [
            term for term in terms
            if not any(
                character.isalpha()
                and not any(script in unicodedata.name(character, "") for script in ("LATIN", "GREEK"))
                for character in term
            )
        ]
        if len(native_terms) != len(terms):
            values["keywords"] = ",".join(native_terms)
    return values

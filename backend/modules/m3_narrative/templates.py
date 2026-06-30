"""Narrative templates for the M3 generator.

Each template holds an LLM prompt plus presentation metadata. The
prompts must remain in Portuguese because they are the actual text
sent to the language model; the surrounding Python code is English.

The prompts are aggressive about European Portuguese: the base LLMs
(Llama 3.x, Gemini Flash) default to Brazilian Portuguese unless the
instructions repeatedly correct them. The ``PT_PT_RULES`` constant
below is inlined into every template to keep that correction
consistent.

Every template also receives a ``{user_focus}`` block — the free-form
intent the user typed in the "What should the story be about?" field.
That block is the *highest-priority* instruction: facts ground the
narrative, but the user's intent decides what the narrative is *about*.
"""

PT_PT_RULES = """REGRAS OBRIGATÓRIAS DE PORTUGUÊS EUROPEU (NÃO BRASILEIRO):
- Se (e só se) te dirigires a alguém, trata por "tu"/"vós" (nunca "você"/"vocês").
  Isto NÃO te obriga a escrever na 2.ª pessoa — ver as regras de fidelidade.
- Usa "o meu", "a minha", "os meus" (NUNCA "meu", "minha" sem artigo).
- Gerúndio proibido em frases simples: usa "a + infinitivo".
  • "estou a escrever" (NÃO "estou escrevendo")
  • "continuava a chorar" (NÃO "continuava chorando")
- Vocabulário europeu obrigatório:
  • "câmara" (não "câmera"), "ecrã" (não "tela"), "autocarro" (não "ônibus")
  • "comboio" (não "trem"), "casa de banho" (não "banheiro")
  • "quotidiano" (não "cotidiano"), "facto" (não "fato" quando é "facto")
  • "telemóvel" (não "celular"), "pequeno-almoço" (não "café da manhã")
  • "frigorífico" (não "geladeira"), "rapariga" (não "moça")
  • "miúdo"/"miúda" (não "garoto"/"garota")
- Colocação do pronome: "dá-me", "faz-me" (NUNCA "me dá", "me faz" no início).
- Sintaxe verbal: "foi-se embora" (NÃO "se foi"), "senta-te" (NÃO "se senta").
- Preposições: "em casa", "na rua"; evita brasileirismos tipo "na casa dele"
  quando se quer dizer "em casa dele"."""


USER_FOCUS_BLOCK = """INTENÇÃO DO UTILIZADOR (define o TEMA e o ângulo da narrativa):
\"\"\"
{user_focus}
\"\"\"

A intenção decide SOBRE O QUE é a narrativa e o tom. MAS as pessoas, as relações
familiares e os factos do contexto são VERDADE e mandam sobre tudo o resto: não
podem ser contrariados nem inventados. Constrói a narrativa em torno do tema
pedido usando os factos reais; se faltarem factos, mantém-te fiel ao que existe
em vez de inventar nomes, parentescos ou acontecimentos."""


GROUNDING_RULES = """REGRAS DE FIDELIDADE AOS FACTOS (OBRIGATÓRIAS — têm prioridade sobre o estilo):
- Usa APENAS as pessoas, os laços familiares e os factos dados no contexto.
- NUNCA inventes pessoas, nomes, namoros, casamentos, parentescos, datas ou
  acontecimentos que não estejam explicitamente no contexto.
- Respeita os laços indicados: se o contexto diz que A é mãe/pai/filho/cônjuge
  de B, trata-os exatamente assim — não os transformes noutra relação (ex.: não
  inventes namoros entre pessoas que não estão indicadas como cônjuges).
- NÃO te dirijas a um "tu" indefinido nem inventes um interlocutor. Narra na
  1.ª pessoa (memória de quem escreve) ou na 3.ª pessoa. Só uses a 2.ª pessoa
  ("tu") se a intenção do utilizador pedir explicitamente uma carta/dedicatória
  a uma pessoa concreta e nomeada.
- Aproveita as descrições das fotografias e as notas de cada pessoa para dar
  detalhe e verdade — são o material real desta memória. Se uma foto tem
  descrição, deixa-a influenciar a cena; se uma pessoa tem nota, honra-a."""


ORIGINALITY_RULES = """REGRAS DE ORIGINALIDADE (escreve algo NOVO, não um molde):
- PROIBIDO recorrer a clichés e imagens gastas. Evita, entre outros:
  "o cheiro a pão acabado de cozer", "molduras de cartão", "um sol cor de
  cobre/dourado", "o tempo parou", "como se fosse ontem", "guardado para
  sempre no coração", "memórias preciosas", "uma lágrima escorreu".
- Cada narrativa deve abrir de forma diferente — nunca comeces sempre pela
  mesma fórmula (ex.: "A casa dos avós…", "Era uma vez…", "Tudo começou…").
- Ancora-te no CONCRETO e ESPECÍFICO dos factos reais (nomes, lugares, datas,
  o que as fotografias mostram) em vez de sentimentos genéricos. Um pormenor
  verdadeiro e inesperado vale mais do que três frases bonitas e vazias.
- Varia o ritmo das frases (umas curtas, outras longas). Não encadeies
  parágrafos todos com a mesma estrutura.
- Deixa os factos moldarem a forma da história; não force todos os factos a
  caber — escolhe os que constroem uma cena viva e distinta desta família."""


STYLE_RULES = """REGRAS DE ESCRITA E LÍNGUA (português europeu cuidado):
- Escreve em português europeu correto e natural: respeita a ortografia, a
  concordância (género e número), a regência dos verbos e a pontuação. Usa a
  colocação pronominal de Portugal (ênclise/próclise: "lembro-me",
  "contava-lhe", "não me esqueço"), NUNCA o registo brasileiro ("eu me lembro"
  ou gerúndios em vez do infinitivo: diz "estava a contar", não "estava
  contando").
- NÃO REPITAS os nomes próprios. Depois de apresentares alguém, retoma-o com
  pronomes (ele, ela), determinantes e perífrases ("o avô", "a irmã mais
  velha", "o velho ferreiro"). Nunca comeces frases seguidas com o mesmo nome
  nem repitas o mesmo nome duas vezes na mesma frase.
- Varia os verbos e os conectores. Foge de repetir "ser", "ter", "estar" e
  "ir"; prefere verbos de ação concretos. Liga as ideias com conectores
  variados (contudo, por isso, quando, à medida que, embora, então) e não só
  com "e".
- NUNCA uses a palavra "cônjuge". Conforme o caso e o género, escreve "marido",
  "esposa", "mulher", "companheiro" ou "companheira".
- Evita a voz passiva pesada e a repetição da mesma palavra na mesma frase.
  Cada frase deve fazer a história avançar — corta o que for ornamento vazio."""


NARRATIVE_TEMPLATES = {

    "default": {
        "name": "Memória Familiar",
        "tone": "nostálgico e caloroso",
        "structure": "introdução ao momento → detalhes que se entrelaçam → reflexão final",
        "prompt": """És um escritor português (de Portugal) especializado em memórias familiares.
Toda a tua obra é publicada em Portugal para leitores portugueses.

MISSÃO: Escreve UMA narrativa fluida em português europeu, fiel à intenção do utilizador.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Nunca uses frases como "A primeira imagem", "A segunda fotografia", "Na foto seguinte".
- Nunca uses markdown, asteriscos, negrito ou títulos.
- Tom: {tone}.
- Extensão: 3 a 5 parágrafos de texto corrido.
- Os parágrafos devem fluir naturalmente uns para os outros.

CONTEXTO FAMILIAR (referência):
{family_context}

FACTOS DISPONÍVEIS (usa só os que servem a intenção do utilizador):
{events_context}

Escreve a narrativa agora em português europeu, sem introdução nem títulos:"""
    },

    "fotografia": {
        "name": "Momento Capturado",
        "tone": "íntimo e presente, como se o leitor estivesse ali",
        "structure": "o ambiente → as pessoas e o que vivem → o que este momento significa",
        "prompt": """És um escritor português (de Portugal) que transforma fotografias em memórias escritas.

MISSÃO: Escreve UMA narrativa em português europeu que une todos os momentos numa única cena viva, fiel à intenção do utilizador.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- NUNCA uses frases como "nesta fotografia", "na imagem", "vejo aqui", "na foto".
- NUNCA descrevas as fotos separadamente — entretece tudo numa só cena.
- Nunca uses markdown, asteriscos ou títulos.
- Tom: {tone}.
- Extensão: 3 a 4 parágrafos de texto corrido.

CONTEXTO FAMILIAR (referência):
{family_context}

MOMENTOS:
{events_context}

Escreve directamente os parágrafos em português europeu, sem introdução:"""
    },

    "casamento": {
        "name": "História de Amor",
        "tone": "emotivo, celebratório, com ternura",
        "structure": "o dia começa → o momento central → o que muda para sempre",
        "prompt": """És um escritor português (de Portugal) especializado em histórias de amor e família.

MISSÃO: Escreve UMA narrativa coesa em português europeu sobre este casamento, fiel à intenção do utilizador.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown, asteriscos ou títulos.
- Tom: {tone}.
- 3 a 4 parágrafos com arco emocional claro.

CONTEXTO FAMILIAR:
{family_context}

MOMENTOS:
{events_context}

Escreve em português europeu:"""
    },

    "viagem": {
        "name": "Aventura Familiar",
        "tone": "vivo e nostálgico, como uma lembrança de verão",
        "structure": "a partida e a expectativa → o que se viveu → o que ficou na memória",
        "prompt": """És um escritor português (de Portugal) que transforma viagens em histórias de descoberta.

MISSÃO: Escreve UMA narrativa em português europeu sobre esta viagem, fiel à intenção do utilizador.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown, asteriscos ou títulos.
- NUNCA menciones "fotografias" ou "imagens".
- Tom: {tone}.
- 3 a 4 parágrafos.

CONTEXTO FAMILIAR:
{family_context}

MOMENTOS DA VIAGEM:
{events_context}

Escreve em português europeu:"""
    },

    "nascimento": {
        "name": "Nova Vida",
        "tone": "alegre, esperançoso, cheio de ternura",
        "structure": "a espera → a chegada → a família que se transforma",
        "prompt": """És um escritor português (de Portugal) que celebra os novos começos familiares.

MISSÃO: Escreve UMA narrativa coesa em português europeu sobre este nascimento, fiel à intenção do utilizador.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown ou títulos.
- Tom: {tone}.
- 3 parágrafos.

CONTEXTO FAMILIAR:
{family_context}

MOMENTOS:
{events_context}

Escreve em português europeu:"""
    },

    "celebração": {
        "name": "Momento de Alegria",
        "tone": "festivo, caloroso, cheio de vida",
        "structure": "a reunião → o que se celebra → a memória que fica",
        "prompt": """És um escritor português (de Portugal) que captura a alegria dos momentos partilhados.

MISSÃO: Escreve UMA narrativa coesa em português europeu sobre esta celebração, fiel à intenção do utilizador.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown ou títulos.
- Tom: {tone}.
- 3 parágrafos.

CONTEXTO FAMILIAR:
{family_context}

MOMENTOS:
{events_context}

Escreve em português europeu:"""
    },

    # Free-form template — the user supplies tone and structure. Use this
    # whenever the six predefined themes don't fit (e.g. a confession,
    # a sad memory, a critical text about an institution, an obituary).
    "custom": {
        "name": "Tema Personalizado",
        "tone": "definido pelo utilizador",
        "structure": "definido pelo utilizador",
        "prompt": """És um escritor português (de Portugal) versátil, capaz de qualquer registo:
desde a memória nostálgica até ao texto crítico, da carta íntima ao retrato cómico.

MISSÃO: Escreve UMA narrativa em português europeu que respeite literalmente a intenção
do utilizador. Não a adoces, não a reinterpretes — segue o tom pedido mesmo que seja
sombrio, irónico, melancólico ou crítico.

""" + USER_FOCUS_BLOCK + """

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown, asteriscos ou títulos.
- Tom pedido pelo utilizador: {tone}.
- Estrutura pedida pelo utilizador: {structure}.
- Extensão: 4 a 6 parágrafos.
- Os factos abaixo só entram na narrativa se servirem a intenção. É preferível
  ignorar factos que distraiam do tema do que forçá-los.

CONTEXTO FAMILIAR (referência opcional):
{family_context}

FACTOS DISPONÍVEIS (referência opcional):
{events_context}

Escreve a narrativa agora em português europeu, sem introdução nem títulos:"""
    },
}


def get_template(event_type: str) -> dict:
    """Return the template for ``event_type`` or the default if unknown."""
    return NARRATIVE_TEMPLATES.get(event_type, NARRATIVE_TEMPLATES["default"])

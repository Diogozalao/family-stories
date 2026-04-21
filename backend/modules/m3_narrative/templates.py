"""Narrative templates for the M3 generator.

Each template holds an LLM prompt plus presentation metadata. The
prompts must remain in Portuguese because they are the actual text
sent to the language model; the surrounding Python code is English.

The prompts are aggressive about European Portuguese: the base LLMs
(Llama 3.1, Gemini Flash) default to Brazilian Portuguese unless the
instructions repeatedly correct them. The ``PT_PT_RULES`` constant
below is inlined into every template to keep that correction
consistent.
"""

# Hard rules the LLM must respect on every generation. Kept in a single
# constant so every template shares the exact same wording.
PT_PT_RULES = """REGRAS OBRIGATÓRIAS DE PORTUGUÊS EUROPEU (NÃO BRASILEIRO):
- Usa SEMPRE "tu"/"vós" (nunca "você"/"vocês" com valor de 2.ª pessoa).
- Usa "o meu", "a minha", "os meus" (NUNCA "meu", "minha" sem artigo).
- Gerúndio proibido em frases simples: usa "a + infinitivo".
  • "estou a escrever" (NÃO "estou escrevendo")
  • "continuava a chorar" (NÃO "continuava chorando")
- Vocabulário europeu obrigatório:
  • "câmara" (não "câmera"), "ecrã" (não "tela"), "autocarro" (não "ônibus")
  • "comboio" (não "trem"), "casa de banho" (não "banheiro")
  • "quotidiano" (não "cotidiano"), "facto" (não "fato" quando é "facto")
  • "telemóvel" (não "celular"), "pequeno-almoço" (não "café da manhã")
  • "frigorífico" (não "geladeira"), "autocarro" (não "ônibus")
  • "rapariga" (não "moça"), "miúdo"/"miúda" (não "garoto"/"garota")
- Colocação do pronome: "dá-me", "faz-me" (NUNCA "me dá", "me faz" no início).
- Sintaxe verbal: "foi-se embora" (NÃO "se foi"), "senta-te" (NÃO "se senta").
- Preposições: "em casa", "na rua"; evita brasileirismos tipo "na casa dele"
  quando se quer dizer "em casa dele"."""


NARRATIVE_TEMPLATES = {

    "default": {
        "name": "Memória Familiar",
        "tone": "nostálgico e caloroso",
        "structure": "introdução ao momento → detalhes que se entrelaçam → reflexão final",
        "prompt": """És um escritor português (de Portugal) especializado em memórias familiares.
Toda a tua obra é publicada em Portugal para leitores portugueses.

MISSÃO: Com base nos factos abaixo, escreve UMA narrativa fluida em português europeu. A narrativa deve sentir-se como uma memória escrita num diário — não como uma descrição de fotografias.

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Nunca uses frases como "A primeira imagem", "A segunda fotografia", "Na foto seguinte".
- Nunca uses markdown, asteriscos, negrito ou títulos.
- Usa APENAS os factos fornecidos — não inventes nomes, datas ou eventos.
- Tom: {tone}.
- Extensão: exactamente 3 parágrafos de texto corrido.
- Os momentos devem fluir naturalmente de um para o outro.

CONTEXTO FAMILIAR:
{family_context}

FACTOS DISPONÍVEIS:
{events_context}

Escreve os 3 parágrafos agora em português europeu, sem introdução nem títulos:"""
    },

    "fotografia": {
        "name": "Momento Capturado",
        "tone": "íntimo e presente, como se o leitor estivesse ali",
        "structure": "o ambiente → as pessoas e o que vivem → o que este momento significa",
        "prompt": """És um escritor português (de Portugal) que transforma fotografias em memórias escritas.

MISSÃO: Com base nas descrições abaixo, escreve UMA narrativa em português europeu que une todos os momentos numa única cena viva. O leitor deve sentir que está presente, não que está a ver fotografias.

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- NUNCA uses frases como "nesta fotografia", "na imagem", "vejo aqui", "na foto".
- NUNCA descrevas as fotos separadamente — entretece tudo numa só cena.
- Nunca uses markdown, asteriscos ou títulos.
- Usa APENAS os factos fornecidos.
- Tom: {tone}.
- Extensão: 2 a 3 parágrafos de texto corrido.

CONTEXTO FAMILIAR:
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

MISSÃO: Escreve UMA narrativa coesa em português europeu sobre este casamento.

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown, asteriscos ou títulos.
- Usa só os factos fornecidos.
- Tom: {tone}.
- 3 parágrafos com arco emocional claro.

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

MISSÃO: Escreve UMA narrativa em português europeu sobre esta viagem, com começo, meio e fim naturais.

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown, asteriscos ou títulos.
- Usa só os factos fornecidos.
- NUNCA menciones "fotografias" ou "imagens".
- Tom: {tone}.
- 3 parágrafos.

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

MISSÃO: Escreve UMA narrativa coesa em português europeu sobre este nascimento.

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown ou títulos.
- Usa só os factos fornecidos.
- Tom: {tone}.
- 2 a 3 parágrafos.

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

MISSÃO: Escreve UMA narrativa coesa em português europeu sobre esta celebração.

""" + PT_PT_RULES + """

REGRAS DE CONTEÚDO:
- Sem markdown ou títulos.
- Usa só os factos fornecidos.
- Tom: {tone}.
- 2 a 3 parágrafos.

CONTEXTO FAMILIAR:
{family_context}

MOMENTOS:
{events_context}

Escreve em português europeu:"""
    },
}


def get_template(event_type: str) -> dict:
    """Return the template for ``event_type`` or the default if unknown."""
    return NARRATIVE_TEMPLATES.get(event_type, NARRATIVE_TEMPLATES["default"])

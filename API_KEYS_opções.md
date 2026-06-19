# Opções de API Keys / LLMs — alternativas ao Gemini pago

> **Para quê serve este ficheiro:** lista de fornecedores de modelos de IA que podem
> gerar as narrativas (e analisar fotos) do *Family Stories*, caso não queiras usar o
> Gemini pago. Inclui limites grátis, preços se quiseres pagar, e o que muda no código.
>
> ⚠️ **Aviso honesto sobre preços:** os preços e limites grátis **mudam com frequência**.
> Só os do **Claude/Anthropic** estão confirmados pela documentação oficial (data abaixo).
> Os restantes são **ordens de grandeza** — confirma sempre na página oficial antes de
> meteres um número no relatório.
>
> *Última revisão: 2026-06-19*

---

## 0. Conceito-chave (ler primeiro)

Há dois mundos completamente diferentes:

| | Onde corre | Precisa de chave? | Custo | Exemplos |
|---|---|---|---|---|
| **Modelos abertos (local)** | No teu PC / servidor | ❌ Não | Grátis (paga o teu hardware) | Llama, Mistral, Gemma, Qwen (via **Ollama**) |
| **Modelos fechados (nuvem)** | Servidores do fornecedor | ✅ Sim (API key) | Pago / free tier limitado | Gemini, GPT (ChatGPT), Claude |

➡️ **"Claude/GPT/Gemini grátis em local" não existe** — são todos fechados, só na nuvem.
O único caminho 100% grátis e local é o **Ollama com modelos abertos**.

⚠️ **Importante para o teu projeto:** em **produção (Render)** não há Ollama, por isso
*online* dependes sempre de um fornecedor de nuvem (com chave). O Ollama só te serve em
**desenvolvimento local**.

---

## 1. O teu projeto precisa de DUAS coisas

1. **Geração de texto** (M3 — narrativas) → qualquer LLM serve.
2. **Visão / análise de imagens** (M1 — descrever fotos) → o modelo tem de aceitar **imagens**.

Na tabela abaixo, a coluna **Visão** diz se o fornecedor cobre o ponto 2.
Se um fornecedor não tiver visão, podias usá-lo só para texto e manter o Gemini só para as fotos.

---

## 2. Comparação dos fornecedores

### 🟢 Ollama (local) — **o que o teu código já usa**
- **Tipo:** modelos abertos, no teu PC.
- **Chave:** não precisa.
- **Limite grátis:** ilimitado (limitado só pelo teu hardware).
- **Custo se pagares:** € 0. (O "Ollama Cloud" para modelos grandes tem chave + tier grátis, depois pago.)
- **Visão:** sim, com modelos como `llama3.2-vision` ou `llava`.
- **Modelos típicos:** `llama3.2:3b` (o teu), `mistral`, `gemma2`, `qwen2.5`.
- **Muda no código?** Não — já está integrado como motor principal.
- **Quando usar:** desenvolvimento local. **Não serve para o site online.**

### 🔵 Google Gemini — **o que usas em produção**
- **Tipo:** nuvem, fechado.
- **Limite grátis:** ~20 pedidos/dia no `2.5-flash` (free tier atual — muito baixo).
- **Custo se pagares:** modelos `flash` são **baratíssimos** (frações de cêntimo por narrativa).
- **Visão:** ✅ sim (já a usas no M1).
- **Crédito de boas-vindas:** 300 USD / 90 dias no Google Cloud.
- **Muda no código?** Não — já está integrado.
- **Quando usar:** produção. É o teu motor online atual.

### 🟣 Anthropic — Claude *(preços CONFIRMados, data 2026-06-04)*
- **Tipo:** nuvem, fechado.
- **Chave:** `console.anthropic.com` (key começa por `sk-ant-...`).
- **Limite grátis:** sem free tier perpétuo; apenas uns dólares de crédito ao criar conta.
- **Custo se pagares (por 1 milhão de tokens):**

  | Modelo | Input | Output |
  |---|---|---|
  | Claude Haiku 4.5 (mais barato) | $1 | $5 |
  | Claude Sonnet 4.6 | $3 | $15 |
  | Claude Opus 4.8 (topo) | $5 | $25 |

- **Visão:** ✅ sim (todos os modelos Claude aceitam imagens).
- **Muda no código?** Sim — `llm_client.py` está feito para o Gemini; usar Claude exige
  instalar `anthropic` e reescrever a chamada. Não compensa só por isto.
- **Quando usar:** se quisesses a melhor qualidade de escrita. Para uma tese, **não compensa** trocar.


### 🟠 OpenAI — ChatGPT / GPT
- **Tipo:** nuvem, fechado.
- **Chave:** `platform.openai.com` (key começa por `sk-...`).
- **Limite grátis:** sem free tier perpétuo; só créditos iniciais ao registar.
- **Custo se pagares:** os modelos `mini` (ex.: `gpt-*-mini`) são baratos, na mesma ordem dos flash/Haiku;
  os modelos "grandes" são bastante mais caros. *(Confirma os preços atuais — mudam muito.)*
- **Visão:** ✅ sim (modelos multimodais).
- **Muda no código?** Sim — biblioteca `openai`, reescrever a chamada.
- **Quando usar:** alternativa popular ao Gemini, mas sem vantagem clara para o teu caso.


### 🟡 Groq — **rápido e com bom free tier**
- **Tipo:** nuvem, corre modelos **abertos** (Llama, Mixtral) mas a altíssima velocidade.
- **Chave:** `console.groq.com` (key `gsk_...`).
- **Limite grátis:** **generoso** (vários milhares de pedidos/dia, varia por modelo). Bom para testes.
- **Custo se pagares:** barato.
- **Visão:** parcial (alguns modelos de visão). Confirma.
- **Muda no código?** Sim, mas a API é compatível com o formato OpenAI → fácil.
- **Quando usar:** ótima alternativa **grátis** para texto, se o free tier do Gemini não chegar.


### 🔴 OpenRouter — **um gateway para TODOS**
- **Tipo:** "porta única" — uma chave dá acesso a Gemini, Claude, GPT, Llama, etc.
- **Chave:** `openrouter.ai` (key `sk-or-...`).
- **Limite grátis:** alguns modelos **gratuitos** (ex.: variantes `:free`) com limites; os bons são pagos.
- **Custo se pagares:** pagas o preço do modelo escolhido + pequena margem.
- **Visão:** depende do modelo escolhido.
- **Muda no código?** Sim, mas formato compatível com OpenAI → fácil; e podes trocar de modelo sem mudar de chave.
- **Quando usar:** se quiseres **experimentar vários modelos** sem abrir conta em cada um.
  ⚠️ Provavelmente é isto que a colega está a usar com o "Claude do Ollama".


### 🟤 Mistral AI
- **Tipo:** nuvem, modelos próprios (e abertos).
- **Chave:** `console.mistral.ai`.
- **Limite grátis:** tier gratuito com limites razoáveis.
- **Custo se pagares:** barato.
- **Visão:** alguns modelos (`pixtral`).
- **Muda no código?** Sim (biblioteca própria ou formato compatível).
- **Quando usar:** alternativa europeia, boa relação qualidade/preço.

### ⚫ DeepSeek
- **Tipo:** nuvem, modelos próprios.
- **Limite grátis:** pequeno; sobretudo pago.
- **Custo se pagares:** **dos mais baratos do mercado**.
- **Visão:** limitada.
- **Muda no código?** Sim (formato compatível com OpenAI).
- **Quando usar:** se o critério for o custo absoluto mais baixo para texto.


### ⚪ GitHub Models — **grátis para estudantes/devs**
- **Tipo:** nuvem; dá acesso a vários modelos (GPT, Llama, etc.) via conta GitHub.
- **Chave:** token do GitHub.
- **Limite grátis:** **grátis** com limites de uso (pensado para experimentação/prototipagem).
- **Custo se pagares:** para produção real encaminha para o Azure (pago).
- **Visão:** depende do modelo.
- **Muda no código?** Sim (formato compatível com OpenAI).
- **Quando usar:** ótimo para **testar de borla** com a tua conta de estudante.


### Outros a conhecer (rápido)
- **Cohere** — tier de avaliação grátis; bom em texto; visão limitada.
- **Together AI** — créditos iniciais; corre muitos modelos abertos; pago depois.
- **Hugging Face (Inference)** — tier grátis com limites; enorme catálogo de modelos abertos.

---

## 3. Resumo: o que escolher?

| Objetivo | Escolha recomendada |
|---|---|
| **Desenvolver no PC, € 0** | **Ollama** (já funciona) |
| **Site online fiável, quase grátis** | **Gemini** + crédito de 300 USD (ou pay-as-you-go, cêntimos/mês) |
| **Free tier online maior que o Gemini, sem cartão** | **Groq** ou **GitHub Models** |
| **Experimentar muitos modelos com 1 chave** | **OpenRouter** |
| **Melhor qualidade de escrita (pago)** | **Claude** (Anthropic) — mas exige mudar código |
| **Custo absoluto mais baixo (texto)** | **DeepSeek** |

---

## 4. Avisos transversais (válidos para qualquer fornecedor pago)

1. **Modelos com visão custam mais** — analisar uma foto gasta mais do que gerar texto.
2. **Põe sempre um travão** — quota diária de pedidos e/ou budget com alertas.
3. **Cada fornecedor = nova biblioteca** — exceto os "compatíveis com OpenAI", que partilham o mesmo formato (Groq, OpenRouter, GitHub Models, DeepSeek, Mistral…), o que facilita trocar.
4. **Nunca metas a chave no código** — usa sempre o `.env`. *(Ver `core/config.py`.)*
5. **Confirma os preços na fonte** antes de assumir valores no relatório.

---

## 5. Estado atual do projeto (referência)

- **Local:** Ollama (`llama3.2:3b`) como motor principal — `backend/modules/m3_narrative/llm_client.py`.
- **Produção (Render):** fallback para **Gemini** (`gemini-2.0-flash` para texto, `gemini-2.5-flash` para visão) — `backend/core/config.py`.
- **Decisão tomada:** ativar **pay-as-you-go no Gemini** (projeto `family-story`), com crédito de 300 USD a ser consumido primeiro, quota diária + budget de 5 €.

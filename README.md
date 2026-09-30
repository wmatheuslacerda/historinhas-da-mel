# 🐑 Historinhas da Mel — Shorts bíblicos automáticos

Robô que **cria e publica sozinho 4 Shorts por dia** no YouTube: historinhas bíblicas para crianças de 3 a 6 anos, contadas pela ovelhinha **Mel**.

Tudo roda de graça no **GitHub Actions**, sem depender do seu computador.

```
07:07 · 11:07 · 15:07 · 19:07 (Brasília)
   │
   ├─ 1. Escolhe a próxima história (120 no catálogo, alterna Antigo/Novo Testamento, Natal e Páscoa automáticos)
   ├─ 2. API do Claude escreve o roteiro (linguagem de hoje, fiel à Bíblia, ~50s)
   ├─ 3. ElevenLabs gera uma voz para cada personagem
   ├─ 4. Python desenha e anima os personagens (boca sincronizada, piscadas, cenários, legenda)
   ├─ 5. Música original gerada na hora (sem direitos autorais)
   └─ 6. Publica no YouTube como "feito para crianças" e salva o histórico
```

---

## ✅ Passo a passo de instalação (uma vez só, ~40 min)

### 1. Criar o canal
Crie o canal no YouTube (de preferência como **conta de marca**, para ter outras pessoas gerenciando depois). Anote o nome e troque em `config.yaml` → `canal.nome`.

### 2. Subir este projeto no GitHub
Crie um repositório **privado** (ex.: `historinhas-da-mel`) e envie estes arquivos.
> Repositório privado tem 2.000 min/mês grátis de Actions. Cada vídeo usa ~6 min → ~720 min/mês. Sobra bastante.

### 3. Chave da Anthropic (roteiros)
1. Acesse **console.anthropic.com** → *API Keys* → *Create Key*.
2. Coloque créditos (poucos dólares por mês dão conta: ~120 roteiros/mês).

### 4. Chave da ElevenLabs (vozes)
1. **elevenlabs.io** → *Profile* → *API Keys* → crie uma chave com permissão de *Text to Speech* e *Voices (read)*.
2. **Vozes brasileiras (recomendado):** na *Voice Library*, filtre por *Portuguese – Brazil*, adicione à sua conta as vozes que gostar e rode `python scripts/listar_vozes.py` para ver os IDs. Cole em `config.yaml` → `elevenlabs.vozes`.
3. **Consumo:** ~900 caracteres por vídeo × 120 vídeos = **~110 mil caracteres/mês**. Confira se o seu plano cobre. Se não cobrir, troque o modelo para `eleven_flash_v2_5` (gasta metade).

### 5. Autorizar o YouTube (Google Cloud)
1. **console.cloud.google.com** → crie um projeto → *APIs e serviços* → *Biblioteca* → ative **YouTube Data API v3**.
2. *Tela de consentimento OAuth* → tipo **Externo** → preencha nome/e-mail → em escopos adicione `youtube.upload` → adicione seu e-mail como usuário de teste.
3. ⚠️ **Muito importante:** depois, clique em **"Publicar app" (Em produção)**. Se ficar em "Teste", a autorização **expira a cada 7 dias** e o robô para de postar. (Vai aparecer um aviso "app não verificado" na hora de autorizar — é normal, clique em *Avançado → Continuar*.)
4. *Credenciais* → *Criar credencial* → **ID do cliente OAuth** → tipo **App para computador** → baixe o JSON, renomeie para `client_secret.json` e coloque em `scripts/`.
5. No seu computador:
   ```bash
   pip install google-auth-oauthlib google-api-python-client
   python scripts/autorizar_youtube.py
   ```
   Entre na conta e **escolha o canal das historinhas**. O script mostra 3 valores.

### 6. Colocar as chaves no GitHub
No repositório: **Settings → Secrets and variables → Actions → New repository secret**. Crie:

| Nome | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | chave da Anthropic |
| `ELEVENLABS_API_KEY` | chave da ElevenLabs |
| `YT_CLIENT_ID` | do passo 5 |
| `YT_CLIENT_SECRET` | do passo 5 |
| `YT_REFRESH_TOKEN` | do passo 5 |

### 7. Primeiro teste
Aba **Actions** → *Postar historinha* → **Run workflow** → desmarque "Publicar" → *Run*.
Quando terminar (~6 min), baixe o vídeo em *Artifacts* e assista. Gostou? Rode de novo com "Publicar" marcado. A partir daí ele posta sozinho 4x por dia.

### 8. ⚠️ Auditoria da API do YouTube (obrigatória para vídeos públicos)
O Google trava como **privado** todo vídeo enviado por projetos de API ainda não auditados. Enquanto a auditoria não sair, os vídeos sobem privados (o robô avisa no log).
- Peça em: *YouTube API Services – Audit and Quota Extension Form* (formulário oficial do Google, gratuito).
- Descreva: "ferramenta interna que publica animações infantis próprias no meu canal".
- Costuma levar de alguns dias a algumas semanas.

---

## 🧪 Testar no seu computador (opcional)
```bash
pip install -r requirements.txt   # precisa do ffmpeg instalado
# Sem nenhuma chave (voz robótica de teste, só para ver a animação):
python -m src.main --offline --roteiro exemplos/davi_e_golias.json
# Com as chaves no .env, gerando sem publicar:
python -m src.main --nao-postar
```

## 🎛️ Personalizar
| O que | Onde |
|---|---|
| Horários | `.github/workflows/postar.yml` (em UTC: Brasília + 3h) |
| Nome do canal, vozes, volume da música | `config.yaml` |
| Histórias disponíveis | `dados/historias.json` |
| Aparência dos personagens | `src/personagens.py` → `PRESETS` |
| Cenários | `src/cenarios.py` |
| Regras do roteirista | `src/roteiro.py` → `SISTEMA` |

## 📁 Estrutura
```
src/main.py         pipeline completo
src/roteiro.py      escolha da história + roteiro via API do Claude
src/vozes.py        ElevenLabs (com tempo de cada letra para a boca mexer)
src/personagens.py  personagens desenhados em Python (80+ prontos)
src/cenarios.py     20 cenários (campo, deserto, Egito, mar, arca, palácio, cova dos leões...)
src/video.py        animação, legendas, transições e render do MP4
src/audio.py        música original, efeitos e mixagem
estado/             histórico do que já foi postado (atualizado pelo robô)
```

## ❓ Se algo der errado
- O GitHub manda **e-mail** quando uma execução falha. Abra a execução na aba *Actions* e veja a última linha com ❌.
- `invalid_grant` no YouTube → a autorização expirou (app ficou em "Teste"). Refaça o passo 5 com o app **Em produção**.
- `quotaExceeded` → a cota diária da API acabou; volta no dia seguinte.
- Erro 401 da ElevenLabs → chave errada ou sem créditos.

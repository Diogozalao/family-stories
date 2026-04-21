# Sistema de Geração Automática de Histórias Familiares

Fluxo Básico (Sempre que alteras ficheiros)
git add .              # 1. Adiciona TODAS as alterações
git commit -m "msg"    # 2. Cria um snapshot com descrição
git push               # 3. Envia para o GitHub


Ver o que mudou antes de adicionar:
    git status             # Vê quais ficheiros foram alterados/adicionados
    git diff               # Vê o conteúdo das alterações


Adicionar apenas ficheiros específicos (em vez de git add .)
    git add backend/app.py        # Apenas um ficheiro
    git add backend/              # Toda uma pasta
    git add *.py                  # Todos os ficheiros .py



------------------------------------
rm -f ~/family-stories/family_stories.db
rm -f ~/family-stories/data/raw/photos/*


fuser -k 8000/tcp
cd ~/family-stories
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000




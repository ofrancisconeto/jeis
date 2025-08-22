from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from validate_docbr import CPF
from django.contrib import messages
from django.db.models.functions import TruncDay
from django.db.models import Count
from app.models import Logo, Comentario, VotoRegistro, BaseConhecimento
import json
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from django.db import transaction 
from .models import PerfilUsuario 
from django.db.models import Q
import openai
from django.conf import settings
import numpy as np
from numpy.linalg import norm



def landing(request):
    return render(request, 'landing.html')


def logout_view(request):
    logout(request)
    return redirect('entrar')

def entrar(request):
    if request.method == 'POST':
        login_input = request.POST.get('login', '').strip()
        senha = request.POST.get('senha')
        user = None

        if not login_input or not senha:
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'entrar.html')

        # Tenta autenticar primeiro como um username normal (para o Murilo)
        user = authenticate(request, username=login_input, password=senha)

        # Se falhar, tenta como um CPF de aluno
        if user is None:
            cpf_limpo = ''.join(filter(str.isdigit, login_input))
            if len(cpf_limpo) == 11:
                user = authenticate(request, username=cpf_limpo, password=senha)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo(a), {user.first_name or user.username}!')
            
            if user.is_staff:
                return redirect('dashboard')
            else:
                return redirect('index')
        
        messages.error(request, 'Usuário ou senha inválidos.')
        return render(request, 'entrar.html')

    return render(request, 'entrar.html')


def cadastrar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip() 
        senha = request.POST.get('senha')
        cpf_raw = request.POST.get('cpf', '').strip()
        turma = request.POST.get('turma', '').strip()

        if not all([nome, senha, cpf_raw, turma]):
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'cadastrar.html')

        cpf_limpo = ''.join(filter(str.isdigit, cpf_raw))
        if len(cpf_limpo) != 11 or not CPF().validate(cpf_limpo):
            messages.error(request, 'O CPF informado é inválido.')
            return render(request, 'cadastrar.html')

        if User.objects.filter(username=cpf_limpo).exists():
            messages.error(request, 'Este CPF já está cadastrado no sistema.')
            return render(request, 'cadastrar.html')
        
        try:
            with transaction.atomic():
                novo_usuario = User.objects.create_user(
                    username=cpf_limpo,
                    password=senha,
                    first_name=nome
                )
                PerfilUsuario.objects.create(user=novo_usuario, turma=turma)
            
            messages.success(request, 'Cadastro realizado com sucesso! Agora você pode fazer o login.')
            return redirect('entrar')

        except Exception as e:
            
            messages.error(request, 'Ocorreu um erro inesperado ao criar sua conta.')
            return render(request, 'cadastrar.html')
            
    return render(request, 'cadastrar.html')


@login_required(login_url='entrar')
def index(request):
    logos = Logo.objects.all()
    context = {
        'logos': logos,
        'active_page': 'home' 
    }
    return render(request, 'index.html', context)


def entrar_professor(request):
        if request.method == 'POST':
            login_raw = request.POST.get('login')
            senha = request.POST.get('senha')
            login_limpo = ''.join(filter(str.isdigit, login_raw))
            cpf_validator = CPF()
            if not cpf_validator.validate(login_limpo):
                messages.error(request, 'CPF ou senha inválidos.')
                return render(request, 'entrar_professor.html')
            if len(login_limpo) != 11:
                messages.error(request, 'CPF ou senha inválidos.')
                return render(request, 'entrar_professor.html')
            user = authenticate(request, username=login_limpo, password=senha)
            if user is not None and user.is_superuser:
                login(request, user)
                messages.success(request, 'Login realizado com sucesso!')
                return redirect('index')  
            messages.error(request, 'CPF ou senha inválidos.')
            return render(request, 'entrar_professor.html')
        return render(request, 'entrar_professor.html')

@login_required(login_url='entrar')
@user_passes_test(lambda u: u.is_staff, login_url='index')
def dashboard(request):
    
    # --- DADOS GERAIS PARA GRÁFICOS E TABELAS DE LOGO ---
    logos = Logo.objects.all().order_by('-votos')
    logo_titles = [logo.titulo for logo in logos]
    vote_counts = [logo.votos for logo in logos]
    total_votos_geral = sum(vote_counts)
    
    dados_tabela_logos = []
    for logo in logos:
        percentual_logo = round((logo.votos / total_votos_geral) * 100, 2) if total_votos_geral > 0 else 0
        dados_tabela_logos.append({
            'titulo': logo.titulo,
            'votos': logo.votos,
            'percentual': percentual_logo
        })

    # --- DADOS PARA OS CARDS DE INDICADORES ---
    total_alunos = User.objects.filter(is_staff=False).count()
    total_votantes = VotoRegistro.objects.values('usuario').distinct().count()
    percentual_participacao = round((total_votantes / total_alunos) * 100, 2) if total_alunos > 0 else 0
    logo_mais_votada = logos.first()
    
    # --- DADOS DE PARTICIPAÇÃO POR TURMA (OTIMIZADO) ---
    dados_por_turma = (
        PerfilUsuario.objects
        .filter(user__is_staff=False)
        .values('turma')
        .annotate(
            cadastrados=Count('user'),
            votantes=Count('user__votoregistro', distinct=True)
        )
        .order_by('turma')
    )
    for item in dados_por_turma:
        item['percentual'] = round((item['votantes'] / item['cadastrados']) * 100, 2) if item['cadastrados'] > 0 else 0

    # --- DADOS PARA O GRÁFICO DE EVOLUÇÃO ---
    votos_por_dia = (
        VotoRegistro.objects
        .annotate(dia=TruncDay('data_voto'))
        .values('dia')
        .annotate(total_votos=Count('id'))
        .order_by('dia')
    )
    datas_grafico = [item['dia'].strftime('%d/%m') for item in votos_por_dia]
    contagem_grafico = [item['total_votos'] for item in votos_por_dia]

    # --- MONTAGEM DO CONTEXTO FINAL ---
    context = {
        'active_page': 'dashboard',
        
        # Gráficos de Logo
        'logo_titles_json': json.dumps(logo_titles),
        'vote_counts_json': json.dumps(vote_counts),

        # Cards de Indicadores
        'total_alunos': total_alunos,
        'total_votantes': total_votantes,
        'percentual_participacao': percentual_participacao,
        'logo_mais_votada': logo_mais_votada,

        # Tabelas
        'dados_tabela_logos': dados_tabela_logos,
        'dados_por_turma': dados_por_turma,

        # Gráfico de Evolução
        'datas_grafico_json': json.dumps(datas_grafico),
        'contagem_grafico_json': json.dumps(contagem_grafico),
    }
    
    return render(request, 'dashboard.html', context)

@staff_member_required(login_url='index')
def adicionar(request):
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        logo = request.FILES.get('logo')

        if not logo:
            messages.error(request, 'Por favor, escolha um arquivo de logo.')
            return render(request, 'adicionar.html')

        Logo.objects.create(
            titulo=titulo,
            descricao=descricao,
            imagem=logo,
            usuario=request.user
        )
        messages.success(request, 'Logo adicionado com sucesso!')
        return redirect('index')

    return render(request, 'adicionar.html')

@staff_member_required(login_url='index')
def editar(request, logo_id):
    logo = Logo.objects.get(id=logo_id, usuario=request.user)
    if request.method == 'POST':
        logo.titulo = request.POST.get('titulo')
        logo.descricao = request.POST.get('descricao')
        logo.imagem = request.FILES.get('logo')
        logo.usuario = request.user
        logo.save()
        messages.success(request, 'Logo editado com sucesso!')
        return redirect('index')
    return render(request, 'editar.html', {'logo': logo})

@staff_member_required(login_url='index')
def deletar(request, logo_id):
    logo = Logo.objects.get(id=logo_id, usuario=request.user)
    logo.delete()
    messages.success(request, 'Logo deletado com sucesso!')
    return redirect('index')

@login_required(login_url='entrar')
def votar(request, logo_id):
    
    if VotoRegistro.objects.filter(usuario=request.user).exists():
        messages.error(request, 'Você já registrou seu voto e não pode votar novamente.')
        return redirect('index')
    
    logo = Logo.objects.get(id=logo_id)
    
    
    VotoRegistro.objects.create(usuario=request.user, logo=logo)
    
    # 2. Incrementa o contador de votos na logo
    logo.votos += 1
    logo.save()
    
    messages.success(request, 'Seu voto foi registrado com sucesso!')
    return redirect('index')




# 1. Crie uma função auxiliar para a lógica de data
def calcular_tempo_relativo(data):
    if not data:
        return ""

    now = timezone.now()
    diff = now - data

    if diff < timedelta(days=7):
        if diff < timedelta(minutes=1):
            return "agora mesmo"
        elif diff < timedelta(hours=1):
            minutos = int(diff.total_seconds() / 60)
            return f"há {minutos} minuto{'s' if minutos > 1 else ''}"
        elif diff < timedelta(days=1):
            horas = int(diff.total_seconds() / 3600)
            return f"há {horas} hora{'s' if horas > 1 else ''}"
        else:
            dias = diff.days
            return f"há {dias} dia{'s' if dias > 1 else ''}"
    else:
        # Formata como "dd de Mês"
        return data.strftime('%d de %b')


@login_required(login_url='entrar')
def ver_detalhes(request, logo_id):
    logo = Logo.objects.get(id=logo_id)
    comentarios = logo.comentarios.all()

    # 2. Itere sobre os comentários e adicione o novo atributo
    for comentario in comentarios:
        comentario.tempo_formatado = calcular_tempo_relativo(comentario.data_criacao)
    
    return render(request, 'ver_detalhes.html', {
        'logo': logo,
        'comentarios': comentarios,
        'logo_id': logo_id
    })

@login_required(login_url='entrar')
def adicionarcomentario(request, logo_id):
    if request.method == 'POST':
        comentario = request.POST.get('texto')
        Comentario.objects.create(
            comentario=comentario,
            logo_id=logo_id,
            usuario=request.user
        )
        print(f"Comentário adicionado: {comentario}")
        messages.success(request, 'Comentário adicionado com sucesso!')
        return redirect('ver_detalhes', logo_id=logo_id)
    

@staff_member_required(login_url='index')
def deletarcomentario(request, comentario_id):
    comentario = Comentario.objects.get(id=comentario_id, usuario=request.user)
    comentario.delete()
    messages.success(request, 'Comentário deletado com sucesso!')
    return redirect('ver_detalhes', logo_id=comentario.logo.id)


@login_required(login_url='entrar')
def murilao_ai(request):
    resposta_ia = None
    query = request.GET.get('q', '')

    if query:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # --- ETAPA 1: BUSCA SEMÂNTICA AVANÇADA ---
            base_conhecimento = BaseConhecimento.objects.all()
            if not base_conhecimento.exists():
                raise ValueError("A base de conhecimento está vazia.")

            perguntas_db = [item.pergunta for item in base_conhecimento]

            query_embedding_response = client.embeddings.create(input=[query], model="text-embedding-ada-002")
            query_vector = query_embedding_response.data[0].embedding

            db_embeddings_response = client.embeddings.create(input=perguntas_db, model="text-embedding-ada-002")
            db_vectors = [data.embedding for data in db_embeddings_response.data]

            similarities = np.array([np.dot(query_vector, db_vector) / (norm(query_vector) * norm(db_vector)) for db_vector in db_vectors])
            
            # --- A GRANDE MUDANÇA: PEGAR OS 3 MAIS SIMILARES ---
            # Pega os índices dos 3 mais similares, em ordem decrescente de similaridade
            indices_mais_similares = np.argsort(similarities)[-3:][::-1]
            
            contexto_faq = ""
            limite_confianca = 0.7 # Limite mais baixo, pois estamos pegando mais de um
            
            # Monta o contexto com os 3 melhores resultados que passarem do limite
            for indice in indices_mais_similares:
                if similarities[indice] > limite_confianca:
                    item_relevante = base_conhecimento[int(indice)] # Converte para int
                    contexto_faq += f"- Pergunta similar encontrada: '{item_relevante.pergunta}' -> Resposta: '{item_relevante.resposta}'\n"

            if not contexto_faq:
                contexto_faq = "Nenhuma informação diretamente relevante foi encontrada na nossa base de conhecimento."

            # --- ETAPA 2: PROMPT COM FOCO EM ANÁLISE ---
            total_votos = VotoRegistro.objects.count()
            total_alunos = User.objects.filter(is_staff=False).count()
            contexto_sistema = f"""
            - Itens da Base de Conhecimento que podem ser relevantes:
            {contexto_faq}
            - Dados gerais do evento: Já temos {total_votos} votos e {total_alunos} alunos participando.
            """
            
            prompt_final = f"""
            **Sua Persona:** Você é 'Murilão', a IA parceira da galera do JEIS. Sua personalidade é amigável e descontraída. Use emojis 🤙🔥.

            **Sua Missão:** Sua tarefa é analisar a lista de "Itens da Base de Conhecimento" que eu te forneci. O aluno fez uma pergunta, e esses são os trechos mais parecidos que eu encontrei. Você deve ler todos eles e decidir se algum deles responde à pergunta do aluno.

            **Regras de Análise:**
            1.  Se você encontrar uma resposta clara em um dos itens, use essa informação para formular uma resposta natural e amigável. Não apenas copie e cole, converse.
            2.  Se nenhum dos itens parecer realmente responder à pergunta do aluno, seja honesto e diga: "Pô, essa aí eu vou ficar te devendo! Não encontrei a resposta exata. Vou checar com a organização e te dou um toque. Fechou? 😉"
            3.  Sua única fonte de informação é o "Contexto Relevante". Não use seu conhecimento geral.

            ---
            CONTEXTO RELEVANTE (Sua fonte da verdade):
            {contexto_sistema}
            ---

            Analisando o contexto acima, responda à pergunta: "{query}"
            """

            # ETAPA 3: CHAMAR O GPT
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Aja como a persona descrita no prompt do usuário."},
                    {"role": "user", "content": prompt_final}
                ],
                max_tokens=150,
                temperature=0.7 # Um pouco de criatividade para formular a resposta
            )
            resposta_ia = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"ERRO NA API DA OPENAI: {e}")
            resposta_ia = f"🤯 Oopa! Deu um tilt aqui no meu cérebro digital. Tente perguntar de novo!"

    context = {
        'active_page': 'murilao_ai',
        'query': query,
        'resposta_ia': resposta_ia
    }
    return render(request, 'murilao_ai.html', context)

@staff_member_required(login_url='entrar')
def gerenciar_ia(request):
   
    base_conhecimento = BaseConhecimento.objects.all().order_by('pergunta')
    context = {
        'active_page': 'gerenciar_ia',
        'base_conhecimento': base_conhecimento
    }
    return render(request, 'gerenciar_ia.html', context)

@staff_member_required(login_url='entrar')
def adicionar_conhecimento(request):

    if request.method == 'POST':
        pergunta = request.POST.get('pergunta', '').strip()
        resposta = request.POST.get('resposta', '').strip()
        if pergunta and resposta:
            # Garante que a pergunta não exista antes de criar
            if not BaseConhecimento.objects.filter(pergunta__iexact=pergunta).exists():
                BaseConhecimento.objects.create(pergunta=pergunta, resposta=resposta)
                messages.success(request, 'Novo conhecimento adicionado com sucesso!')
            else:
                messages.error(request, 'Essa pergunta já existe na base de conhecimento.')
        else:
            messages.error(request, 'Pergunta e resposta não podem estar em branco.')
    return redirect('gerenciar_ia')

@staff_member_required(login_url='entrar')
def editar_conhecimento(request, id):
    """ Exibe o formulário de edição e salva as alterações. """
    item = BaseConhecimento.objects.get(id=id)
    if request.method == 'POST':
        pergunta = request.POST.get('pergunta', '').strip()
        resposta = request.POST.get('resposta', '').strip()
        
        # Verifica se já existe outra pergunta com o mesmo nome (excluindo a atual)
        if BaseConhecimento.objects.filter(pergunta__iexact=pergunta).exclude(id=id).exists():
            messages.error(request, 'Já existe outra pergunta com este mesmo texto.')
        elif pergunta and resposta:
            item.pergunta = pergunta
            item.resposta = resposta
            item.save()
            messages.success(request, 'Conhecimento atualizado com sucesso!')
            return redirect('gerenciar_ia')
        else:
            messages.error(request, 'Pergunta e resposta não podem estar em branco.')
    
    context = {'item': item, 'active_page': 'gerenciar_ia'}
    return render(request, 'editar_conhecimento.html', context)

@staff_member_required(login_url='entrar')
def deletar_conhecimento(request, id):
    """ Deleta um item da base de conhecimento. """
    if request.method == 'POST': # Garante que a deleção seja feita via POST por segurança
        item = BaseConhecimento.objects.get(id=id)
        item.delete()
        messages.success(request, 'Conhecimento deletado com sucesso!')
    return redirect('gerenciar_ia')

def is_superuser(user):
    return user.is_superuser

def cadastrar_professor(request):
    if request.method == 'POST':
        # 1. Coletar dados do formulário
        nome = request.POST.get('nome')
        senha = request.POST.get('senha')
        cpf_formatado = request.POST.get('username') # O campo se chama 'username' no HTML

        # 2. Validações
        if not all([nome, senha, cpf_formatado]):
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'cadastrar_professor.html')

        # CORREÇÃO CRÍTICA: Limpar o CPF para remover pontos e traço
        cpf_limpo = ''.join(filter(str.isdigit, cpf_formatado))

        # Validação para garantir que o CPF tem 11 dígitos após a limpeza
        if len(cpf_limpo) != 11:
            messages.error(request, 'O CPF informado é inválido. Ele deve conter 11 dígitos.')
            return render(request, 'cadastrar_professor.html')

        # Agora, a verificação usa o CPF limpo
        if User.objects.filter(username=cpf_limpo).exists():
            messages.error(request, 'Este CPF já está cadastrado no sistema.')
            return render(request, 'cadastrar_professor.html')
        
        
        with transaction.atomic():
        # Criamos o usuário com o CPF limpo como username
            novo_professor = User.objects.create_user(
                username=cpf_limpo,
                password=senha,
                first_name=nome
            )
                
            # Definimos como "staff" para diferenciar de alunos normais
            # Isso é útil para futuras verificações de permissão
            novo_professor.is_staff = True
            novo_professor.save()
                
            return redirect('entrar')

        
    # Se a requisição for GET, apenas renderiza a página
    return render(request, 'cadastrar_professor.html')
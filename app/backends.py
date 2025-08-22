from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class CPFAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        # Tenta encontrar um usuário cujo username seja o input (para professores)
        # OU cujo username seja o input limpo como CPF (para alunos)
        try:
            # Limpa o input para o caso de ser um CPF
            cpf_limpo = ''.join(filter(str.isdigit, username))
            
            # Busca por um usuário que corresponda a qualquer um dos critérios
            user = UserModel.objects.get(Q(username__iexact=username) | Q(username__iexact=cpf_limpo))
            
            # Se encontrou um usuário, verifica a senha
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            # Se não encontrou nenhum usuário, retorna None
            return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
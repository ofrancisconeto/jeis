from django.db import models
import os
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_save, pre_delete
from django.contrib.auth.models import User

# --- MODELO CORRETO PARA ARMAZENAR DADOS DO ALUNO ---
class PerfilUsuario(models.Model):
    # Relação um-para-um: cada usuário terá um perfil.
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Campo para armazenar a turma do aluno, como você precisa.
    turma = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} - {self.turma}'




# --- MODELO LOGO (CORRIGIDO SEM O CAMPO "turma") ---
class Logo(models.Model):
    titulo = models.CharField(max_length=200, unique=True)
    descricao = models.TextField()
    imagem = models.ImageField(upload_to='')
    votos = models.IntegerField(default=0)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE) # unique=True foi removido para um admin poder cadastrar mais de uma logo
    
    # 👇 COMENTE OU DELETE ESTA LINHA 👇
    # votantes = models.ManyToManyField(User, related_name='votantes', blank=True)
    
# --- O RESTO DOS SEUS MODELOS (sem alteração) ---
class Comentario(models.Model):
    comentario = models.TextField()
    logo = models.ForeignKey(Logo, on_delete=models.CASCADE, related_name='comentarios')
    data_criacao = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

@receiver(pre_save, sender=Logo)
def atualizar_foto(sender, instance, **kwargs):
    if instance.pk:
        try:
            logo_antiga = Logo.objects.get(pk=instance.pk)
            if logo_antiga.imagem != instance.imagem:
                caminho = os.path.join(settings.MEDIA_ROOT, str(logo_antiga.imagem))
                if os.path.exists(caminho):
                    os.remove(caminho)
        except Logo.DoesNotExist:
            pass
        
class VotoRegistro(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    logo = models.ForeignKey(Logo, on_delete=models.CASCADE)
    data_voto = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Garante que um usuário só pode votar uma vez em uma logo
        # (na verdade, em qualquer logo, como vamos controlar na view)
        unique_together = ('usuario', 'logo')
        
class BaseConhecimento(models.Model):
    pergunta = models.CharField(max_length=255, unique=True)
    resposta = models.TextField()

    def __str__(self):
        return self.pergunta

    class Meta:
        verbose_name = "Base de Conhecimento"
        verbose_name_plural = "Bases de Conhecimento"

@receiver(pre_delete, sender=Logo)
def deletar_foto(sender, instance, **kwargs):
    if instance.imagem:
        caminho = os.path.join(settings.MEDIA_ROOT, str(instance.imagem))
        if os.path.exists(caminho):
            os.remove(caminho)
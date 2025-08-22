from django.contrib import admin
from app.models import Logo, Comentario, VotoRegistro, BaseConhecimento, PerfilUsuario
# Register your models here.
admin.site.register(Logo)
admin.site.register(PerfilUsuario)
admin.site.register(Comentario)
admin.site.register(VotoRegistro)

@admin.register(BaseConhecimento)
class BaseConhecimentoAdmin(admin.ModelAdmin):
    list_display = ('pergunta', 'resposta')
    search_fields = ('pergunta', 'resposta')
"""
URL configuration for setup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app.views import landing, murilao_ai, entrar, dashboard,cadastrar, index, adicionar, editar, deletar, logout_view, votar, entrar_professor, ver_detalhes, deletarcomentario, adicionarcomentario, adicionar_conhecimento, editar_conhecimento, deletar_conhecimento, gerenciar_ia, cadastrar_professor


from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name='landing'),
    path('entrar/', entrar, name='entrar'),
    path('cadastrar/', cadastrar, name='cadastrar'),
    path('index/', index, name='index'),
    path('dashboard/', dashboard, name='dashboard'),
    path('adicionar/', adicionar, name='adicionar'),
    path('editar/<int:logo_id>/', editar, name='editar'),
    path('deletar/<int:logo_id>/', deletar, name='deletar'),
    path('votar/<int:logo_id>/', votar, name='votar'),
    path('entrar_professor/', entrar_professor, name='entrar_professor'),
    path('sair/', logout_view, name='sair'),
    path('detalhes/<int:logo_id>/', ver_detalhes, name='ver_detalhes'),
    path('deletarcomentario/<int:comentario_id>/', deletarcomentario, name='deletarcomentario'),
    path('adicionarcomentario/<int:logo_id>/', adicionarcomentario, name='adicionarcomentario'),
    path('murilao-ai/', murilao_ai, name='murilao_ai'),
    path('gerenciar-ia/', gerenciar_ia, name='gerenciar_ia'),
    path('gerenciar-ia/adicionar/', adicionar_conhecimento, name='adicionar_conhecimento'),
    path('gerenciar-ia/editar/<int:id>/', editar_conhecimento, name='editar_conhecimento'),
    path('gerenciar-ia/deletar/<int:id>/', deletar_conhecimento, name='deletar_conhecimento'),
    path('cadastrar_professor/', cadastrar_professor, name='cadastrar_professor')
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""tiptoe URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import re_path, include
from django.contrib import admin
from questionnaire.views import *
from rest_framework import routers
from rest_framework.authtoken import views

from django.contrib.staticfiles.views import serve
from django.views.generic import RedirectView 

from django.conf import settings
from django.conf.urls.static import static


admin.autodiscover()

router = routers.DefaultRouter()
router.register(r'categories', CategoryList)
router.register(r'questions/(?P<category>[0-9]+)', QuestionList)
router.register(r'question', QuestionView)
router.register(r'answer', AnswerViewSet)
router.register(r'survey', SurveyView)
router.register(r'organization', OrganizationView)
router.register(r'user', UserView, basename='user')
router.register(r'definitions', DefinitionList, basename='d')
#router.register(r'stats', StatView, basename='s')
router.register(r'completion', CompletionView, basename='cv')

urlpatterns = [
    re_path(r'^api/', include(router.urls)),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^api/auth/', views.obtain_auth_token),
    re_path(r'^api/joyplot', joyplot),
    re_path(r'^api/tmd_stats', tmd_stats),
    re_path(r'^api/tpm_stats', tpm_stats),
    re_path(r'^api/basic_stats', stats),
    re_path(r'^api/create_user/(?P<questionnaire_type>\S+)', create_web_user),
    re_path(r'^api/create_survey/', create_survey),
    re_path(r'^api/update_email', update_email),
    re_path(r'^api/retrieve_user', retrieve_user),
    re_path(r'^api/invite/', invite_to_org),
    re_path(r'^api/approve', approve_srvy),
    re_path(r'^api/token_login/', token_login),
    re_path(r'^api/stats/(?P<stat_type>\S+)', api_stat),
    re_path(r'^api/policies/(?P<speciality>\S+)', api_policy),
    re_path(r'^api/rdf/(?P<survey_id>[0-9]+)', RDFView.as_view()),
    re_path(r'^api/percent_yes/(?P<web_category>\S+)', api_percent_yes),
    re_path(r'^api/answers/(?P<web_category>\S+)', api_category_responses),
    re_path(r'^api/run_query/$', run_unique_query),
    re_path(r'^api/sample_size/', get_sample_size),
    re_path(r'^graphs/(?P<path>.*)', RedirectView.as_view(url='/static/%(path)s')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

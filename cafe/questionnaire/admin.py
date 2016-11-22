from django.contrib import admin
from django.apps import apps
from questionnaire.models import Question, Statement

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    filter_horizontal = ['options', 'depends_on']


class StatementFilter(admin.SimpleListFilter):
    title = 'Question'
    parameter_name= 'question'

    def lookups(self, request, model_admin):
        questions = set([q for q in Question.objects.all()])
        return [(q.id, q.id) for q in questions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(question__id__exact=self.value())
        else:
            return queryset


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_filter = (StatementFilter,)

# Register your models here.
app = apps.get_app_config('questionnaire')

for model_name, model in app.models.items():
    try:
        admin.site.register(model)
    except:
        pass

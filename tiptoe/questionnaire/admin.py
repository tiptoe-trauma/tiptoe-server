from django.contrib import admin
from django.apps import apps
from django import forms
from questionnaire.models import Question, Statement
from django.core.exceptions import ValidationError

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


class StatementAdminForm(forms.ModelForm):
    class Meta:
        model = Statement
        fields = '__all__'

    def validate_format(self, value):
        try:
            p, specific = value.split(':')
            print(p, specific)
        except:
            raise ValidationError(
                '{} is not formated correclty are you perhaps missing a colon or prefix?'
                .format(value))

    def clean(self):
        print('cleaned?')
        self.validate_format(self.cleaned_data['subject'])
        self.validate_format(self.cleaned_data['predicate'])
        self.validate_format(self.cleaned_data['obj'])
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(StatementAdminForm, self).__init__(*args, **kwargs)
        # This allows you to edit the options easily after a question is created
        try:
            self.fields['choice'].queryset = self.instance.question.options
        # But excepts the first time a statement is created
        except:
            pass


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_filter = (StatementFilter,)
    form = StatementAdminForm

# Register your models here.
app = apps.get_app_config('questionnaire')

for model_name, model in app.models.items():
    try:
        admin.site.register(model)
    except:
        pass

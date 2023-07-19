from questionnaire.models import *
from rest_framework import serializers
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'group', 'questionnaire')

class StatSerializer(serializers.Serializer):
    same = serializers.FloatField()

class CompletionSerializer(serializers.Serializer):
    category = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    completed_questions = serializers.IntegerField()

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('text', 'options', 'integer', 'flt', 'yesno', 'question')

class UserAnswer(serializers.ModelSerializer):
    # user request to find specific user
    pass

class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = '__all__'

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization 
        fields = '__all__'

class DefinitionSerializer(serializers.Serializer):
    word = serializers.CharField(max_length=200)
    definition = serializers.CharField(max_length=2000)

class UserSerializer(serializers.ModelSerializer):
    active_survey = serializers.SerializerMethodField('get_active')

    def get_active(self, user):
        if user.is_authenticated:
            if hasattr(user, 'activesurvey'):
                return SurveySerializer(user.activesurvey.survey).data
        return None
    class Meta:
        model = User
        fields = ('id', 'username', 'is_staff', 'email', 'active_survey')

class QuestionSerializer(serializers.ModelSerializer):
    enabled = serializers.SerializerMethodField('is_enabled')
    graph = serializers.SerializerMethodField('has_graph')
    depends_on = serializers.SerializerMethodField('get_depends')
    answer = serializers.SerializerMethodField('get_user_answer')

    def is_enabled(self, question):
        user = self.context['request'].user
        return question.enabled(user)

    def has_graph(self, question):
        s = Statement.objects.filter(question=question)
        return bool(s)

    def get_depends(self, question):
        deps = []
        for d in question.depends_on.all():
            deps.append(d.id)
        return deps

    def get_user_answer(self, question):
        user = self.context['request'].user
        if user.is_authenticated:
            try:
                answers = Answer.objects.get(question=question, survey=user.activesurvey.survey)
                serializer = AnswerSerializer(answers)
                if answers:
                    return serializer.data
            except Answer.DoesNotExist:
                return None
        return None

    class Meta:
        model = Question
        fields = ('id', 'text', 'q_type', 'options', 'answer', 'tags', 'help_text', 'enabled', 'graph', 'depends_on')
        depth = 1

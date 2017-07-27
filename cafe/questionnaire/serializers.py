from questionnaire.models import *
from rest_framework import serializers
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'group', 'questionnaire')

class StatSerializer(serializers.Serializer):
    same = serializers.FloatField()

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('text', 'options', 'integer', 'yesno', 'question')

class UserAnswer(serializers.ModelSerializer):
    # user request to find specific user
    pass

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class DefinitionSerializer(serializers.Serializer):
    word = serializers.CharField(max_length=200)
    definition = serializers.CharField(max_length=2000)

class UserSerializer(serializers.ModelSerializer):
    active_organization = serializers.SerializerMethodField('get_active')

    def get_active(self, user):
        if user.is_authenticated():
            if hasattr(user, 'activeorganization'):
                return OrganizationSerializer(user.activeorganization.organization).data
        return None
    class Meta:
        model = User
        fields = ('id', 'username', 'is_staff', 'email', 'active_organization')

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
        if user.is_authenticated():
            try:
                answers = Answer.objects.get(question=question, organization=user.activeorganization.organization)
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

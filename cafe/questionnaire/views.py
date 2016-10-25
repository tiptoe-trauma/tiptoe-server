from questionnaire.models import *
from questionnaire.serializers import *
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework import permissions
from questionnaire.rdf import get_definitions, run_statements, delete_context


# Create your views here.
class DefinitionList(viewsets.ViewSet):
    def list(self, request):
        words = get_definitions()
        if words:
            serializer = DefinitionSerializer(words, many=True)
            return Response(serializer.data)
        else:
            return Response()

class CategoryList(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('order')
    serializer_class = CategorySerializer

class QuestionList(viewsets.ReadOnlyModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, category):
        print(request.user)
        questions = Question.objects.filter(category=category).order_by('order')
        for q in questions:
            if request.user.is_authenticated():
                q.answer = Answer.objects.filter(user=request.user, question=q)
            else:
                q.answer = Answer.objects.none()
        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)

class StatDetails(viewsets.ViewSet):
    serializer_class = StatSerializer
    authentication_classes = (TokenAuthentication,)

    def get(self, request, question):
        print(question)

class AnswerAccessPermission(permissions.BasePermission):
    message = 'Must be logged in to submit answers'

    def has_permission(self, request, view):
        return request.user is not None

    def has_object_permission(self, request, view, obj):
        self.message = "You can only modify your own answers"
        return obj.user == request.user

class UserView(viewsets.ViewSet):
    authentication_classes = (TokenAuthentication,)

    def get(self, request):
        if request.user:
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        else:
            return Response()

    def list(self, request):
        if request.user:
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        else:
            return Response()

class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer
    queryset = Answer.objects.all()
    permission_classes = (AnswerAccessPermission,)
    authentication_classes = (TokenAuthentication,)
    lookup_fields = ('question', 'user')

    def perform_create(self, serializer):
        Answer.objects.filter(user=self.request.user, question=serializer.validated_data['question']).delete()
        instance = serializer.save(user=self.request.user)
        self.run_rdf(instance)

    def perform_update(self, serializer):
        instance = serializer.save(user=self.request.user)
        self.run_rdf(instance)

    def run_rdf(self, instance):
        if instance.question.q_type == 'bool':
            if instance.yesno == True:
                statements = []
                for statement in Statement.objects.filter(question=instance.question):
                    s = self.parse(statement.subject, instance)
                    p = self.parse(statement.predicate, instance)
                    o = self.parse(statement.obj, instance)
                    statements.append((s, p, o))
                run_statements(statements, instance.context())
            else:
                delete_context(instance.context())
        elif instance.question.q_type == 'check':
            if instance.options:
                delete_context(instance.context())
                statements = []
                for statement in Statement.objects.filter(question=instance.question):
                    if statement.choice is None:
                        print(statement)
                        s = self.parse(statement.subject, instance)
                        p = self.parse(statement.predicate, instance)
                        o = self.parse(statement.obj, instance)
                        statements.append((s, p, o))
                    elif statement.choice in instance.options:
                        print('choice ' + statement)
                        s = self.parse(statement.subject, instance)
                        p = self.parse(statement.predicate, instance)
                        o = self.parse(statement.obj, instance)
                        statements.append((s, p, o))
                run_statements(statements, instance.context())
            else:
                delete_context(instance.context())

    def parse(self, statement, answer):
        pre, uri = statement.split(':')
        if pre == '_':
            return statement
        prefix = RDFPrefix.objects.get(short=pre).full
        partial_statement = prefix.format(uri)
        return partial_statement.format(user=answer.user.id)

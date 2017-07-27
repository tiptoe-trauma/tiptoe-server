from questionnaire.models import *
from questionnaire.serializers import *
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework import permissions
from questionnaire.rdf import get_definitions, run_statements, delete_context


# Create your views here.
class DefinitionList(viewsets.ViewSet):
    def list(self, request):
        words = get_definitions()
        serializer = DefinitionSerializer(words, many=True)
        return Response(serializer.data)

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
                q.answer = Answer.objects.filter(organization=request.user.activeorganization.organization, question=q)
            else:
                q.answer = Answer.objects.none()
        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)

class QuestionView(viewsets.ViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, pk):
        question = Question.objects.get(pk=pk)
        serializer = QuestionSerializer(question, context={'request': request})
        return Response(serializer.data)

class AnswerAccessPermission(permissions.BasePermission):
    message = 'Must be logged in to submit answers'

    def has_permission(self, request, view):
        return request.user is not None

    def has_object_permission(self, request, view, obj):
        self.message = "You can only modify your own answers"
        return obj.organization == request.user.activeorganization.organization

class OrganizationAccessPermission(permissions.BasePermission):
    message = 'Must be logged in to see your organizations'

    def has_permission(self, request, view):
        if request.method == 'POST':
            if request.user.is_authenticated():
                self.message = 'You can only create organizations in which you are the user'
                user_id = request.user.id
                return 'users' in request.data and user_id in request.data['users']
        return request.user.is_authenticated()

    def has_object_permission(self, request, view, obj):
        self.message = "You can only modify your own organizations"
        return request.user in obj.users.all()

class StatView(viewsets.ViewSet):
    serializer_class = StatSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AnswerAccessPermission,)

    def retrieve(self, request, pk):
        question = Question.objects.get(pk=pk)
        answer = Answer.objects.get(question=question, user=request.user)
        other_answers = Answer.objects.filter(question=answer.question)
        truth_map = [x.eq(answer) for x in other_answers]
        same = truth_map.count(True)
        percent = 0.0
        if len(truth_map) > 0:
            percent = same / len(truth_map)
        serializer = StatSerializer({'same': percent})
        return Response(serializer.data)

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

    def post(self, request):
        if 'id' not in request.data:
            return Response('Organization ID required', status=400)
        org_id = request.data['id']
        org = Organization.objects.filter(pk=org_id, users=request.user)
        if org.exists() == False:
            return Response('organization either does not exist, or you do not have permission', status=403)
        if hasattr(request.user, 'activeorganization'):
            request.user.activeorganization.organization = org.first()
            request.user.activeorganization.save()
        else:
            ao = ActiveOrganization.objects.create(user=request.user,
                                                   organization=org.first())
            request.user.activeorganization = ao
        request.user.save()
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class OrganizationView(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = (OrganizationAccessPermission,)
    authentication_classes = (TokenAuthentication,)
    queryset = Organization.objects.all()

    def list(self, request):
        if request.user.is_authenticated():
            organizations = Organization.objects.filter(users=request.user)
            return Response(OrganizationSerializer(organizations, many=True).data)
        return Response()

class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer
    queryset = Answer.objects.all()
    permission_classes = (AnswerAccessPermission,)
    authentication_classes = (TokenAuthentication,)
    lookup_fields = ('question', 'user')

    def retrieve(self, request, pk=None):
        if request.user.is_authenticated():
            queryset = Answer.objects.all()
            data = get_object_or_404(queryset, question=pk, organization=request.user.activeorganization.organization)
            serializer = AnswerSerializer(data)
            return Response(serializer.data)
        else:
            return Response()

    def perform_create(self, serializer):
        Answer.objects.filter(organization=self.request.user.activeorganization.organization, question=serializer.validated_data['question']).delete()
        instance = serializer.save(organization=self.request.user.activeorganization.organization)
        self.run_rdf(instance)

    def perform_update(self, serializer):
        instance = serializer.save(organization=self.request.user.activeorganization.organization)
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
        return partial_statement.format(user=answer.organization.id)

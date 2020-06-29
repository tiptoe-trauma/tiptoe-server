from questionnaire.models import *
import json
from django.conf import settings
from questionnaire.serializers import *
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view
from rest_framework import permissions
from questionnaire.rdf import get_definitions, run_statements, delete_context, rdf_from_organization
from averaged_dict.average_dict import average_dict
from django.core.mail import send_mail

def get_or_zero(classmodel, **kwargs):
    try:
        return classmodel.objects.get(**kwargs).value()
    except classmodel.DoesNotExist:
        return 0

def get_or_none(classmodel, **kwargs):
    try:
        return classmodel.objects.get(**kwargs).value()
    except classmodel.DoesNotExist:
        return None

def strip_definitions(text):
    if("|" in text):
        text = text.split("|")[1].replace("}", "")
    return text

def populate_stats(org, stat_type):
    data = {}
    data['organization'] = org.name
    for question in Question.objects.filter(tags__contains=stat_type):
        data[question.api_name] = get_or_none(Answer, organization=org, question=question)
    return data

def send_login_email(request, user):
    token = Token.objects.get(user=user).key
    login_url = 'http://{}/?token={}'.format(request.get_host(), token)
    if(settings.EMAIL_HOST):
        email_message = "Here is your login URL for cafe\n\n{}".format(login_url)
        send_mail(
            'CAFE Trauma Login',
            email_message,
            'please-do-not-reply@ufl.edu',
            [user.email],
            fail_silently=False,
        )
    else:
        print(login_url)

@api_view(['POST'])
def retrieve_user(request):
    body = json.loads(request.body.decode('utf-8'))
    email = body.get('email')
    try:
        user = User.objects.get(email=email)
        send_login_email(request, user)
        return Response("Email Sent")
    except User.DoesNotExist:
        return Response("No matching email found", status=404)
    except:
        return Response("Email sending failed, please contact site owner", status=500)
    return Response("Server Error", status=500)

@api_view(['POST'])
def token_login(request):
    body = json.loads(request.body.decode('utf-8'))
    login_token = body.get('login_token')
    try:
        # TODO: Switch to a token table instead of just emailing the actual tokens
        token = Token.objects.get(key=login_token)
        return Response({'token': token.key})
    except Token.DoesNotExist:
        return Response("Invalid login token", status=404)
    return Response("Server Error", status=500)

def unique_email(email):
    return User.objects.filter(email=email).count() == 0

@api_view(['POST'])
def create_web_user(request, questionnaire_type):
    if request.user.is_authenticated():
        return Response("Must be logged out to create new user", status=500)
    if questionnaire_type not in ['center', 'system']:
        return Response("Cannot create survey of type {}".format(questionnaire_type), status=500)
    body = json.loads(request.body.decode('utf-8'))
    email = body.get('email')
    name = body.get('name')
    if(not unique_email(email)):
        return Response("Email must be unique", status=500)
    user_count = User.objects.count()
    user = User.objects.create(username='web' + str(user_count))
    if email:
        user.email = email
        user.save()
    token = Token.objects.get(user=user)
    if name:
        org = Organization.objects.create(name=name, org_type=questionnaire_type)
    else:
        org = Organization.objects.create(name=questionnaire_type + str(user_count), org_type=questionnaire_type)
    org.users.add(user)
    org.save()
    ActiveOrganization.objects.create(user=user, organization=org)
    return Response({'token': token.key})

@api_view(['POST'])
def update_email(request):
    if request.user.is_authenticated():
        body = json.loads(request.body.decode('utf-8'))
        email = body.get('email')
        if(not unique_email(email)):
            return Response("Email must be unique", status=500)
        if email:
            request.user.email = email
            request.user.save()
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        return Response("No Email Provided", status=500)
    return Response("Must be logged in", status=401)


@api_view(['GET'])
def tmd_stats(request):
    if request.user.is_authenticated():
        org = request.user.activeorganization.organization
        return Response(populate_stats(org, 'tmd'))
    return Response("TMD Problem", status=500)

@api_view(['GET'])
def tpm_stats(request):
    if request.user.is_authenticated():
        org = request.user.activeorganization.organization
        return Response(populate_stats(org, 'tpm'))
    return Response("TPM Problem", status=500)

@api_view(['GET'])
def api_policy(request, speciality):
    if request.user.is_authenticated():
        user_org = request.user.activeorganization.organization
        response = {}
        for question in Question.objects.filter(tags__contains=speciality,
                                                q_type="bool"):
            response[question.api_name] = get_or_none(Answer,
                                                      organization=user_org,
                                                      question=question)
        return Response(response)
    return Response("Must be logged in", status=402)

@api_view(['GET'])
def api_stat(request, stat_type):
    response = {}
    other_orgs = []
    certified_orgs = []
    questions = Question.objects.filter(tags__contains=stat_type, q_type="int")
    if len(questions) == 0:
        return Response("No questions found for '{}' type".format(stat_type), status=404)
    total_question = questions.get(tags__contains='total')
    questions = questions.exclude(id=total_question.id)
    if request.user.is_authenticated():
        user_org = request.user.activeorganization.organization
        # import pdb; pdb.set_trace()
        for org in Organization.objects.filter(org_type='center'):
            stats = {}
            total_count = get_or_zero(Answer, organization=org, question=total_question)
            if total_count != 0:
                for question in questions:
                    count = get_or_none(Answer, organization=org, question=question)
                    if count != None:
                        stats[question.api_name] = count / total_count
                    else:
                        stats[question.api_name] = None
                if org == user_org:
                    response['user_org'] = stats
                elif org.approved:
                    certified_orgs.append(stats)
                else:
                    other_orgs.append(stats)
    response['certified_orgs'] = average_dict(certified_orgs)
    response['other_orgs'] = average_dict(other_orgs)
    print(response)
    return Response(response)

@api_view(['GET'])
def stats(request):
    response = []
    for org in Organization.objects.filter(org_type='center'):
        data = {'yes': 0, 'no': 0}
        for answer in Answer.objects.filter(organization=org, question__q_type='bool'):
            if(answer.yesno):
               data['yes'] += 1
            else:
                data['no'] += 1
        response.append(data)
    return Response(response)

@api_view(['GET'])
def api_category_responses(request, web_category):
    # Get all responses to all questions in a given category
    category = web_category.replace('_', ' ')
    response = {}
    cat_list = Category.objects.filter(name__exact=category)
    cat_id = cat_list[0].id
    questionnaire = cat_list[0].questionnaire
    questions = Question.objects.filter(category__exact=cat_id)
    if request.user.is_authenticated():
        user_org = request.user.activeorganization.organization_id
        for question in questions:
            answers = Answer.objects.filter(question_id__exact=question.id)
            response[question.id] = {'q_text': question.text,
                                    'questionnaire': questionnaire,
                                    'order': question.order,
                                    'total': len(answers)}

            answer_type = ''
            for answer in answers:
                org_id = answer.organization_id
                if not answer_type:
                    if answer.yesno is not None:
                        answer_type = "yesno"
                    elif answer.integer:
                        answer_type = "number"
                    elif answer.text:
                        answer_type = "text"
                    elif answer.options.values():
                        answer_type = "options"
                
                if answer_type == "yesno":
                    if answer.yesno:
                        try:
                            response[question.id]['trues'] += 1
                        except KeyError:
                            response[question.id]['trues'] = 1
                    if user_org == org_id:
                        response[question.id]['active_answer'] = answer.yesno
                elif answer_type == "number":
                    try:
                        response[question.id]['numbers'].append(answer.integer)
                    except KeyError:
                        response[question.id]['numbers'] = [answer.integer]
                    if user_org == org_id:
                        response[question.id]['active_answer'] = answer.integer
                elif answer_type == "options":
                    if 'options' not in response[question.id].keys():
                        response[question.id]['options'] = {}
                    if user_org == org_id:
                        response[question.id]['active_answer'] = []
                    for option in answer.options.values():
                        if option['text'] not in response[question.id]['options'].keys():
                            response[question.id]['options'][option['text']] = 0
                        else:
                            response[question.id]['options'][option['text']] += 1
                        if user_org == org_id:
                            response[question.id]['active_answer'].append(option['text'])
    return Response(response)



@api_view(['GET'])
def api_percent_yes(request, web_category):
    # For gathering responses whose type is boolean
    category = web_category.replace('_', ' ')
    response = {}
    cat_list = Category.objects.filter(name__exact=category)
    cat_id = cat_list[0].id
    questionnaire = cat_list[0].questionnaire

    questions = Question.objects.filter(category__exact=cat_id)
    if request.user.is_authenticated():
        user_org = request.user.activeorganization.organization
        for question in questions:
            import pdb; pdb.set_trace()
            response[question.id] = {'q_text': question.text, 'questionnaire': questionnaire}
            answers = Answer.objects.filter(question_id__exact=question.id)
            total = len(answers)
            trues = 0
            for answer in answers:
                org_id = answer.organization_id
                if answer.yesno:
                    trues += 1
                    if user_org == org_id:
                        response[question.id]['active_answer'] = answer.yesno
            response[question.id]['percent_yes'] = round((trues/total) * 100)
    return Response(response)

@api_view(['GET'])
def api_numbers(request, web_category):
    # For gathering responses whose type is integers
    response = {}
    cat_list = Category.objects.filter(name__exact=category)
    cat_id = cat_list[0].id
    questionnaire = cat_list[0].questionnaire

    questions = Question.objects.filter(category__exact=cat_id)
    if request.user.is_authenticated():
        user_org = request.user.activeorganization.organization
        for question in questions:
            response[question.id] = {'q_text': question.text, 'questionnaire': questionnaire, 'answers': []}
            answers = Answer.objects.filter(question_id__exact=question_id)
            for answer in answers:
                org_id = answer.organization_id
                if answer.integer:
                    response[question.id]['answers'].append(answer.integer)
                    if user_org == org_id:
                       response[question.id]['active_answer'] = answer.integer
    return Response(response)

@api_view(['GET'])
def api_multichoice(request, web_category):
    # For gathering responses with multichoice answers
    response = {}
    cat_list = Category.objects.filter(name__exact=category)
    cat_id = cat_list[0].id
    questionnaire = cat_list[0].questionnaire

    questions = Question.objects.filter(category__exact=cat_id)
    if request.user.is_authenticated():
        user_org = request.user.activeorganization.organization
        for question in questions:
            response[question.id] = {'q_text': question.text, 'questionnaire': questionnaire, 'answers': []}
            answers = Answer.objects.filter(question_id__exact=question_id)
            for answer in answers:
                org_id = answer.organization_id
                if answer.integer:
                    response[question.id]['answers'].append(answer.integer)
                    if user_org == org_id:
                       response[question.id]['active_answer'] = answer.integer
    return Response(response)


def populate_joyplot(org):
    data = {}
    data['id'] = org.id
    data['247_coverage'] = get_or_none(Answer, organization=org, question=41)
    data['trauma_backup'] = get_or_none(Answer, organization=org, question=57)
    data['trauma_backup_approved'] = get_or_none(Answer, organization=org, question=213)
    data['ortho_247'] = get_or_none(Answer, organization=org, question=60)
    data['ortho_liason'] = get_or_none(Answer, organization=org, question=61)
    data['ortho_50_meetings'] = get_or_none(Answer, organization=org, question=63)
    data['ortho_residency'] = get_or_none(Answer, organization=org, question=72)
    data['ortho_fellowship'] = get_or_none(Answer, organization=org, question=73)
    data['neuro_247'] = get_or_none(Answer, organization=org, question=75)
    data['neuro_liason'] = get_or_none(Answer, organization=org, question=76)
    data['neuro_50_meetings'] = get_or_none(Answer, organization=org, question=80)
    data['neuro_residency'] = get_or_none(Answer, organization=org, question=84)
    data['anesth_247'] = get_or_none(Answer, organization=org, question=87)
    data['anesth_liason'] = get_or_none(Answer, organization=org, question=91)
    data['general_atls_once'] = get_or_zero(Answer, organization=org, question=45)
    data['general_atls_current'] = get_or_zero(Answer, organization=org, question=46)
    data['trauma_priv'] = get_or_zero(Answer, organization=org, question=43)
    data['trauma_panel'] = get_or_zero(Answer, organization=org, question=42)
    data['trauma_cme'] = get_or_zero(Answer, organization=org, question=47)
    data['trauma_board_eligible'] = get_or_zero(Answer, organization=org, question=44)
    data['trauma_board_certified'] = get_or_zero(Answer, organization=org, question=152)
    data['trauma_exclusive'] = get_or_zero(Answer, organization=org, question=54)
    data['trauma_critical_certifications'] = get_or_zero(Answer, organization=org, question=58)
    data['trauma_fellowship'] = get_or_zero(Answer, organization=org, question=59)
    data['ortho_panel'] = get_or_zero(Answer, organization=org, question=64)
    data['ortho_cme'] = get_or_zero(Answer, organization=org, question=62)
    data['ortho_board_eligible'] = get_or_zero(Answer, organization=org, question=65)
    data['ortho_board_certified'] = get_or_zero(Answer, organization=org, question=145)
    data['ortho_exclusive'] = get_or_zero(Answer, organization=org, question=67)
    data['neuro_panel'] = get_or_zero(Answer, organization=org, question=77)
    data['neuro_cme'] = get_or_zero(Answer, organization=org, question=79)
    data['neuro_board_eligible'] = get_or_zero(Answer, organization=org, question=214)
    data['neuro_board_certified'] = get_or_zero(Answer, organization=org, question=215)
    data['neuro_exclusive'] = get_or_zero(Answer, organization=org, question=81)
    data['anesth_panel'] = get_or_zero(Answer, organization=org, question=93)
    data['anesth_board_certified'] = get_or_zero(Answer, organization=org, question=216)
    data['anesth_residency'] = get_or_zero(Answer, organization=org, question=94)
    return data

@api_view(['GET'])
def joyplot(request):
    response = []
    approved = []
    # these are hardcoded values for starter survey, need to find better method
    print(request.user)
    if request.user.is_authenticated():
        response.append(populate_joyplot(request.user.activeorganization.organization))
        for org in Organization.objects.filter(org_type='center', approved=True):
            if org != request.user.activeorganization.organization:
                approved.append(populate_joyplot(org))
    response.append(average_dict(approved))
    return Response(response)

class DefinitionList(viewsets.ViewSet):
    def list(self, request):
        words = get_definitions()
        serializer = DefinitionSerializer(words, many=True)
        return Response(serializer.data)

class CategoryList(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('order')
    serializer_class = CategorySerializer

    def list(self, request):
        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data)


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


class CompletionView(viewsets.ViewSet):
    serializer_class = CompletionSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AnswerAccessPermission,)

    def list(self, request):
        data = []
        # determine if center or system
        try:
            qtype = request.user.activeorganization.organization.org_type
            for category in Category.objects.filter(questionnaire=qtype):
                c = {}
                c['category'] = category.id
                questions = Question.objects.filter(category=category)
                c['total_questions'] = len(questions)
                answer_count = Answer.objects.filter(
                        organization=request.user.activeorganization.organization,
                        question__in=questions).count()
                c['completed_questions'] = answer_count
                data.append(c)
            serializer = CompletionSerializer(data, many=True)
            return Response(serializer.data)
        except AttributeError:
            return Response()

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
                    elif statement.choice in instance.options.all():
                        print('choice ' + str(statement))
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
        if uri:
            partial_statement = prefix + uri
        else:
            partial_statement = prefix
        return '<' + partial_statement.format(user=answer.organization.id) + '>'

class RDFView(APIView):
    authentication_classes = (TokenAuthentication,)

    def get(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        if request.user.is_authenticated() and request.user in organization.users.all():
            rdf = rdf_from_organization(organization)
            return HttpResponse(rdf, content_type="rdf/xml")
        else:
            return Response('Incorrect User', status=403)

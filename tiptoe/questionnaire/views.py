from questionnaire.models import *
import json
from django.conf import settings
from django.db.models import Q
from questionnaire.serializers import *
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from questionnaire.rdf import get_definitions, run_query, run_statements, delete_context, rdf_from_survey
from averaged_dict.average_dict import average_dict
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import pandas as pd
import xml.etree.ElementTree as ET

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

#adjust for org
def populate_stats(srvy, stat_type):
    data = {}
    data['survey'] = srvy.name
    for question in Question.objects.filter(tags__contains=stat_type):
        data[question.api_name] = get_or_none(Answer, survey=srvy, question=question)
    return data

def send_login_email(request, user):
    token = Token.objects.get(user=user).key
    if(settings.LOGIN_URL):
        login_url = 'https://{}/?token={}'.format(settings.LOGIN_URL, token)
    else:
        login_url = 'http://{}/?token={}'.format(request.get_host(), token)

    if(settings.EMAIL_HOST):
        email_message = "Here is your login URL for TIPTOE\n\n{}".format(login_url)
        send_mail(
            'TIPTOE Login',
            email_message,
            'questionnaire_retrieval@tiptoe.apps.dbmi.cloud',
            [user.email],
            fail_silently=False,
        )
    else:
        print(login_url)

def send_invite_email(user, message):
    token = Token.objects.get(user=user).key
    if(settings.LOGIN_URL):
        login_url = 'https://{}/?token={}'.format(settings.LOGIN_URL, token)
    else:
        login_url = 'http://{}/?token={}'.format(request.get_host(), token)
    if(settings.EMAIL_HOST):
        email_message = message + "\n\nHere is your login URL: {}".format(login_url)
        send_mail(
            'TIPTOE Invitation',
            email_message,
            'questionnaire_retrieval@tiptoe.apps.dbmi.cloud',
            [user.email],
            fail_silently=False,
        )
    else:
        print(login_url)

@api_view(['POST'])
def invite_to_org(request):
    print("starting invite")
    if request.user.is_authenticated:
        print("authenticated")
        body = json.loads(request.body.decode('utf-8'))
        email = body[0].lower()
        org_id = body[1]
        print(org_id)
        message = body[2]
        allowed_org = Organization.objects.get(pk=org_id, users=request.user)
        print(allowed_org)

        if(unique_email(email)):
            print('new user')
            user_count = User.objects.count()
            user = User.objects.create(username='web' + str(user_count))
            user.email = email
            user.save()
        else:
            print("else")
            user = User.objects.get(email=email)

        print('after')
        allowed_org.users.add(user)
        allowed_org.save()

        send_invite_email(user, message)

        return Response('Invitation sent.')
    else:
        return Response("Must be logged in to send an invitation.", status=500)

@api_view(['POST'])
def approve_srvy(request):
    if request.user.is_authenticated:
        active_srvy = request.user.activesurvey.survey
        active_srvy.approved=True
        active_srvy.save()

        return Response('Survey submitted.')
    else:
        return Response("Must be logged in to approve a submission.", status=500)

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
    return User.objects.filter(email=email.lower()).count() == 0

@api_view(['POST'])
def create_survey(request):
    if request.user.is_authenticated:
        body = json.loads(request.body.decode('utf-8'))
        surveyDate = body[0]
        surveyOrg = body[1]

        survey = Survey.objects.create(date=surveyDate, organization_id = surveyOrg["id"])
        survey.save()

        serializer = SurveySerializer(survey)
        return Response(serializer.data)
    else:
        return Response("Must be logged in to create a survey.", status=500)



@api_view(['POST'])
def create_web_user(request, questionnaire_type):
    if request.user.is_authenticated:
        return Response("Must be logged out to create new user", status=500)
    if questionnaire_type not in ['center', 'system', 'tiptoe', 'tos']:
        return Response("Cannot create survey of type {}".format(questionnaire_type), status=500)
    body = json.loads(request.body.decode('utf-8'))
    email = body.get('email').lower()
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
    #need an active survey?
    return Response({'token': token.key})

@api_view(['POST'])
def update_email(request):
    if request.user.is_authenticated:
        body = json.loads(request.body.decode('utf-8'))
        email = body.get('email').lower()
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
    if request.user.is_authenticated:
        srvy = request.user.activesurvey.survey
        return Response(populate_stats(srvy, 'tmd'))
    return Response("TMD Problem", status=500)

@api_view(['GET'])
def tpm_stats(request):
    if request.user.is_authenticated:
        srvy = request.user.activesurvey.survey
        return Response(populate_stats(srvy, 'tpm'))
    return Response("TPM Problem", status=500)

@api_view(['GET'])
def api_policy(request, speciality):
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey
        response = {}
        for question in Question.objects.filter(tags__contains=speciality,
                                                q_type="bool"):
            response[question.api_name] = get_or_none(Answer,
                                                      survey=user_srvy,
                                                      question=question)
        return Response(response)
    return Response("Must be logged in", status=402)

@api_view(['GET'])
def api_stat(request, stat_type):
    response = {}
    other_srvys = []
    certified_srvys = []
    questions = Question.objects.filter(tags__contains=stat_type, q_type="int")
    if len(questions) == 0:
        return Response("No questions found for '{}' type".format(stat_type), status=404)
    total_question = questions.get(tags__contains='total')
    questions = questions.exclude(id=total_question.id)
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey
        # import pdb; pdb.set_trace()
        for srvy in Survey.objects.filter(org_type='center'):
            stats = {}
            total_count = get_or_zero(Answer, survey=srvy, question=total_question)
            if total_count != 0:
                for question in questions:
                    count = get_or_none(Answer, survey=srvy, question=question)
                    if count != None:
                        stats[question.api_name] = count / total_count
                    else:
                        stats[question.api_name] = None
                if srvy == user_srvy:
                    response['user_srvy'] = stats
                elif srvy.approved:
                    certified_srvys.append(stats)
                else:
                    other_srvys.append(stats)
    response['certified_srvys'] = average_dict(certified_srvys)
    response['other_srvys'] = average_dict(other_srvys)
    print(response)
    return Response(response)

@api_view(['GET'])
def stats(request):
    response = []
    for srvy in Survey.objects.filter(org_type='center'):
        data = {'yes': 0, 'no': 0}
        for answer in Answer.objects.filter(survey=srvy, question__q_type='bool'):
            if(answer.yesno):
               data['yes'] += 1
            else:
                data['no'] += 1
        response.append(data)
    return Response(response)

@api_view(['GET'])
def get_sample_size(request):
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey
        organizations = Organization.objects.filter( Q(org_type='tiptoe') & ~Q(pk=user_srvy.organization.id)).all()
        

        result = 0
        for org in organizations:
            surveys = [survey for survey in org.surveys.all() if survey.approved]
            if surveys:
                result += 1
        return Response(result)

@api_view(['GET'])
def api_category_responses(request, web_category):
    # Get all responses to all questions in a given category
    category = web_category.replace('_', ' ')
    response = {}
    cat_list = Category.objects.filter(name__exact=category)
    cat_id = cat_list[0].id
    questionnaire = cat_list[0].questionnaire
    questions = Question.objects.filter(category__exact=cat_id)
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey_id
        organizations = Organization.objects.all().exclude(pk=request.user.activesurvey.survey.organization.pk)
        correct_surveys = []
        correct_surveys.append(request.user.activesurvey.survey)
        #all orgs except current one
        for org in organizations:
            latest_survey = org.surveys.filter(approved=True).order_by('-date')
            if latest_survey:
                correct_surveys.append(latest_survey[0])


        for question in questions:
            answers = Answer.objects.filter( Q(question_id__exact=question.id) & (
                                            Q(survey__in=correct_surveys) ) )
            response[question.id] = {'q_text': question.text,
                                    'questionnaire': questionnaire,
                                    'order': question.order,
                                    'total': len(answers)}

            answer_type = ''
            for answer in answers:
                srvy_id = answer.survey_id
                if not answer_type:
                    if answer.integer == -1:
                        answer_type = "yesno"
                    elif answer.integer or answer.flt:
                        answer_type = "number"
                    elif answer.text:
                        answer_type = "text"
                    elif answer.options.values():
                        answer_type = "options"
                    elif answer.yesno is not None: 
                        answer_type = "yesno"
                
                if answer_type == "yesno":
                    if answer.yesno:
                        try:
                            response[question.id]['trues'] += 1
                        except KeyError:
                            response[question.id]['trues'] = 1
                    if user_srvy == srvy_id:
                        if answer.integer == -1:
                            response[question.id]['active_answer'] = False
                        else:
                            response[question.id]['active_answer'] = answer.yesno
                    if answer.integer == -1:
                        response[question.id]['total'] -= 1
                elif answer_type == "number":
                    if (answer.integer):
                        try:
                            response[question.id]['numbers'].append(answer.integer)
                        except KeyError:
                            response[question.id]['numbers'] = [answer.integer]
                        if user_srvy == srvy_id:
                            response[question.id]['active_answer'] = answer.integer
                    else:
                        try:
                            response[question.id]['numbers'].append(answer.flt)
                        except KeyError:
                            response[question.id]['numbers'] = [answer.flt]
                        if user_srvy == srvy_id:
                            response[question.id]['active_answer'] = answer.flt

                elif answer_type == "text":
                    if 'options' not in response[question.id].keys():
                        response[question.id]['options'] = {}
                    if user_srvy == srvy_id:
                        response[question.id]['active_answer'] = []
                    if answer.text:
                        if answer.text not in response[question.id]['options'].keys():
                            response[question.id]['options'][answer.text] = 1
                        else:
                            response[question.id]['options'][answer.text] += 1
                        if user_srvy == srvy_id:
                            response[question.id]['active_answer'].append(answer.text)
                elif answer_type == "options":
                    if 'options' not in response[question.id].keys():
                        response[question.id]['options'] = {}
                    if user_srvy == srvy_id:
                        response[question.id]['active_answer'] = []
                    for option in answer.options.values():
                        if option['text'] not in response[question.id]['options'].keys():
                            response[question.id]['options'][option['text']] = 1
                        else:
                            response[question.id]['options'][option['text']] += 1
                        if user_srvy == srvy_id:
                            response[question.id]['active_answer'].append(option['text'])

            if answer_type == "text" or answer_type == "options":
                options = {}
                for option in question.options.values():
                    options[option['text']] = option['id']

                options = {a: b for a, b in sorted(options.items(), key=lambda item: item[1])}
                response[question.id]['or_options'] = sorted(response[question.id]['options'].items(),
                                                            key=lambda kv: options[kv[0]])

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
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey
        for question in questions:
            import pdb; pdb.set_trace()
            response[question.id] = {'q_text': question.text, 'questionnaire': questionnaire}
            #change to this answer plus latest approved answer from *other* orgs
            answers = Answer.objects.filter( Q(question_id__exact=question.id) & (
                                            Q(survey_id=user_srvy)  | Q(survey__approved=True) ) )
            total = len(answers)
            trues = 0
            for answer in answers:
                srvy_id = answer.survey_id
                if answer.yesno:
                    trues += 1
                    if user_srvy == srvy_id:
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
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey
        for question in questions:
            response[question.id] = {'q_text': question.text, 'questionnaire': questionnaire, 'answers': []}
            #change to this answer plus latest approved answer from *other* orgs
            answers = Answer.objects.filter( Q(question_id__exact=question.id) & (
                                            Q(survey_id=user_srvy)  | Q(survey__approved=True) ) )
            for answer in answers:
                srvy_id = answer.survey_id
                if answer.integer:
                    response[question.id]['answers'].append(answer.integer)
                    if user_srvy == srvy_id:
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
    if request.user.is_authenticated:
        user_srvy = request.user.activesurvey.survey
        for question in questions:
            response[question.id] = {'q_text': question.text, 'questionnaire': questionnaire, 'answers': []}
            answers = Answer.objects.filter( Q(question_id__exact=question.id) & (
                                            Q(survey_id=user_srvy)  | Q(survey__approved=True) ) )
            #change to this answer plus latest approved answer from *other* orgs
            for answer in answers:
                srvy_id = answer.survey_id
                if answer.integer:
                    response[question.id]['answers'].append(answer.integer)
                    if user_srvy == srvy_id:
                       response[question.id]['active_answer'] = answer.integer
    return Response(response)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def run_unique_query(request):
    query = request.GET.get('query')
    res = run_query(query)
    print(res)
    return Response(res)

def populate_joyplot(srvy):
    data = {}
    data['id'] = srvy.id
    data['247_coverage'] = get_or_none(Answer, survey=srvy, question=41)
    data['trauma_backup'] = get_or_none(Answer, survey=srvy, question=57)
    data['trauma_backup_approved'] = get_or_none(Answer, survey=srvy, question=213)
    data['ortho_247'] = get_or_none(Answer, survey=srvy, question=60)
    data['ortho_liason'] = get_or_none(Answer, survey=srvy, question=61)
    data['ortho_50_meetings'] = get_or_none(Answer, survey=srvy, question=63)
    data['ortho_residency'] = get_or_none(Answer, survey=srvy, question=72)
    data['ortho_fellowship'] = get_or_none(Answer, survey=srvy, question=73)
    data['neuro_247'] = get_or_none(Answer, survey=srvy, question=75)
    data['neuro_liason'] = get_or_none(Answer, survey=srvy, question=76)
    data['neuro_50_meetings'] = get_or_none(Answer, survey=srvy, question=80)
    data['neuro_residency'] = get_or_none(Answer, survey=srvy, question=84)
    data['anesth_247'] = get_or_none(Answer, survey=srvy, question=87)
    data['anesth_liason'] = get_or_none(Answer, survey=srvy, question=91)
    data['general_atls_once'] = get_or_zero(Answer, survey=srvy, question=45)
    data['general_atls_current'] = get_or_zero(Answer, survey=srvy, question=46)
    data['trauma_priv'] = get_or_zero(Answer, survey=srvy, question=43)
    data['trauma_panel'] = get_or_zero(Answer, survey=srvy, question=42)
    data['trauma_cme'] = get_or_zero(Answer, survey=srvy, question=47)
    data['trauma_board_eligible'] = get_or_zero(Answer, survey=srvy, question=44)
    data['trauma_board_certified'] = get_or_zero(Answer, survey=srvy, question=152)
    data['trauma_exclusive'] = get_or_zero(Answer, survey=srvy, question=54)
    data['trauma_critical_certifications'] = get_or_zero(Answer, survey=srvy, question=58)
    data['trauma_fellowship'] = get_or_zero(Answer, survey=srvy, question=59)
    data['ortho_panel'] = get_or_zero(Answer, survey=srvy, question=64)
    data['ortho_cme'] = get_or_zero(Answer, survey=srvy, question=62)
    data['ortho_board_eligible'] = get_or_zero(Answer, survey=srvy, question=65)
    data['ortho_board_certified'] = get_or_zero(Answer, survey=srvy, question=145)
    data['ortho_exclusive'] = get_or_zero(Answer, survey=srvy, question=67)
    data['neuro_panel'] = get_or_zero(Answer, survey=srvy, question=77)
    data['neuro_cme'] = get_or_zero(Answer, survey=srvy, question=79)
    data['neuro_board_eligible'] = get_or_zero(Answer, survey=srvy, question=214)
    data['neuro_board_certified'] = get_or_zero(Answer, survey=srvy, question=215)
    data['neuro_exclusive'] = get_or_zero(Answer, survey=srvy, question=81)
    data['anesth_panel'] = get_or_zero(Answer, survey=srvy, question=93)
    data['anesth_board_certified'] = get_or_zero(Answer, survey=srvy, question=216)
    data['anesth_residency'] = get_or_zero(Answer, survey=srvy, question=94)
    return data

@api_view(['GET'])
def joyplot(request):
    response = []
    approved = []
    # these are hardcoded values for starter survey, need to find better method
    print(request.user)
    if request.user.is_authenticated:
        response.append(populate_joyplot(request.user.activesurvey.survey))
        for srvy in Survey.objects.filter(org_type='center', approved=True):
            if srvy != request.user.activesurvey.survey:
                approved.append(populate_joyplot(srvy))
    response.append(average_dict(approved))
    return Response(response)

class DefinitionList(viewsets.ViewSet):
    def list(self, request):
        words = get_definitions()
        serializer = DefinitionSerializer(words, many=True)
        return Response(serializer.data)

class CategoryList(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('order')

    def list(self, request):
        self.update_queryset()
        serializer = CategorySerializer(CategoryList.queryset, many=True)
        return Response(serializer.data)
    
    def update_queryset(self):
        CategoryList.queryset = Category.objects.all().order_by('order')

class QuestionList(viewsets.ReadOnlyModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, category):
        print(request.user)
        questions = Question.objects.filter(category=category).order_by('order')
        for q in questions:
            if request.user.is_authenticated:
                print("Question List potential issue.")
                q.answer.set(Answer.objects.filter(survey=request.user.activesurvey.survey, question=q))
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
        return obj.survey == request.user.activesurvey.survey

class OrganizationAccessPermission(permissions.BasePermission):
    message = 'Must be logged in to see your organizations'

    def has_permission(self, request, view):
        if request.method == 'POST':
            if request.user.is_authenticated:
                self.message = 'You can only create organizations in which you are the user'
                user_id = request.user.id
                return 'users' in request.data and user_id in request.data['users']
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        self.message = "You can only modify your own organizations"
        return request.user in obj.users.all()

class SurveyAccessPermission(permissions.BasePermission):
    message = 'Must be logged in to see your surveys'

    def has_permission(self, request, view):
        if request.method == 'POST':
            if request.user.is_authenticated:
                self.message = 'You can only create surveys in which you are the user'
                user_id = request.user.id
                return 'users' in request.data and user_id in request.data['users']
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        self.message = "You can only modify your own surveys"
        return request.user in obj.users.all()


class CompletionView(viewsets.ViewSet):
    serializer_class = CompletionSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AnswerAccessPermission,)

    def list(self, request):
        data = []
        # determine if center or system
        try:
            qtype = request.user.activesurvey.survey.organization.org_type
            for category in Category.objects.filter(questionnaire=qtype):
                c = {}
                c['category'] = category.id
                questions = Question.objects.filter(category=category)
                c['total_questions'] = len(questions)
                answer_count = Answer.objects.filter(
                        survey=request.user.activesurvey.survey,
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
        #change to this answer plus latest approved answer from *other* orgs
        answer = Answer.objects.get(question=question, user=request.user)
        other_answers = Answer.objects.filter( Q(question=answer.question) & Q(survey__approved=True))
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
            return Response('Survey ID required', status=400)
        srvy_id = request.data['id']
        #change to be org for permission
        allowed_orgs = Organization.objects.filter(users=request.user)
        srvy = Survey.objects.filter(pk=srvy_id, organization__in=allowed_orgs)
        if srvy.exists() == False:
            return Response('survey either does not exist, or you do not have permission', status=403)
        if hasattr(request.user, 'activesurvey'):
            request.user.activesurvey.survey = srvy.first()
            request.user.activesurvey.save()
        else:
            ao = ActiveSurvey.objects.create(user=request.user,
                                                   survey=srvy.first())
            request.user.activesurvey = ao
        request.user.save()
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class SurveyView(viewsets.ModelViewSet):
    serializer_class = SurveySerializer
    permission_classes = (SurveyAccessPermission,)
    authentication_classes = (TokenAuthentication,)
    queryset = Survey.objects.all()

    def list(self, request):
        if request.user.is_authenticated:
            allowed_orgs = Organization.objects.filter(users=request.user)
            surveys = Survey.objects.filter(organization__in=allowed_orgs).order_by('date')
            return Response(SurveySerializer(surveys, many=True).data)
        return Response()

class OrganizationView(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = (OrganizationAccessPermission,)
    authentication_classes = (TokenAuthentication,)
    queryset = Organization.objects.all()

    def list(self, request):
        if request.user.is_authenticated:
            orgs = Organization.objects.filter(users=request.user)
            return Response(OrganizationSerializer(orgs, many=True).data)
        return Response()

class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer
    queryset = Answer.objects.all()
    permission_classes = (AnswerAccessPermission,)
    authentication_classes = (TokenAuthentication,)
    lookup_fields = ('question', 'user')

    def retrieve(self, request, pk=None):
        if request.user.is_authenticated:
            queryset = Answer.objects.all()
            data = get_object_or_404(queryset, question=pk, survey=request.user.activesurvey.survey)
            serializer = AnswerSerializer(data)
            return Response(serializer.data)
        else:
            return Response()

    def perform_create(self, serializer):
        old_answer = Answer.objects.filter(survey=self.request.user.activesurvey.survey, question=serializer.validated_data['question'])
        Answer.objects.filter(survey=self.request.user.activesurvey.survey, question=serializer.validated_data['question']).delete()
        instance = serializer.save(survey=self.request.user.activesurvey.survey)
        self.run_rdf(instance, old_answer)

    def perform_update(self, serializer):
        instance = serializer.save(survey=self.request.user.activesurvey.survey)
        self.run_rdf(instance)

    def run_rdf(self, instance, old_answer=None):
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
        elif instance.question.q_type == 'combo':
            statements = []
            delete_context(instance.context())
            if instance.value():
                for statement in Statement.objects.filter(question=instance.question):
                    if statement.choice is None:
                        s = self.parse(statement.subject, instance)
                        p = self.parse(statement.predicate, instance)
                        o = self.parse(statement.obj, instance)
                        statements.append((s, p, o))
                    elif statement.choice.text == instance.value():
                        print('choice ' + str(statement))
                        s = self.parse(statement.subject, instance)
                        p = self.parse(statement.predicate, instance)
                        o = self.parse(statement.obj, instance)
                        statements.append((s, p, o))
                run_statements(statements, instance.context())
        elif instance.question.q_type == 'int':
            if instance.integer:
                statements = []
                delete_context(instance.context())
                for statement in Statement.objects.filter(question=instance.question):
                    s = self.parse(statement.subject, instance)
                    p = self.parse(statement.predicate, instance)
                    o = self.parse(statement.obj, instance)
                    statements.append((s, p, o))
                run_statements(statements, instance.context())
            else:
                delete_context(instance.context())
        elif instance.question.q_type == 'flt':
            if instance.flt:
                statements = []
                delete_context(instance.context())
                for statement in Statement.objects.filter(question=instance.question):
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
            if '{{value}}' in uri:
                return str(answer.value())
            else:
                node = statement + 'o' + str(answer.survey_id) + 'q' + str(answer.question_id)
                return node
        prefix = RDFPrefix.objects.get(short=pre).full
        if uri:
            partial_statement = prefix + uri
        else:
            partial_statement = prefix
        return  '<' + partial_statement.format(user=answer.survey.id) + '>' 

class RDFView(APIView):
    authentication_classes = (TokenAuthentication,)

    def get(self, request, survey_id):
        survey = Survey.objects.get(pk=survey_id)
        #change to org users
        if request.user.is_authenticated and request.user in survey.users.all():
            rdf = rdf_from_survey(survey)
            return HttpResponse(rdf, content_type="rdf/xml")
        else:
            return Response('Incorrect User', status=403)


def model_form_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = DocumentForm()
    return redirect('home')


# List of potential PHI data features
phi_features = ["LastModifiedDateTime", "FacilityId", "PatientId", "HomeZip", "HomeCountry", "HomeCity", "HomeState", "HomeCounty", "HomeResidences", "DateOfBirth", "Age", "AgeUnits", "IncidentDate", "IncidentTime", "PlaceOfInjuryCode", "InjuryZip", "IncidentCountry", "IncidentCity", "IncidentState", "IncidentCounty", "HospitalArrivalDate", "HospitalArrivalTime", "TraumaSurgeonArrivalDate", "TraumaSurgeonArrivalTime", "PatientUUID", "EdDischargeDate", "EdDischargeTime", "HospitalDischargeDate", "HospitalDischargeTime", "WithdrawalOfLifeSupportingTreatmentDate", "WithdrawalOfLifeSupportingTreatmentTime", "NationalProviderIdentifier" ]

# Function to check if a data feature contains PHI
def contains_phi(element):
    return element.tag.lower() in [tag.lower() for tag in phi_features] and element.text is not None and element.text.strip() != ""

@api_view(['POST'])
def read_file(request, survey_id):
    # Parse the TQIP file and return a dictionary of needed values
    if request.method == 'POST':
        file = request.FILES['profile']
        print(file)

        # Check if the file format is XML
        if file.name.lower().endswith('.xml'):
            print('xml file')
            # Load the XML file and parse it
            try:
                tree = ET.parse(file)
                root = tree.getroot()
                print('getting file')

                # Check if XML data contains PHI before processing. There could be a problem with performance if the file is very large, a potential solution
                # would be to only check the first NtdsRecord.
                for record in root.findall('NtdsRecord'):
                    print('reading record')
                    for column in record:
                        if contains_phi(column):
                            #This will take the file out of the loop and it should never reach the storage since this return will break the code.
                            return Response(f"Error: The data feature '{column.tag}' contains PHI. Please resubmit the document without PHI.", status=500)
                #break
                #Uncomment the break above if performance becomes an issue (large files being checked)

                #Since data did not contain PHI, then it can be saved and stored.
                print('saving file')
                tqip = Tqip.objects.create(content=file)
                survey = Survey.objects.get(pk=survey_id)
                survey.tqip = tqip
                tqip.save()
                survey.save()

                return JsonResponse({'message': 'File uploaded and processed successfully!'})

            except Exception as e:
                print(f'error processing file:  {str(e)}')
                return Response(f"Error processing the file: {str(e)}", status=500)

        else:
            print('Invalid file format. Please upload an XML file.')
            return Response("Invalid file format. Please upload an XML file.", status=500)

    else:
        return Response("Invalid request", status=500)

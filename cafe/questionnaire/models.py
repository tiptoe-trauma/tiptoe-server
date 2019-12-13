from django.db import models
from django.contrib.auth.models import User
# imports for user token creation
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist
import re
from datetime import datetime, timedelta

# Create your models here.
class Definition():
    def __init__(self, word, definition):
        self.word = word
        self.definition = definition

QUESTIONNAIRES = (('center', 'Trauma Center'),
                  ('system', 'Trauma System'))

class Category(models.Model):
    name = models.CharField(max_length=50)
    order = models.IntegerField()
    group = models.CharField(max_length=50, default="default")
    questionnaire = models.CharField(max_length=6, blank=False,
                                     choices=QUESTIONNAIRES)
    def __str__(self):
        return self.name

QUESTION_TYPES = (('combo', 'Combo Box'),
                  ('check', 'Check Boxes'),
                  ('text', 'Text Field'),
                  ('int', 'Integer Field'),
                  ('unit', 'Unit Int Field'),
                  ('bool', 'Yes or No'))

class Question(models.Model):
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    text = models.TextField(blank=False)
    order = models.IntegerField()
    q_type = models.CharField(max_length=5, choices=QUESTION_TYPES)
    options = models.ManyToManyField('Option', blank=True)
    tags = models.CharField(max_length=100, blank=True, null=True)
    help_text = models.CharField(max_length=500, blank=True, null=True)
    depends_on = models.ManyToManyField('Question', blank=True)
    depends_string = models.CharField(max_length=200, blank=True, null=True)
    api_name = models.CharField(max_length=100, blank=True, null=True)

    dep_regex = re.compile(r"#(?P<question>\d+)\s(?P<operator>==|!=|>=|>|<|<=)\s(?P<value>'[^']+'|True|False|\d+)\s?(?P<logic>or|and|xor)*\s?")

    def enabled(self, user):
        if self.depends_string == None:
            return True
        if user.is_authenticated():
            matches = self.dep_regex.finditer(self.depends_string)
            cur_status = True
            prev_operator = ""
            for matchnum, match in enumerate(matches):
                d = match.groupdict()
                q = Question.objects.get(pk=int(d['question']))
                a = Answer.objects.filter(organization=user.activeorganization.organization, question=q).first()
                print(d, q, a)
                next_status = self.dep_evaluate(d['operator'], d['value'], q, a)
                if prev_operator != "":
                    if prev_operator == 'and':
                        cur_status = next_status and cur_status
                    elif prev_operator == 'or':
                        cur_status = next_status or cur_status
                    elif prev_operator == 'xor':
                        cur_status = next_status != cur_status
                else:
                    cur_status = next_status
                if d['logic'] != None:
                    prev_operator = d['logic']
            return cur_status
        return False

    def __str__(self):
        return "{} - {}".format(self.id, self.text[:100])

    def only_text(self):
        return re.sub(r'<([^>]+)\|([^>]+)>', '\\1', self.text)

    def dep_evaluate(self, operator, value, question, answer):
        if question.q_type == 'bool':
            if operator == '==':
                if answer == None:
                    return False
                else:
                    return str(answer.yesno) == value
            elif operator == '!=':
                if answer == None:
                    return True
                else:
                    return str(answer.yesno) != value
        elif question.q_type == 'combo':
            if operator == '==':
                if answer == None:
                    return False
                else:
                    return answer.text == value.replace("'", '')
            elif operator == '!=':
                if answer == None:
                    return True
                else:
                    return answer.text != value.replace("'", '')
        # default to enabled
        print('defaulted')
        return True

class Option(models.Model):
    text = models.CharField(max_length=200)
    free = models.BooleanField(default=False)
    def __str__(self):
        return self.text

class Organization(models.Model):
    name = models.CharField(max_length=200, blank=True)
    users = models.ManyToManyField(User)
    org_type = models.CharField(max_length=6)
    approved = models.BooleanField(default=False)
    def __str__(self):
        return self.name

class ActiveOrganization(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    def __str__(self):
        return "{}-{}".format(self.user, self.organization)


class Answer(models.Model):
    text = models.CharField(max_length=50, null=True, blank=True)
    options = models.ManyToManyField('Option', blank=True)
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='answer')
    integer = models.IntegerField(null=True, blank=True)
    yesno = models.NullBooleanField(null=True, blank=True)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    class Meta:
        unique_together = ('organization', 'question')
    def eq(self, target):
        if(target.question.q_type == 'bool'):
            return self.yesno == target.yesno
        if(target.question.q_type == 'combo'):
            return self.text == target.text
        if(target.question.q_type == 'int'):
            return self.integer == target.integer
        return False
    def value(self):
        if(self.question.q_type == 'bool'):
            return self.yesno
        if(self.question.q_type == 'combo'):
            return self.text
        if(self.question.q_type == 'int'):
            return self.integer
        if(self.question.q_type == 'check'):
            return [ x.text for x in self.options.all() ]
        return 'bad question type'
    def __str__(self):
        return "{} - {}".format(self.organization, self.question.id)
    def context(self):
        return "<https://cafe-trauma.com/cafe/organization/{}/question/{}>".format(self.organization.id, self.question.id)

FUNCTION_TYPES = (('month_to_date', 'Number of months to date'),
                  ('example', 'Example'))

def month_to_date(answer):
    d = datetime.today() - timedelta(months=answer.integer)
    return d

STATEMENT_MAPPER = {
    'month_to_date': month_to_date
}

class Statement(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    predicate = models.CharField(max_length=255)
    obj = models.CharField(max_length=255)
    choice = models.ForeignKey('Option', on_delete=models.CASCADE, null=True, blank=True)
    value = models.BooleanField()
    f_type = models.CharField(max_length=50, choices=FUNCTION_TYPES, null=True, blank=True)
    def __str__(self):
        return "{} - {} {} {}".format(self.question, self.subject, self.predicate, self.obj)

class RDFPrefix(models.Model):
    short = models.CharField(max_length=10)
    full = models.CharField(max_length=255)
    def __str__(self):
        return "{}:{}".format(self.short, self.full)


# Create user tokens
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

@receiver(post_save, sender=Statement)
def generate_graphs(sender, instance=None, created=False, **kwargs):
    if instance:
        call_command('generate_graphs', str(instance.question.id), verbosity=0)

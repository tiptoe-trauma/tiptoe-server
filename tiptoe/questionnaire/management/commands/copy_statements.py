from django.core.management.base import BaseCommand, CommandError
from questionnaire.models import *

class Command(BaseCommand):
    help = 'Copy statements from one question to another/'

    def add_arguments(self, parser):
        parser.add_argument('from', type=int)
        parser.add_argument('to', type=int)

    def handle(self, *args, **options):
        print(options['from'])
        print(options['to'])
        from_question = Question.objects.get(pk=options['from'])
        to_question = Question.objects.get(pk=options['to'])
        for statement in Statement.objects.filter(question=from_question):
            statement.pk = None
            statement.question = to_question
            statement.save()

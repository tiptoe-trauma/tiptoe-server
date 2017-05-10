from django.core.management.base import BaseCommand, CommandError
from questionnaire.models import *
import os

class Command(BaseCommand):
    help = 'Generate Graphviz graph files in graphs/'

    def handle(self, *args, **options):
        self.stdout.write('{} statements'.format(len(Statement.objects.all())))
        with open("graphs/super.dot", "w") as f:
            f.write("digraph g { node [shape=rectangle];\n")
            for statement in Statement.objects.all():
                f.write(self.parse(statement))
            f.write("}")
        os.system("dot -Tpng graphs/super.dot -o static_graphs/super.png")

    def humanize(self, statement, question):
        if "_:" in statement:
            statement = statement.replace("_:", "{}:".format(question.id))
        predicates = {
                'obo:BFO_0000053': 'is_bearer_of',
                'obo:BFO_0000051': 'has_part',
                'obo:RO_0000052': 'inheres_in',
                'obo:RO_0000056': 'participates_in',
                'obo:IAO_0000136': 'is_about',
                'obo:BFO_0000050': 'part_of',
                'obo:RO_0002350': 'member_of',
                }
        for key in predicates:
            statement = statement.replace(key, predicates[key])
        return statement


    def parse(self, statement):
        subject = self.humanize(statement.subject, statement.question)
        obj = self.humanize(statement.obj, statement.question)
        predicate = self.humanize(statement.predicate, statement.question)
        return '"{}" -> "{}" [label="{}"]\n'.format(
                                            subject,
                                            obj,
                                            predicate)

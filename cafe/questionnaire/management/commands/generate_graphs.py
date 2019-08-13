from django.core.management.base import BaseCommand, CommandError
from questionnaire.models import *
import requests
import os

class Command(BaseCommand):
    help = 'Generate Graphviz graph files in graphs/'
    known_uris = {}

    def add_arguments(self, parser):
        parser.add_argument('question_id', nargs='*', type=int)

    def write_graph(self, statements, question):
        with open("graphs/{}.dot".format(question.id), "w") as f:
            f.write("digraph g { node [shape=rectangle];\n")
            f.write("graph [splines=true, nodesep=.5, ranksep=0, overlap=false];\n")
            f.write('labelloc="t";label="#{} {}";\n'.format(question.id, question.only_text()))
            for statement in statements:
                f.write(self.parse(statement))
            f.write("}")
        os.system("dot -Tpng graphs/{0}.dot -o static_graphs/{0}.png".format(question.id))

    def handle(self, *args, **options):
        questions = Question.objects.all()
        if options['question_id']:
            questions = Question.objects.filter(pk__in=options['question_id'])
        for question in questions:
            statements = Statement.objects.filter(question=question)
            if statements:
                self.write_graph(statements, question)

    def find_label(self, uri):
        if uri in self.known_uris:
            return self.known_uris[uri]
        headers = {'Accept': 'application/rdf+json'}
        p, specific = uri.split(':')
        if p == '_':
            return uri
        prefix = RDFPrefix.objects.get(short=p)
        full_uri = uri
        if(prefix):
            full_uri = prefix.full + specific
        url = "{}/rdf/statements?subj=<{}>".format(settings.TRIPLESTORE_URL, full_uri)
        label = 'http://www.w3.org/2000/01/rdf-schema#label'
        r = requests.get(url, headers=headers)
        if r.ok:
            try:
                d = r.json()
                if len(d.keys()) == 1:
                    self.known_uris[uri] = next(iter(d.values()))[label][0]['value']
                    return self.known_uris[uri]
            except Exception as e:
                return uri
        return uri

    def humanize(self, statement, question):
        return self.find_label(statement)

    def parse(self, statement):
        subject = self.humanize(statement.subject, statement.question)
        obj = self.humanize(statement.obj, statement.question)
        predicate = self.humanize(statement.predicate, statement.question)
        if statement.choice:
            predicate += "\n{}".format(statement.choice)
        return '"{}" -> "{}" [label="{}"]\n'.format(
                                            subject,
                                            obj,
                                            predicate)

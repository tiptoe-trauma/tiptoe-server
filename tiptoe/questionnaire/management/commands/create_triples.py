from django.core.management.base import BaseCommand, CommandError
from questionnaire.models import *
from questionnaire.rdf import get_triples, run_statements

import requests
from django.conf import settings
from rdflib import Graph, BNode, URIRef,  Literal, Namespace

#Only meant to be run on empty triplestore to initialize from DB answers
class Command(BaseCommand):
  help = 'Generate triples'

  def handle(self, *args, **options):

    bnodes = {}

    #load prefixes
    prefixes = {}
    for prefix in RDFPrefix.objects.all():
        prefixes[prefix.short] = Namespace(prefix.full)
        print("prefixes: " + prefix.short + " " + prefixes[prefix.short]);

    # Generate triples for answers
    for survey in Survey.objects.all():
        for answer in Answer.objects.filter(survey=survey):
            run_statements(get_triples(answer, prefixes, bnodes), answer.context());
            for triple in get_triples(answer, prefixes, bnodes):
                print(triple);
  

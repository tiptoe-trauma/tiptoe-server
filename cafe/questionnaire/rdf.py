import requests
from questionnaire.models import *
from django.conf import settings
from rdflib import Graph, BNode, URIRef, Literal, Namespace

def get_definitions():
    query = """
PREFIX obo: <http://purl.obolibrary.org/obo/>
    SELECT DISTINCT ?term ?userdef ?otherdef
    FROM <file://full_oostt.owl>
    WHERE {
      ?class rdf:type owl:Class .
      ?class rdfs:label ?term .
      optional {?class obo:OOSTT_00000030 ?userdef . }
      optional {?class obo:IAO_0000115 ?otherdef . }
}
    """
    body = {'query': query, 'Accept': 'application/sparql-results+json' }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    try:
        r = requests.request('POST', settings.BASE_URL + 'rdf', data=body, headers=headers)
        if r.ok:
            try:
                data = r.json()
                terms = []
                for term in data['results']['bindings']:
                    word = term['term']['value']
                    defi = ''
                    if 'userdef' in term.keys():
                        defi = term['userdef']['value']
                    elif 'otherdef' in term.keys():
                        defi = term['otherdef']['value']
                    terms.append(Definition(word, defi))
                return terms
            except ValueError:
                print('Bad json data')
                print(r.content)
                return []
        else:
            print(r)
            return []
    except:
        print('failed rdf')
        return []


def delete_context(context):
    pass

def run_statements(statements, context):
    body = ' .\n'.join([' '.join(s) for s in statements]) + ' .\n'
    headers = {'content-type': 'application/n-triples'}
    params = {'context': context}
    print('bod: {}'.format(body))
    try:
        r = requests.request('PUT', settings.BASE_URL + 'rdf/statements', data=body, headers=headers, params=params)
        print('finished: {}'.format(r.text))
    except:
        print('failed rdf')

def get_uri(text, prefixes, bnodes, answer):
    split = text.format(user=answer.organization.id).split(':')
    if len(split) > 1:
        # we have a prefix
        if split[0] == '_':
            if '{' in split[1]:
                return Literal(answer.integer)
            else:
                bnode_name = split[1] + str(answer.id)
                # we have a blank node
                # check to see if it already exists
                if bnode_name in bnodes.keys():
                    return bnodes[bnode_name]
                else:
                    # if not create it
                    # b = BNode(bnode_name)
                    b = prefixes['bnode'][bnode_name]
                    bnodes[bnode_name] = b
                    return b
        else:
            if split[0] in prefixes.keys():
                return prefixes[split[0]][split[1]]
            else:
                print('No prefix found: {}'.format(split))
                return None
    else:
        return text
    pass


def get_triples(answer, prefixes, bnodes):
    ret = []
    q_type = answer.question.q_type
    if q_type == 'bool':
        if answer.yesno:
            for statement in Statement.objects.filter(question=answer.question,
                                                      value=False):
                s = get_uri(statement.subject, prefixes, bnodes, answer)
                p = get_uri(statement.predicate, prefixes, bnodes, answer)
                o = get_uri(statement.obj, prefixes, bnodes, answer)
                ret.append((s, p, o))
        else:
            for statement in Statement.objects.filter(question=answer.question,
                                                      value=True):
                s = get_uri(statement.subject, prefixes, bnodes, answer)
                p = get_uri(statement.predicate, prefixes, bnodes, answer)
                o = get_uri(statement.obj, prefixes, bnodes, answer)
                ret.append((s, p, o))
    elif q_type == 'check':
        if answer.options:
            for statement in Statement.objects.filter(question=answer.question):
                if statement.choice is not None:
                    if statement.choice in answer.options.all():
                        s = get_uri(statement.subject, prefixes, bnodes, answer)
                        p = get_uri(statement.predicate, prefixes, bnodes, answer)
                        o = get_uri(statement.obj, prefixes, bnodes, answer)
                        ret.append((s, p, o))
                else:
                    s = get_uri(statement.subject, prefixes, bnodes, answer)
                    p = get_uri(statement.predicate, prefixes, bnodes, answer)
                    o = get_uri(statement.obj, prefixes, bnodes, answer)
                    ret.append((s, p, o))
    elif q_type == 'combo':
        if answer.text:
            for statement in Statement.objects.filter(question=answer.question):
                if statement.choice is not None:
                    if str(statement.choice) == str(answer.text):
                        s = get_uri(statement.subject, prefixes, bnodes, answer)
                        p = get_uri(statement.predicate, prefixes, bnodes, answer)
                        o = get_uri(statement.obj, prefixes, bnodes, answer)
                        ret.append((s, p, o))
                else:
                    s = get_uri(statement.subject, prefixes, bnodes, answer)
                    p = get_uri(statement.predicate, prefixes, bnodes, answer)
                    o = get_uri(statement.obj, prefixes, bnodes, answer)
                    ret.append((s, p, o))
    elif q_type == 'int' or q_type == 'text':
        for statement in Statement.objects.filter(question=answer.question):
            if statement.value:
                s = get_uri(statement.subject, prefixes, bnodes, answer)
                p = get_uri(statement.predicate, prefixes, bnodes, answer)
                if q_type == 'int':
                    o = Literal(answer.integer)
                else:
                    o = Literal(answer.text)
                ret.append((s, p, o))
            else:
                s = get_uri(statement.subject, prefixes, bnodes, answer)
                p = get_uri(statement.predicate, prefixes, bnodes, answer)
                o = get_uri(statement.obj, prefixes, bnodes, answer)
                ret.append((s, p, o))


    return ret


def rdf_from_organization(organization):
    # first clear graph
    g = Graph()
    bnodes = {}

    # next load prefixes
    prefixes = {}
    for prefix in RDFPrefix.objects.all():
        prefixes[prefix.short] = Namespace(prefix.full)
        g.bind(prefix.short, prefixes[prefix.short])

    # Generate triples for answers
    for answer in Answer.objects.filter(organization=organization):
        for triple in get_triples(answer, prefixes, bnodes):
            g.add(triple)

    return g.serialize()

import requests
from questionnaire.models import *
from django.conf import settings
from rdflib import Graph, BNode, URIRef, Literal, Namespace

def get_definitions():
    query = """
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?term ?userdef ?otherdef
    WHERE {
    #   ?class rdf:type owl:Class .
      ?class rdfs:label ?term .
      optional {?class obo:OOSTT_00000030 ?userdef . }
      optional {?class obo:IAO_0000115 ?otherdef . }
}
    """
    body = {'query': query, 'Accept': 'application/sparql-results+json' }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    try:
        r = requests.request('POST', settings.TRIPLESTORE_URL, data=body, headers=headers, auth=(settings.TRIPLESTORE_USER, settings.TRIPLESTORE_PASSWORD), verify=False)
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

def run_query(query):
    payload = {'query': query, 'Accept': 'application/sparql-results+json'}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    print('Running:\n' + query)

    r = requests.get(settings.TRIPLESTORE_URL, params=payload, headers=headers, auth=(settings.TRIPLESTORE_USER, settings.TRIPLESTORE_PASSWORD), verify=False)
    # r = requests.get(ENDPOINT, params=payload, headers=headers)
    # import pdb;pdb.set_trace()

    return r.json()

def delete_context(context):
    query = """\
            CLEAR GRAPH {}
            """.format(context)
    payload = { 'update': query }
    headers = {'content-type': 'application/n-triples'}
    print(query)
    r = requests.post(settings.TRIPLESTORE_URL + '/statements' , params=payload, auth=(settings.TRIPLESTORE_USER, settings.TRIPLESTORE_PASSWORD), verify=False)
    # r = requests.post(ENDPOINT +'/statements', params=payload)
    if r.status_code == 200 or r.status_code == 204:
        print('triples deleted')
    else:
        print('error during triple deletion')
        print(r.status_code)

def run_statements(statements, context):
    body = ' .\n'.join([' '.join(s) for s in statements]) + ' .\n'
    headers = {'content-type': 'application/n-triples'}
    query = '''
        INSERT DATA {{
            GRAPH {context} {{
                {body}
            }}
        }}
    '''.format(context=context, body=body)
    print(query)
    params = {'context': context}
    payload = {'update': query}
    r = requests.request('PUT', settings.TRIPLESTORE_URL + '/statements', data=body, headers=headers,  params=params, auth=(settings.TRIPLESTORE_USER, settings.TRIPLESTORE_PASSWORD), verify=False)
    if r.status_code == 200 or r.status_code == 204:
        print('triples added')
    else:
        print('error during triple creation')
        print(r.status_code)


def get_uri(text, prefixes, bnodes, answer):
    split = text.format(user=answer.organization.id).split(':')
    if len(split) > 1:
        # we have a prefix
        if split[0] == '_':
            if '{{value}}' in split[1]:
                return Literal(answer.value())
            else:
                bnode_name = split[1] + str(answer.id)
                # we have a blank node
                # check to see if it already exists
                if bnode_name in bnodes.keys():
                    return  '_:' + bnodes[bnode_name]
                else:
                    # if not create it
                    # b = BNode(bnode_name)
                    b = prefixes['bnode'][bnode_name]
                    bnodes[bnode_name] = b
                    return  '_:' +  b 
        else:
            if split[0] in prefixes.keys():
                return '<' + prefixes[split[0]][split[1]] + '>'
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
            if statement.value or '{{value}}' in statement.obj:
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

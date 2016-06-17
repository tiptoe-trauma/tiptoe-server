import requests
from questionnaire.models import Definition

def get_definitions():
    query = """
PREFIX obo: <http://purl.obolibrary.org/obo/>
    SELECT DISTINCT ?term ?userdef ?otherdef
    FROM <https://raw.githubusercontent.com/OOSTT/OOSTT/master/oostt.owl>
    WHERE {
      ?class rdf:type owl:Class .
      ?class rdfs:label ?term .
      optional {?class obo:OOSTT_00000030 ?userdef . }
      optional {?class obo:IAO_0000115 ?otherdef . }
}
    """
    body = {'query': query, 'Accept': 'application/sparql-results+json' }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    r = requests.request('POST', 'http://localhost:5000/rdf', data=body, headers=headers)
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
            return False
    else:
        print(r)
        return False


def delete_context(context):
    pass

def run_statements(statements, context):
    body = ' .\n'.join([' '.join(s) for s in statements]) + ' .\n'
    headers = {'content-type': 'application/n-triples'}
    params = {'context': context}
    print(body)
    r = requests.request('PUT', 'http://localhost:5000/rdf/statements', data=body, headers=headers, params=params)
    print(r.text)

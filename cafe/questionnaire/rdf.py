import requests
from questionnaire.models import Definition

def get_definitions():
    query = """
PREFIX obo: <http://purl.obolibrary.org/obo/>
    SELECT DISTINCT ?term ?userdef ?otherdef
    FROM <file://oostt_test.owl>
    WHERE {
      ?class rdf:type owl:Class .
      ?class rdfs:label ?term .
      optional {?class obo:OOSTT_00000030 ?userdef . }
      optional {?class obo:IAO_0000115 ?otherdef . }
}
    """
    body = {'query': query, 'Accept': 'application/sparql-results+json' }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    r = requests.request('POST', 'http://dev.cafe-trauma.com/rdf', data=body, headers=headers)
    if r.ok:
        try:
            data = r.json()
            terms = []
            terms.append(Definition("test", "A human health care role borne by a physician that, if realized, is realized by having the authority to direct and oversee the management all aspects of the trauma service."))
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

def run_statements(statments, context, user):
    pass

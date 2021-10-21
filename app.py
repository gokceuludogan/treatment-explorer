import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd


def query_wikidata(query):
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return pd.io.json.json_normalize(results['results']['bindings'])


sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
st.title('Treatment Explorer')
st.markdown('### Choose a disease')
disease = st.text_input(value='common cold', label='Disease name')
id_query = f"""
SELECT distinct ?item ?itemLabel ?itemDescription WHERE{{ 
  ?item ?label "{disease}"@en.  
  ?article schema:about ?item .
  ?article schema:isPartOf <https://en.wikipedia.org/>.	
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}   
}}"""
results_df = query_wikidata(id_query)
results_df['id'] = results_df['item.value'].apply(lambda x: x.split('/')[-1])
results_df['name'] = results_df.apply(lambda x: f'{x["itemLabel.value"]}:{x["itemDescription.value"]}', axis=1)
disease_name = st.selectbox('Map the disease to Wikidata', results_df['name'].tolist())
# disease_id = st.text_input('Enter the identifier', value='Q11081', key='id')
disease_id = results_df[results_df['name'] == disease_name]['id'].tolist()[0]

retrieve_drugs = f"""
  SELECT DISTINCT ?item ?itemLabel ?itemDescription ?ChEMBL
  WHERE
  {{
     wd:{disease_id} wdt:P2176 ?item.
     ?item wdt:P592 ?ChEMBL.
     ?item wdt:P31 wd:Q12140.
     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  }}
  """

drugs_df = query_wikidata(retrieve_drugs)
if drugs_df.shape[0] == 0:
    st.write('No possible treatment on Wikidata for this disease.')
    st.stop()
drugs_df['id'] = drugs_df['item.value'].apply(lambda x: x.split('/')[-1])
drugs_df.rename(columns={'itemLabel.value': 'drug', 'item.value': 'Wikidata', 'ChEMBL.value': 'ChEMBL'}, inplace=True)
st.markdown('### Posssible Treatments')
st.table(drugs_df[['drug', 'Wikidata', 'ChEMBL']])

query = f"""
 SELECT DISTINCT ?item ?itemLabel ?item2 ?item2Label WHERE {{
  wd:{disease_id} wdt:P2176 ?item.
  ?item wdt:P769 ?item2 .
   ?item wdt:P31 wd:Q12140.
   ?item2 wdt:P31 wd:Q12140.
   SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}

}}"""
st.markdown('### Number of drug interactions')
interactions_df = query_wikidata(query)
if interactions_df.shape[0] == 0:
    st.write('No drug interactions on Wikidata.')
    st.stop()
interactions_df.rename(columns={'itemLabel.value': 'drug', 'item2Label.value': 'interacted_drug'}, inplace=True) # , 'item.value': 'Wikidata', 'ChEMBL.value': 'ChEMBL'}, inplace=True)

st.table(interactions_df.groupby(['drug'])['interacted_drug'].count())

from streamlit_agraph import agraph, TripleStore, Config
store = TripleStore()
for node1, node2 in zip(interactions_df.drug, interactions_df.interacted_drug):
    link = '-'
    store.add_triple(node1, link, node2)

config = Config(height=500, width=600, nodeHighlightBehavior=True, highlightColor="#F7A7A6", directed=True,
                collapsible=True)

agraph(list(store.getNodes()), (store.getEdges()), config)

st.markdown('### Interact or not?')
drug_name = st.selectbox('Drug name', drugs_df['drug'].tolist())
# disease_id = st.text_input('Enter the identifier', value='Q11081', key='id')
drug_id = drugs_df[drugs_df['drug'] == drug_name]['id'].tolist()[0]
interacted_drug = st.text_input(value='imatinib', label='Possible interacted drug name')

id_query = f"""
SELECT distinct ?item ?itemLabel ?itemDescription WHERE{{ 
  ?item ?label "{interacted_drug}"@en.  
  # ?item wdt:P279 wdt:Q12136. # subclass of disease
  ?article schema:about ?item .
  ?article schema:inLanguage "en" .
  ?article schema:isPartOf <https://en.wikipedia.org/>.	
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}   
}}"""
results_df = query_wikidata(id_query)
results_df['id'] = results_df['item.value'].apply(lambda x: x.split('/')[-1])
results_df['name'] = results_df.apply(lambda x: f'{x["itemLabel.value"]}:{x["itemDescription.value"]}', axis=1)
interacted_name = st.selectbox('Map the possible interacted drug to Wikidata', results_df['name'].tolist())
interacted_drug_id = results_df[results_df['name'] == interacted_name]['id'].tolist()[0]
query = f"""
 SELECT DISTINCT *  WHERE {{
   wd:{drug_id} wdt:P769 wd:{interacted_drug_id}.
   wd:{drug_id} wdt:P31 wd:Q12140.
   wd:{interacted_drug_id} wdt:P31 wd:Q12140.
   SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}

  # OPTIONAL  {{?item2 rdfs:label ?label filter (lang(?label) = "en")}}
}}"""
do_interact = query_wikidata(query)
interacted_name = results_df[results_df['id'] == interacted_drug_id]['itemLabel.value'].tolist()[0]
if do_interact.shape[0] == 0:
    st.write(f"{drug_name} and {interacted_name} do not interact")
else:
    st.markdown(f"**{drug_name} and {interacted_name} interacts**")




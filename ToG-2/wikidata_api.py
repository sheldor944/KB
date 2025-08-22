# wikidata_api.py
import requests
import json
import time
from typing import Dict, List, Optional
import urllib.parse

class WikidataAPIClient:
    def __init__(self):
        self.base_url = "https://www.wikidata.org/w/api.php"
        self.sparql_url = "https://query.wikidata.org/sparql"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ToG-WikidataClient/1.0 (https://example.com/contact)'
        })
    
    def _make_request(self, url: str, params: dict, retries: int = 3) -> Optional[dict]:
        """Make API request with retries and rate limiting"""
        for attempt in range(retries):
            try:
                time.sleep(0.1)  # Rate limiting
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == retries - 1:
                    print(f"API request failed after {retries} attempts: {e}")
                    return None
                time.sleep(1)
        return None
    
    def _sparql_query(self, query: str) -> Optional[dict]:
        """Execute SPARQL query"""
        params = {
            'query': query,
            'format': 'json'
        }
        return self._make_request(self.sparql_url, params)
    
    def label2qid(self, label: str) -> str:
        """Convert label to QID"""
        params = {
            'action': 'wbsearchentities',
            'search': label,
            'language': 'en',
            'format': 'json',
            'limit': 1
        }
        print("\n\n\n\n\n\nIn the wikidata.py file and calling some label2qid function\n\n\n\n\n\n\n\n\n")
        
        result = self._make_request(self.base_url, params)
        if result and 'search' in result and len(result['search']) > 0:
            return result['search'][0]['id']
        return "Not Found!"
    
    def label2pid(self, label: str) -> str:
        """Convert property label to PID"""
        params = {
            'action': 'wbsearchentities',
            'search': label,
            'language': 'en',
            'format': 'json',
            'type': 'property',
            'limit': 10
        }
        
        result = self._make_request(self.base_url, params)
        print("these are the results of label2pid", result)
        if result and 'search' in result and len(result['search']) > 0:
            return result['search'][0]['id']
        return "Not Found!"
    # def label2pid(self, label: str) -> List[str]:
    #     """Convert property label to (possibly multiple) PIDs."""
    #     params = {
    #         'action': 'wbsearchentities',
    #         'search': label,
    #         'language': 'en',
    #         'format': 'json',
    #         'type': 'property',
    #         'limit': 10  # Search for more than 1 to catch ambiguous cases
    #     }

    #     result = self._make_request(self.base_url, params)
    #     print("these are the results of label2pid", result)
    #     pids = []
    #     if result and 'search' in result and len(result['search']) > 0:
    #         for item in result['search']:
    #             pids.append(item['id'])
    #     # Fallback if nothing is found
    #     if not pids:
    #         return []
    #     return pids
    def qid2label(self, qid: str) -> str:
        """Convert QID to label"""
        params = {
            'action': 'wbgetentities',
            'ids': qid,
            'languages': 'en',
            'format': 'json',
            'props': 'labels'
        }
        
        result = self._make_request(self.base_url, params)
        if result and 'entities' in result and qid in result['entities']:
            entity = result['entities'][qid]
            if 'labels' in entity and 'en' in entity['labels']:
                return entity['labels']['en']['value']
        return "Not Found!"
    
    def pid2label(self, pid: str) -> str:
        """Convert PID to label"""
        return self.qid2label(pid)  # Properties work the same way
    # Modifying this function a little bit to show the pid as well 
    def get_all_relations_of_an_entity(self, entity_qid: str) -> Dict[str, List]:
        print("in this function get_all_relations_of_an_entity")
        time.sleep(0.5)  # Rate limiting
        """Get all relations of an entity, with proper label and id structure for both head and tail."""
        query = f"""
        SELECT ?property ?propertyLabel ?value ?valueLabel WHERE {{
        wd:{entity_qid} ?property ?value .
        ?prop wikibase:directClaim ?property .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }}
        LIMIT 100
        """

        result = self._sparql_query(query)
        if not result or 'results' not in result:
            return {"head": [], "tail": []}
        # print("this is the results from the query get_all_relations_of_an_entity", result)
        head_relations = []
        tail_relations = []

        for binding in result['results']['bindings']:
            # Head relation (the property)
            if 'property' in binding:
                head_label = binding.get('propertyLabel', {}).get('value', binding['property']['value'])
                head_id    = binding['property']['value'].split('/')[-1] if '/' in binding['property']['value'] else binding['property']['value']
                head_relations.append({"label": head_label, "id": head_id})

            # Tail (the value/entity reached via this property)
            if 'value' in binding:
                tail_label = binding.get('valueLabel', {}).get('value', binding['value']['value'])
                tail_id    = binding['value']['value'].split('/')[-1] if '/' in binding['value']['value'] else binding['value']['value']
                tail_relations.append({"label": tail_label, "id": tail_id})
        
        # print(f"head_relations: {head_relations}")
        # print(f"tail_relations: {tail_relations}")

        return {"head": head_relations, "tail": tail_relations}
    # def get_all_relations_of_an_entity(self, entity_qid: str) -> Dict[str, List]:
    #     """
    #     Get all relations of an entity, including property label, property id, value label, and value id for both head and tail.
    #     Returns:
    #         {
    #             "head": [{"label":..., "id":..., "property_label":..., "property_id":...}],
    #             "tail": [...]
    #         }
    #     """
    #     print("in this function get_all_relations_of_an_entity")
    #     time.sleep(0.5)  # Rate limiting
        
    #     query = f"""
    #     SELECT ?property ?propertyLabel ?value ?valueLabel WHERE {{
    #     wd:{entity_qid} ?property ?value .
    #     ?prop wikibase:directClaim ?property .
    #     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    #     }}
    #     LIMIT 100
    #     """
    #     result = self._sparql_query(query)
    #     if not result or 'results' not in result:
    #         return {"head": [], "tail": []}
        
    #     head_relations = []
    #     tail_relations = []
    #     for binding in result['results']['bindings']:
    #         # always get these
    #         property_label = binding.get('propertyLabel', {}).get('value', binding['property']['value'])
    #         property_id = binding['property']['value'].split('/')[-1] if '/' in binding['property']['value'] else binding['property']['value']
    #         value_label = binding.get('valueLabel', {}).get('value', binding['value']['value'])
    #         value_id = binding['value']['value'].split('/')[-1] if '/' in binding['value']['value'] else binding['value']['value']
            
    #         # Head relation (from entity to value)
    #         head_relations.append({
    #             "label": property_label,         # old: property label
    #             "id": property_id,               # old: property id
    #             "property_label": property_label,
    #             "property_id": property_id,
    #             "value_label": value_label,
    #             "value_id": value_id,
    #         })
    #         # Tail: the value (for reverse navigation/filtering)
    #         tail_relations.append({
    #             "label": value_label,      # old: value label
    #             "id": value_id,            # old: value id
    #             "property_label": property_label,
    #             "property_id": property_id,
    #             "entity_label": value_label,
    #             "entity_id": value_id
    #         })

    #     print(f"head_relations: {head_relations}")
    #     print(f"tail_relations: {tail_relations}")

    #     return {"head": head_relations, "tail": tail_relations}
    
    def get_tail_values_given_head_and_relation(self, head_qid: str, relation_pid: str) -> List[str]:
        """Get tail values (literals) given head and relation"""
        query = f"""
        SELECT ?value WHERE {{
          wd:{head_qid} wdt:{relation_pid} ?value .
          FILTER(!isURI(?value))
        }}
        """
        
        result = self._sparql_query(query)
        if not result or 'results' not in result:
            return []
        
        values = []
        for binding in result['results']['bindings']:
            if 'value' in binding:
                values.append(str(binding['value']['value']))
        
        return values
    
    def get_external_id_given_head_and_relation(self, head_qid: str, relation_pid: str) -> List[str]:
        """Get external IDs given head and relation"""
        return self.get_tail_values_given_head_and_relation(head_qid, relation_pid)
    
    def get_wikipedia_link(self, qid: str) -> List[str]:
        """Get Wikipedia link for entity"""
        params = {
            'action': 'wbgetentities',
            'ids': qid,
            'format': 'json',
            'props': 'sitelinks'
        }
        
        result = self._make_request(self.base_url, params)
        if result and 'entities' in result and qid in result['entities']:
            entity = result['entities'][qid]
            if 'sitelinks' in entity and 'enwiki' in entity['sitelinks']:
                return [entity['sitelinks']['enwiki']['title']]
        return ["Not Found!"]
    
    def mid2qid(self, mid: str) -> str:
        """Convert Freebase MID to QID (basic implementation)"""
        # This requires a more complex mapping, for now return not found
        return "Not Found!"
    
    def get_tail_entities_given_head_and_relation(self, head_qid: str, relation_pid: str) -> Dict[str, List]:
        """Get tail entities given head and relation, with proper label/id structure."""
        query = f"""
        SELECT ?object ?objectLabel WHERE {{
        wd:{head_qid} wdt:{relation_pid} ?object .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
        }}
        """
        result = self._sparql_query(query)
        if not result or 'results' not in result:
            return {"head": [], "tail": []}
        
        head_entities = []
        tail_entities = []
        
        for binding in result['results']['bindings']:
            # For head, use the head_qid and label if you want (can be just a placeholder)
            head_label = self.qid2label(head_qid)
            head_entities.append({"label": head_label, "id": head_qid})

            # For tail, get label/id from SPARQL results
            if 'object' in binding:
                tail_label = binding.get('objectLabel', {}).get('value', binding['object']['value'])
                tail_id    = binding['object']['value'].split('/')[-1] if '/' in binding['object']['value'] else binding['object']['value']
                tail_entities.append({"label": tail_label, "id": tail_id})

        # Optionally deduplicate head_entities if they are repeated (since for each result they are the same)
        if head_entities:
            head_entities = [head_entities[0]]  # only keep a single head entity for clarity

        return {"head": head_entities, "tail": tail_entities}
    
    def find_property_ids_for_relations(self, entity_qid: str, relation_labels: list) -> dict:
        """
        For a Wikidata entity and a list of relation (value) labels, find the property ID (pid)
        that links the entity to a value with that label.

        Returns a mapping: {relation_label: property_id}
        """
        # Lowercase and strip all relations to make lookup easier
        search_labels = {r.lower().strip() for r in relation_labels}
        result_mapping = {}

        query = f"""
        SELECT ?property ?propertyLabel ?value ?valueLabel WHERE {{
        wd:{entity_qid} ?prop ?value .
        ?property wikibase:directClaim ?prop .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 500
        """

        result = self._sparql_query(query)
        if not result or 'results' not in result:
            return {}

        for binding in result['results']['bindings']:
            value_label = binding.get('valueLabel', {}).get('value', '').lower().strip()
            property_id = binding['property']['value'].split('/')[-1] if '/' in binding['property']['value'] else binding['property']['value']
            # For debugging:
            # print(f"{value_label} --> {property_id}")

            if value_label in search_labels:
                result_mapping[value_label] = property_id

        # Return user-provided label (original casing) mapped to property id.
        return {
            orig_label: result_mapping.get(orig_label.lower().strip(), "Not Found!")
            for orig_label in relation_labels
        }
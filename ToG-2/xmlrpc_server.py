# xmlrpc_server.py
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import threading
from wikidata_api import WikidataAPIClient

class WikidataXMLRPCServer:
    def __init__(self, port=8000):
        self.port = port
        self.api_client = WikidataAPIClient()
        self.server = None

    def label2qid(self, label: str) -> str:
        return self.api_client.label2qid(label)

    def label2pid(self, label: str) -> str:
        print("\n\n\n\n\n In the xmlrpc_server.py file and calling some label2pid function\n\n\n\n\n\n\n\n\n")
        return self.api_client.label2pid(label)

    def pid2label(self, pid: str) -> str:
        return self.api_client.pid2label(pid)

    def qid2label(self, qid: str) -> str:
        return self.api_client.qid2label(qid)

    def get_all_relations_of_an_entity(self, entity_qid: str):
        return self.api_client.get_all_relations_of_an_entity(entity_qid)

    def get_tail_entities_given_head_and_relation(self, head_qid: str, relation_pid: str):
        return self.api_client.get_tail_entities_given_head_and_relation(head_qid, relation_pid)

    def get_tail_values_given_head_and_relation(self, head_qid: str, relation_pid: str):
        return self.api_client.get_tail_values_given_head_and_relation(head_qid, relation_pid)

    def get_external_id_given_head_and_relation(self, head_qid: str, relation_pid: str):
        return self.api_client.get_external_id_given_head_and_relation(head_qid, relation_pid)

    def get_wikipedia_link(self, qid: str):
        return self.api_client.get_wikipedia_link(qid)

    def mid2qid(self, mid: str) -> str:
        return self.api_client.mid2qid(mid)
    # new added 
    def find_property_ids_for_relations(self, entity_qid: str, relation_labels: list) -> dict:
        print("in the server side call for find_property_ids_for_relations")
        return self.api_client.find_property_ids_for_relations(entity_qid, relation_labels)

    def start_server(self):
        """Start the XML-RPC server"""
        print(f"Starting Wikidata XML-RPC server on port {self.port}...")

        self.server = SimpleXMLRPCServer(("localhost", self.port), allow_none=True)
        # Register all Wikidata methods
        self.server.register_function(self.label2qid, 'label2qid')
        self.server.register_function(self.label2pid, 'label2pid')
        self.server.register_function(self.pid2label, 'pid2label')
        self.server.register_function(self.qid2label, 'qid2label')
        self.server.register_function(self.get_all_relations_of_an_entity, 'get_all_relations_of_an_entity')
        self.server.register_function(self.get_tail_entities_given_head_and_relation, 'get_tail_entities_given_head_and_relation')
        self.server.register_function(self.get_tail_values_given_head_and_relation, 'get_tail_values_given_head_and_relation')
        self.server.register_function(self.get_external_id_given_head_and_relation, 'get_external_id_given_head_and_relation')
        self.server.register_function(self.get_wikipedia_link, 'get_wikipedia_link')
        self.server.register_function(self.mid2qid, 'mid2qid')
        self.server.register_function(self.find_property_ids_for_relations, 'find_property_ids_for_relations')

        # Register system.* introspection methods
        self.server.register_introspection_functions()

        print(f"Wikidata XML-RPC server ready at http://localhost:{self.port}")
        self.server.serve_forever()

    def stop_server(self):
        """Stop the XML-RPC server"""
        if self.server:
            self.server.shutdown()

def start_server_in_background(port=8000):
    """Start server in a background thread"""
    server = WikidataXMLRPCServer(port)
    thread = threading.Thread(target=server.start_server, daemon=True)
    thread.start()
    return server, thread

if __name__ == "__main__":
    server = WikidataXMLRPCServer(8000)
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop_server()
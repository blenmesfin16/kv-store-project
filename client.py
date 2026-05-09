import requests
import random
import sys
import time

class KVClient:
    def __init__(self, nodes):
        self.nodes = nodes
        self.alive_nodes = nodes.copy()  # Track alive nodes
    
    def _get_alive_node(self):
        """Returns a random alive node"""
        if not self.alive_nodes:
            # If all nodes seem dead, reset and try all
            self.alive_nodes = self.nodes.copy()
        
        # Try up to 3 times to find an alive node
        for attempt in range(3):
            node = random.choice(self.alive_nodes)
            if self._is_alive(node):
                return node
            else:
                # Remove dead node from alive list
                if node in self.alive_nodes:
                    self.alive_nodes.remove(node)
                    print(f"Removed dead node: {node}")
        
        # If all nodes are dead
        return None
    
    def _is_alive(self, node):
        """Check if a node is alive"""
        try:
            resp = requests.get(f"http://{node}/ping/", timeout=1)
            return resp.status_code == 200
        except:
            return False
    
    def set(self, key, value):
        """Store a key-value pair"""
        node = self._get_alive_node()
        if node is None:
            return {"error": "No alive nodes available"}
        
        url = f"http://{node}/set/{key}/"
        try:
            resp = requests.post(url, json={"value": value}, timeout=5)
            return resp.json()
        except Exception as e:
            # Remove this node if it fails
            if node in self.alive_nodes:
                self.alive_nodes.remove(node)
            return {"error": str(e)}
    
    def get(self, key):
        """Retrieve a value by key"""
        node = self._get_alive_node()
        if node is None:
            return {"error": "No alive nodes available"}
        
        url = f"http://{node}/get/{key}/"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return {"error": "not found"}
        except Exception as e:
            # Remove this node if it fails
            if node in self.alive_nodes:
                self.alive_nodes.remove(node)
            return {"error": str(e)}

if __name__ == "__main__":
    nodes = ["localhost:8001", "localhost:8002", "localhost:8003"]
    client = KVClient(nodes)
    
    if len(sys.argv) < 2:
        print("Usage: python client.py set <key> <value> OR python client.py get <key>")
        sys.exit(1)
    
    if sys.argv[1] == "set" and len(sys.argv) == 4:
        result = client.set(sys.argv[2], sys.argv[3])
        print(result)
    elif sys.argv[1] == "get" and len(sys.argv) == 3:
        result = client.get(sys.argv[2])
        print(result)
    else:
        print("Invalid command")
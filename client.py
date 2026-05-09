import requests
import random
import sys

class KVClient:
    def __init__(self, nodes):
        self.nodes = nodes
    
    def set(self, key, value):
        node = random.choice(self.nodes)
        url = f"http://{node}/set/{key}/"
        try:
            resp = requests.post(url, json={"value": value}, timeout=5)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get(self, key):
        node = random.choice(self.nodes)
        url = f"http://{node}/get/{key}/"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return {"error": "not found"}
        except Exception as e:
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
    elif sys.command == "get" and len(sys.argv) == 3:
        result = client.get(sys.argv[2])
        print(result)
    else:
        print("Invalid command")
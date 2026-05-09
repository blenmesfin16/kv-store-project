import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.consistent_hash import ConsistentHash

# ========== CONFIGURATION ==========
my_port = os.environ.get('MY_PORT', '8000')
my_address = f"localhost:{my_port}"

# List of all nodes in the cluster
all_nodes = ["localhost:8001", "localhost:8002", "localhost:8003"]

# How many copies of each key to store
REPLICA_COUNT = 2

# In-memory storage
store = {}

# Initialize consistent hash ring
ch = ConsistentHash(all_nodes)


# ========== HELPER FUNCTIONS ==========
def get_replicas(key):
    """Returns list of nodes that should store this key"""
    primary = ch.get_node(key)
    replicas = [primary]
    for node in all_nodes:
        if node != primary and len(replicas) < REPLICA_COUNT:
            replicas.append(node)
    return replicas


# ========== MAIN API ENDPOINTS ==========
@csrf_exempt
@require_http_methods(["POST"])
def set_key(request, key):
    """Store a key-value pair"""
    try:
        data = json.loads(request.body)
        value = data['value']
    except:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    
    replicas = get_replicas(key)
    
    for node in replicas:
        if node == my_address:
            store[key] = value
        else:
            try:
                requests.post(
                    f"http://{node}/_internal_set/{key}/",
                    json={"value": value},
                    timeout=1
                )
            except:
                print(f"Warning: Could not replicate to {node}")
    
    return JsonResponse({
        "status": "ok",
        "key": key,
        "value": value,
        "stored_on": replicas
    })


@csrf_exempt
@require_http_methods(["POST"])
def internal_set(request, key):
    """Internal endpoint used for replication"""
    data = json.loads(request.body)
    store[key] = data['value']
    return JsonResponse({"status": "replicated"})


@require_http_methods(["GET"])
def get_key(request, key):
    """Retrieve a value by key"""
    target_node = ch.get_node(key)
    
    if target_node != my_address:
        try:
            resp = requests.get(f"http://{target_node}/get/{key}/", timeout=2)
            return JsonResponse(resp.json(), status=resp.status_code)
        except:
            for node in all_nodes:
                if node != target_node:
                    try:
                        resp = requests.get(f"http://{node}/get/{key}/", timeout=2)
                        if resp.status_code == 200:
                            return JsonResponse(resp.json())
                    except:
                        continue
            return JsonResponse({"error": "All nodes failed"}, status=500)
    
    if key in store:
        return JsonResponse({"key": key, "value": store[key]})
    return JsonResponse({"error": "Key not found"}, status=404)


@require_http_methods(["GET"])
def ping(request):
    """Health check endpoint"""
    return JsonResponse({"status": "alive", "port": my_port})


@csrf_exempt
@require_http_methods(["POST"])
def join_cluster(request):
    """Add a new node to the cluster"""
    try:
        data = json.loads(request.body)
        new_node = data.get('node')
        
        if not new_node:
            return JsonResponse({"error": "Missing 'node' field"}, status=400)
        
        if new_node not in all_nodes:
            all_nodes.append(new_node)
            ch.add_node(new_node)
            print(f"Node {new_node} joined the cluster. Current nodes: {all_nodes}")
        
        return JsonResponse({"status": "joined", "cluster_nodes": all_nodes})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_all_keys(request):
    """Return all keys stored on this node"""
    return JsonResponse({"keys": list(store.keys())})


@require_http_methods(["GET"])
def recover(request):
    """Recover keys that belong to this node from other nodes"""
    recovered_count = 0
    my_address_local = my_address
    
    for node in all_nodes:
        if node == my_address_local:
            continue
        
        try:
            resp = requests.get(f"http://{node}/get_all_keys/", timeout=2)
            keys_on_other = resp.json().get('keys', [])
            
            for key in keys_on_other:
                if ch.get_node(key) == my_address_local and key not in store:
                    value_resp = requests.get(f"http://{node}/get/{key}/", timeout=2)
                    if value_resp.status_code == 200:
                        store[key] = value_resp.json()['value']
                        recovered_count += 1
                        print(f"Recovered key: {key}")
        except:
            continue
    
    return JsonResponse({"recovered": recovered_count, "total_keys": len(store)})
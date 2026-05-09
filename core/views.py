import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.consistent_hash import ConsistentHash

my_port = os.environ.get('MY_PORT', '8000')
my_address = f"localhost:{my_port}"
all_nodes = ["localhost:8001", "localhost:8002", "localhost:8003"]
REPLICA_COUNT = 2
store = {}
ch = ConsistentHash(all_nodes)

def get_replicas(key):
    primary = ch.get_node(key)
    replicas = [primary]
    for node in all_nodes:
        if node != primary and len(replicas) < REPLICA_COUNT:
            replicas.append(node)
    return replicas

@csrf_exempt
@require_http_methods(["POST"])
def set_key(request, key):
    try:
        data = json.loads(request.body)
        value = data['value']
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    replicas = get_replicas(key)
    for node in replicas:
        if node == my_address:
            store[key] = value
        else:
            try:
                requests.post(f"http://{node}/_internal_set/{key}/", json={"value": value}, timeout=1)
            except:
                pass
    return JsonResponse({"status": "ok", "key": key, "value": value, "stored_on": replicas})

@csrf_exempt
@require_http_methods(["POST"])
def internal_set(request, key):
    data = json.loads(request.body)
    store[key] = data['value']
    return JsonResponse({"status": "replicated"})

@require_http_methods(["GET"])
def get_key(request, key):
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
    return JsonResponse({"status": "alive", "port": my_port})

@require_http_methods(["GET"])
def get_all_keys(request):
    return JsonResponse({"keys": list(store.keys())})

@require_http_methods(["GET"])
def recover(request):
    recovered_count = 0
    for node in all_nodes:
        if node == my_address:
            continue
        try:
            resp = requests.get(f"http://{node}/get_all_keys/", timeout=2)
            keys_on_other = resp.json().get('keys', [])
            for key in keys_on_other:
                if ch.get_node(key) == my_address and key not in store:
                    value_resp = requests.get(f"http://{node}/get/{key}/", timeout=2)
                    if value_resp.status_code == 200:
                        store[key] = value_resp.json()['value']
                        recovered_count += 1
        except:
            continue
    return JsonResponse({"recovered": recovered_count, "total_keys": len(store)})
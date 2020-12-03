import zmq
import time
import requests
import sys
import consul
from itertools import cycle

import hrw
import consistent_hashing

c = consul.Consul()
servers = []

def create_clients(servers):
    producers = {}
    context = zmq.Context()
    for server in servers:
        print(f"Creating a server connection to {server}...")
        producer_conn = context.socket(zmq.REQ)
        producer_conn.bind(server)
        producers[server] = producer_conn
    return producers


def generate_data_round_robin(servers):
    print("Starting...")
    producers = create_clients(servers)
    pool = cycle(producers.values())
    for num in range(10):
        data = { 'op': 'PUT', 'key': f'key-{num}', 'value': f'value-{num}' }
        print(f"Sending data:{data}")
        node = next(pool)
        node.send_json(data)
        message = node.recv_json()
        time.sleep(1)
    print("Done")


def generate_data_consistent_hashing_simple(servers):
    print("Starting Consistent Hashing...")
    producers = create_clients(servers)
    nodes = []
    for key, value in producers.items():
        nodes.append(consistent_hashing.Node(value, key))
    client_ring = consistent_hashing.ConsistentHashRing(nodes)

    print("Writing data, 1-10...")
    for num in range(10):
        data = {
            'op': 'PUT',
            'key': f'key-{num}',
            'value': f'value-{num}'
        }
        print(f"Sending data:{data}")
        node, _ = client_ring.get_node(data['key'])
        print(f"to node:{node.name}")
        node.node.send_json(data)
        message = node.node.recv_json()
        time.sleep(1)
    print("Done writing...")

    print("Reading previously written data...")
    for num in range(10):
        data = { 'op': 'GET_ONE', 'key': f'key-{num}' }
        print(f"Getting data:{data}")
        node, _= client_ring.get_node(data['key'])
        node.node.send_json(data)
        message = node.node.recv_json()
        print(f"data is {message}")
        print(f"from node: {node.name}")
        time.sleep(1)
    print("Done reading")

def generate_data_consistent_hashing_add_remove(servers, port_to_delete):
    print("Starting Consistent Hashing...")
    producers = create_clients(servers)
    nodes = []
    for key, value in producers.items():
        nodes.append(consistent_hashing.Node(value, key))
    client_ring = consistent_hashing.ConsistentHashRing(nodes)

    print("Writing data, 1-10...")
    for num in range(10):
        data = {
            'op': 'PUT',
            'key': f'key-{num}',
            'value': f'value-{num}'
        }
        print(f"Sending data:{data}")
        node, _ = client_ring.get_node(data['key'])
        print(f"to node:{node.name}")
        node.node.send_json(data)
        message = node.node.recv_json()
        time.sleep(1)
    print("Done writing...")

    print("Adding new node...")
    node = nodes[0]
    node.node.send_json({ 'op': 'ADD_NODE' })
    message = node.node.recv_json()
    print(f"new node successfully added, {message}")
    new_port = message['port']
    servers.append(f'tcp://127.0.0.1:{new_port}')
    producers = create_clients([f'tcp://127.0.0.1:{new_port}'])

    new_node = None
    for key, value in producers.items():
        new_node = consistent_hashing.Node(value, key)
        nodes.append(new_node)
    client_ring.add_node(new_node)
    node_next_to_new_node = client_ring.get_next_node(new_node)
    node_next_to_new_node.node.send_json({
        'op': 'GET_ALL'
    })
    message = node_next_to_new_node.node.recv_json()
    print(f"node that is next to newly added node have data {message}")
    content = message['collection']
    print("Balancing Data...")
    for item in content:
        cur_node, next_node = client_ring.get_node(item['key'])
        cur_node.node.send_json({
            'op': 'PUT',
            'key': item['key'],
            'value': item['value']
        })
        message = cur_node.node.recv_json()
        print(f"rebalanced data to new node, {message}")
        next_node.node.send_json({
            'op': 'DELETE',
            'key': item['key'],
        })
        message = next_node.node.recv_json()
        print(f"rebalanced data from old node, {message}")

    for num in range(11, 20):
        data = { 'op': 'PUT', 'key': f'key-{num}', 'value': f'value-{num}' }
        print(f"Sending data:{data}")
        node, _= client_ring.get_node(data['key'])
        node.node.send_json(data)
        message = node.node.recv_json()
        time.sleep(1)
    print("Done Rebalancing data")
    time.sleep(1)
    print("Done adding new node")


    print("Removing added node...")
    node = nodes[0]
    node_to_remove = None
    for k, mynode in client_ring.ring.items():
        if mynode.name== f"tcp://127.0.0.1:{port_to_delete}": #new_node.name:
            node_to_remove = mynode
    node_to_remove.node.send_json({
        'op': 'GET_ALL'
    })
    message = node_to_remove.node.recv_json()
    print(f"node to be removed has data: {message}")
    content = message['collection']
    for item in content:
        _, nextnode= client_ring.get_node(item['key'])
        nextnode.node.send_json({
            'op': 'PUT',
            'key': item['key'],
            'value': item['value']
        })
        message = nextnode.node.recv_json()
        print(f"data is rebalanced to next node: {message}")
        node_to_remove.node.send_json({
            'op': 'DELETE',
            'key': item['key'],
        })
        message = node_to_remove.node.recv_json()
        print(f"data is rebalanced from current node: {message}")

    nextnode.node.send_json({
        'op': 'GET_ALL'
    })
    message = nextnode.node.recv_json()
    print(f"now data is moved in the next node is {message}")
    node.node.send_json({'op': 'DELETE_NODE', 'key': port_to_delete})
    message = node.node.recv_json()
    print(f"deleted node {message}")
    time.sleep(1)
    print("Done removing")

def generate_data_hrw_hashing(servers):
    print("Starting...")
    ## TODO
    producers = create_clients(servers)
    counter = 1
    nodes = []
    for key, value in producers.items():
        nodes.append(hrw.Node(value, counter))
        counter +=1
    for num in range(10):
        data = { 'op': 'PUT', 'key': f'key-{num}', 'value': f'value-{num}' }
        print(f"Sending data:{data}")
        node = hrw.determine_responsible_node(nodes, data['key'])
        node.node.send_json(data)
        message = node.node.recv_json()
        time.sleep(1)
    print("Done")

if __name__ == "__main__":
    mode = 'ch-basic'
    port_to_delete = None
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    if len(sys.argv) >2:
        port_to_delete = int(sys.argv[2])
    services = c.agent.services()
    for key in services:
        if key.startswith('server-'):
            server_port = services[key]['Port']
            servers.append(f'tcp://127.0.0.1:{server_port}')
    print("Servers:", servers)
    if mode == 'rr':
        generate_data_round_robin(servers)
    elif mode == 'ch-basic':
        generate_data_consistent_hashing_simple(servers)
    elif mode == 'ch-add-remove':
        generate_data_consistent_hashing_add_remove(servers, port_to_delete)
    elif mode == 'hrw':
        generate_data_hrw_hashing(servers)
    else:
        print("invalid mode...")
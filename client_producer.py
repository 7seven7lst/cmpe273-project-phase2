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


def generate_data_consistent_hashing(servers):
    print("Starting...")
    ## TODO
    producers = create_clients(servers)
    nodes = []
    for key, value in producers.items():
        print("key is >>>",key, value)
        nodes.append(consistent_hashing.Node(value, key))
    client_ring = consistent_hashing.ConsistentHashRing(nodes)

    for num in range(10):
        data = { 'op': 'PUT', 'key': f'key-{num}', 'value': f'value-{num}' }
        print(f"Sending data:{data}")
        node, _= client_ring.get_node(data['key'])
        node.node.send_json(data)
        message = node.node.recv_json()
        time.sleep(1)
    print("Done writing")

    for num in range(10):
        data = { 'op': 'GET_ONE', 'key': f'key-{num}' }
        print(f"Getting data:{data}")
        node, _= client_ring.get_node(data['key'])
        node.node.send_json(data)
        message = node.node.recv_json()
        print("message is >>", message)
        time.sleep(1)
    print("Done reading")

    new_node_data = { 'op': 'ADD_NODE' }
    node = nodes[0]
    node.node.send_json(new_node_data)
    message = node.node.recv_json()
    print("message is >>>", message)
    new_port = message['port']
    servers.append(f'tcp://127.0.0.1:{new_port}')

    producers = create_clients([f'tcp://127.0.0.1:{new_port}'])
    new_node = None
    for key, value in producers.items():
        new_node = consistent_hashing.Node(value, key)
        nodes.append(new_node)
    client_ring.add_node(new_node)
    node_next_to_new_node = client_ring.get_next_node(new_node)
    print("node_next_to_new_node>>>",node_next_to_new_node)
    node_next_to_new_node.node.send_json({
        'op': 'GET_ALL'
    })
    message = node_next_to_new_node.node.recv_json()
    print("message here is >>>", message)
    content = message['collection']
    for item in content:
        mynode, nextnode= client_ring.get_node(item['key'])
        print("node.name>>>", mynode.name, item['key'], item['value'])
        mynode.node.send_json({
            'op': 'PUT',
            'key': item['key'],
            'value': item['value']
        })
        message = mynode.node.recv_json()
        print("messsage1 now is >>>", message)
        nextnode.node.send_json({
            'op': 'DELETE',
            'key': item['key'],
        })
        message = nextnode.node.recv_json()
        print("messsage2 now is >>>", message)

    for num in range(11, 20):
        data = { 'op': 'PUT', 'key': f'key-{num}', 'value': f'value-{num}' }
        print(f"Sending data:{data}")
        node, _= client_ring.get_node(data['key'])
        node.node.send_json(data)
        message = node.node.recv_json()
        time.sleep(1)
    print("Done writing")

    time.sleep(1)
    print("Done adding")


    node = nodes[0]
    node_to_remove = None
    print("client_ring.ring>>>", client_ring.ring)
    for k, mynode in client_ring.ring.items():
        if mynode.name=='tcp://127.0.0.1:2004':
            node_to_remove = mynode
    node_to_remove.node.send_json({
        'op': 'GET_ALL'
    })
    message = node_to_remove.node.recv_json()
    content = message['collection']
    for item in content:
        _, nextnode= client_ring.get_node(item['key'])
        nextnode.node.send_json({
            'op': 'PUT',
            'key': item['key'],
            'value': item['value']
        })
        message = nextnode.node.recv_json()
        print("messsage3 now is >>>", message)
        node_to_remove.node.send_json({
            'op': 'DELETE',
            'key': item['key'],
        })
        message = node_to_remove.node.recv_json()
        print("messsage4 now is >>>", message)

    nextnode.node.send_json({
        'op': 'GET_ALL'
    })
    message = nextnode.node.recv_json()
    print("now data is moved to next node>>>", message)
    node.node.send_json({'op': 'DELETE_NODE'})
    message = node.node.recv_json()
    print("message is >>>", message)
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
        time.sleep(1)
    print("Done")

if __name__ == "__main__":

    services = c.agent.services()
    for key in services:
        if key.startswith('server-'):
            server_port = services[key]['Port']
            servers.append(f'tcp://127.0.0.1:{server_port}')
    print("Servers:", servers)
    #generate_data_round_robin(servers)
    generate_data_consistent_hashing(servers)
    #generate_data_hrw_hashing(servers)
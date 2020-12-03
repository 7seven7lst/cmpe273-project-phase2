import zmq
import sys
import requests
import atexit
import urllib
import consul
import os, signal
from  multiprocessing import Process

c = consul.Consul()
storage_dict = {}

def server(port):
    context = zmq.Context()
    consumer = context.socket(zmq.REP)
    consumer.connect(f"tcp://127.0.0.1:{port}")

    while True:
        raw = consumer.recv_json()
        op, key, value = raw.get('op'), raw.get('key'), raw.get('value')
        print(f"Server_port={port}:key={key},value={value}")
        # FIXME: Implement to store the key-value data.
        if op == 'PUT':
            storage_dict[key] = value
            consumer.send_json({
                'key': key,
                'value': value
            })
        elif op == 'GET_ONE':
            print("GETTING ONE...", key)
            if storage_dict.get(key):
                consumer.send_json({
                    'key': key,
                    'value': storage_dict.get(key)
                })
            else:
                consumer.send_json({
                    'key': key,
                    'value': "Sorry, the key-value does not exist"
                })
        elif op == 'GET_ALL':
            print("GETTING ALL...")
            key_list = []
            for key, value in storage_dict.items():
                key_list.append({
                    'key': key,
                    'value': value
                })
            consumer.send_json({
                'collection': key_list
            })
        elif op == 'DELETE':
            storage_dict.pop(key, None)
            consumer.send_json({
                'key': key,
                'status': 'deleted'
            })
        elif op == 'ADD_NODE':
            print("add node...")
            services = c.agent.services()
            last_server = list(services.keys())[-1]
            last_server_port = int(services[last_server]['Port'])
            current_server = {'server': f"tcp://127.0.0.1:{server_port}", 'port': str(last_server_port+1)}

            p = Process(target=server, args=(last_server_port+1,))
            p.start()
            current_server['pid'] = p.pid
            register_server(current_server)
            consumer.send_json({'port': last_server_port+1})

        elif op == 'DELETE_NODE':
            print("delete node...")
            services = c.agent.services()
            last_server = list(services.keys())[-1]
            server_id = 'server-'+str(services[last_server]['Port'])
            c.agent.service.deregister(server_id)
            pid = services[server_id]['Address']
            os.kill(int(pid), signal.SIGSTOP)
            consumer.send_json({'port': services[last_server]['Port']})
            print("herer")

def register_server(server):
    c.agent.service.register(
        'server-'+server['port'],
        service_id='server-'+server['port'],
        tags=["primary", "v1"],
        address=str(server['pid']),
        port=int(server['port'])
    )

def deregister_server(server):
    c.agent.service.deregister('server-'+server['port'])

def exit_handler():
    services = c.agent.services()
    for key in services:
        if key.startswith('server-'):
            c.agent.service.deregister(key)

atexit.register(exit_handler)

if __name__ == "__main__":
    num_server = 1
    if len(sys.argv) > 1:
        num_server = int(sys.argv[1])
        print(f"num_server={num_server}")


    for each_server in range(num_server):
        server_port = "200{}".format(each_server)
        print(f"Starting a server at:{server_port}...")
        current_server = {'server': f"tcp://127.0.0.1:{server_port}", 'port': server_port}
        p = Process(target=server, args=(server_port,))
        p.start()
        current_server['pid'] = p.pid
        register_server(current_server)



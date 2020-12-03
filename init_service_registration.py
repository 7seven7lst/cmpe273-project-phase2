import consul
import sys

c = consul.Consul()

def register_server(server):
    c.agent.service.register(
        'server-'+server['port'],
        service_id='server-'+server['port'],
        tags=["primary", "v1"],
        port=int(server['port'])
    )

if __name__ == "__main__":
    num_server = 1
    if len(sys.argv) > 1:
        num_server = int(sys.argv[1])
        print(f"num_server={num_server}")

    for each_server in range(num_server):
        server_port = "200{}".format(each_server)
        print(f"Starting a server at:{server_port}...")
        current_server = {
            'server': f"tcp://127.0.0.1:{server_port}",
            'port': server_port
        }
        register_server(current_server)
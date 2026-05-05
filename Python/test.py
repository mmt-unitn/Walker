from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri
import time

agent = Agent("walker_inertia") 
agent.set_id("script1")

# Crypto
agent.set_key_dir("/home/miro/security")
agent.set_client_key_name("broker")
agent.set_server_key_name("broker")

agent.set_settings_timeout(2000) # 2 sec timeout
while agent.init(True) != 0:
    print("Cannot contact broker\n")
print(agent.settings()) # received from the broker

if agent.set_queue_size(1) != 0:
    print(agent.last_error())
    exit()

agent.connect()
agent.set_receive_timeout(2000) # Timeout for receiving messages, in ms

while(True):
    time.sleep(0.5)
    r = agent.receive(True)
    if r == MessageType.NONE:
        print("No message received\n")
    else:
        lm = agent.last_message()
        print(f"from topic {lm[0]} got: {lm[1]}\n")


agent.disconnect()
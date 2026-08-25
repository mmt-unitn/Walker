import sys, os
import subprocess
import time
mads_path = subprocess.check_output(["mads", "-p"], text=True).strip()
sys.path.append(os.path.join(mads_path, 'python'))

from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri

agent = Agent("ego_state_trajectory", "../mads.ini") # then the mads.ini file MUST have a python_agent section!
agent.set_id("python agent")
# Configure crypto settings
agent.set_key_dir("../keys")
agent.set_client_key_name("gui")
agent.set_server_key_name("broker")
agent.set_settings_timeout(2000) # 2 sec timeout
while agent.init(True) != 0:
    sys.stderr.write("Cannot contact broker\n")
    time.sleep(1)
print(agent.settings()) # received from the broker
agent.connect()


try:
    while True:
        agent.set_receive_timeout(5000) # Timeout for receiving messages in ms
        r = agent.receive()
        if r == MessageType.NONE:
            sys.stderr.write("No message received\n")
        else:
            #sys.stderr.write("Processing...\n")
            lm = agent.last_message()

            if lm[0] == "ego_state":
                received_ego_msg = lm[1]
                x_coord = received_ego_msg['ego_state']['x']
                y_coord = received_ego_msg['ego_state']['y']

                trajectory = [x_coord, y_coord, 0]
                
                trajectory_send_msg = {"trajectory": trajectory}
                agent.publish(trajectory_send_msg,"ego_state_trajectory")
            

except KeyboardInterrupt:
    print("Stopping...")

finally:
    agent.disconnect()

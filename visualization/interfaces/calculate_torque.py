import sys, os
import subprocess
mads_path = subprocess.check_output(["mads", "-p"], text=True).strip()
sys.path.append(os.path.join(mads_path, 'python'))

from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri

agent = Agent("calculate_torque", "../mads.ini") # then the mads.ini file MUST have a python_agent section!
agent.set_id("python agent")
# Configure crypto settings
agent.set_key_dir("../keys")
agent.set_client_key_name("gui")
agent.set_server_key_name("broker")
agent.set_settings_timeout(2000) # 2 sec timeout
if agent.init(True) != 0:
    sys.stderr.write("Cannot contact broker\n")
    sys.exit(1)
settings_received = agent.settings()
print(settings_received) # received from the broker
const = settings_received.get("torque_current_ratio", 0.6)
agent.connect()
agent.set_receive_timeout(5000) # Timeout for receiving messages in ms

try:
    while True:
        r = agent.receive()
        if r == MessageType.NONE:
            sys.stderr.write("No message received\n")
        else:
            lm = agent.last_message()

            if lm[0] == "driver":
                received_currents_msg = lm[1]
                driver_currents_msg = received_currents_msg['currents']

                l_current = float(driver_currents_msg['left']) / 10.0
                r_current = float(driver_currents_msg['right']) / 10.0

                l_torque = l_current * const * 100
                r_torque = -r_current * const * 100

                torque_send_msg = {"torque": {"right_calculated": r_torque, "left_calculated": l_torque, }}
                agent.publish(torque_send_msg,"calculated_torque")

except KeyboardInterrupt:
    print("Stopping...")

finally:
    agent.disconnect()

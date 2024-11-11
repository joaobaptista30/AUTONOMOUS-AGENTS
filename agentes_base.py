import asyncio
from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

shelters_list = [
    "shelter0@localhost", "shelter1@localhost", "shelter2@localhost",
    "shelter3@localhost", "shelter4@localhost", "shelter5@localhost",
    "shelter6@localhost", "shelter7@localhost", "shelter8@localhost",
    "shelter9@localhost"
]
suppliers_list = [
    "supplier0@localhost", "supplier1@localhost", "supplier2@localhost",
    "supplier3@localhost", "supplier4@localhost", "supplier5@localhost",
    "supplier6@localhost", "supplier7@localhost", "supplier8@localhost",
    "supplier9@localhost"
]
rescuers_list = [
    "rescuer0@localhost", "rescuer1@localhost", "rescuer2@localhost",
    "rescuer3@localhost", "rescuer4@localhost", "rescuer5@localhost",
    "rescuer6@localhost", "rescuer7@localhost", "rescuer8@localhost",
    "rescuer9@localhost"
]


class ShelterAgent(agent.Agent):
    def __init__(self, jid, password, people_capacity, num_supplies, position):
        super().__init__(jid, password)
        self.People_Capacity = people_capacity   # Total space available in shelter
        self.NUM_SUPPLIES = num_supplies         # Initial number of supplies available
        self.position = position                 # Position on the map
        self.current_supplies = num_supplies

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")

                # Handle requests from rescuers about shelter capacity
                if performative == "query_space":
                    response = Message(to=msg.sender.jid)  # Respond directly to sender's JID
                    response.set_metadata("performative", "inform")
                    response.body = f"Available space: {self.agent.People_Capacity}, Position: {self.agent.position}"
                    await self.send(response)
                    print(f"{self.agent.name}: Responded to {msg.sender.jid} with space info.")

                else:
                    print(f"{self.agent.name} received an unhandled message from {msg.sender.jid}: {msg.body}")

    class CheckSuppliesBehaviour(CyclicBehaviour):
        async def run(self):
            # Check if current supplies are less than half the capacity
            if self.agent.current_supplies < self.agent.NUM_SUPPLIES / 2:
                # Request supplies from all supplier agents (we assume their JIDs are known)
                print(f"{self.agent.name}: Supplies low ({self.agent.current_supplies}). Requesting resupply.")
                for i in range(len(suppliers_list)):  # Iterate over the suppliers_list
                    msg = Message(to=suppliers_list[i])  # Send request to each supplier
                    msg.set_metadata("performative", "request_supplies")
                    msg.body = "Need supplies"
                    await self.send(msg)
                    print(f"{self.agent.name}: Requested supplies from {suppliers_list[i]}")

            # Delay before checking again (for example, every 10 seconds)
            await asyncio.sleep(10)

    async def setup(self):
        print(f"Shelter Agent {self.name} started with capacity {self.People_Capacity} and supplies {self.NUM_SUPPLIES}.")
        self.add_behaviour(self.ReceiveMessageBehaviour())
        self.add_behaviour(self.CheckSuppliesBehaviour())


class SupplierAgent(agent.Agent):
    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.sender != self.agent.jid:
                if msg.get_metadata("performative") == "request_supplies":
                    print(f"{self.agent.name} received request from {msg.sender}: {msg.body}")
                    # Respond to the shelter agent with the supplies information
                    response = Message(to=msg.sender.jid)
                    response.set_metadata("performative", "inform")
                    response.body = "Supplying requested resources."
                    await self.send(response)
                    print(f"{self.agent.name}: Responded to {msg.sender.jid} with supply confirmation.")


    async def setup(self):
        print(f"Supplier Agent {self.name} started.")
        self.add_behaviour(self.ReceiveMessageBehaviour())


class RescueAgent(agent.Agent):
    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.sender != self.agent.jid:
                print(f"{self.agent.name} received message from {msg.sender}: {msg.body}")


    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        self.add_behaviour(self.ReceiveMessageBehaviour())


async def start_agents():
    # Create shelter agents
    for jid in shelters_list:
        password = "password"
        agent_instance = ShelterAgent(jid, password, people_capacity=100, num_supplies=50, position="Unknown")
        await agent_instance.start()

    # Create supplier agents
    for jid in suppliers_list:
        password = "password"
        agent_instance = SupplierAgent(jid, password)
        await agent_instance.start()

    # Create rescue agents
    for jid in rescuers_list:
        password = "password"
        agent_instance = RescueAgent(jid, password)
        await agent_instance.start()


async def main():
    await start_agents()  # Start agents based on predefined lists


if __name__ == "__main__":
    asyncio.run(main())

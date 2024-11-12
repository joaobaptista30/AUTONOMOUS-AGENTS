import asyncio
from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.behaviour import OneShotBehaviour

shelters_list = [
    "shelter0@localhost", "shelter1@localhost", "shelter2@localhost",
    "shelter3@localhost", "shelter4@localhost", "shelter5@localhost",
    "shelter6@localhost"
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
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.max_people = 100            # Max people capacity
        self.max_supplies = 500          # Max supplies capacity
        self.position = position         # Position on the map
        self.current_supplies = self.max_supplies
        self.flag = True                 # Control flag for supply requests

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "query_space":
                    response = Message(to=msg.sender.jid)
                    response.set_metadata("performative", "inform")
                    response.body = f"Available space: {self.agent.max_people}, Position: {self.agent.position}"
                    await self.send(response)
                    print(f"{self.agent.name}: Responded to {msg.sender.jid} with space info.")
                elif performative == "inform" and msg.body == "Supplying requested resources.":
                    self.agent.current_supplies += 50  # Example increment for delivered supplies
                    print(f"{self.agent.name}: Supplies replenished. Current supplies: {self.agent.current_supplies}")
                    self.agent.flag = True  # Reset request flag after resupply
                else:
                    print(f"{self.agent.name} received an unhandled message from {msg.sender.jid}: {msg.body}")

    class AskSuppliesBehavior(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.name}: Supplies low ({self.agent.current_supplies}). Requesting supplies.")
            for supplier_jid in suppliers_list:
                msg = Message(to=supplier_jid)
                msg.set_metadata("performative", "request_supplies")
                msg.body = "Need supplies"
                await self.send(msg)
                print(f"{self.agent.name}: Requested supplies from {supplier_jid}")

    class CheckSuppliesBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.flag and self.agent.current_supplies <= self.agent.max_supplies / 2:
                self.agent.flag = False  # Lock further requests until resupply occurs
                self.agent.add_behaviour(self.agent.AskSuppliesBehavior())
            await asyncio.sleep(10)

    async def setup(self):
        print(f"Shelter Agent {self.name} started with max people {self.max_people} and supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessageBehaviour())
        self.add_behaviour(self.CheckSuppliesBehaviour())


class SupplierAgent(agent.Agent):
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position
        self.max_supplies = 250
        self.num_supplies = self.max_supplies  # Current available supplies

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("performative") == "request_supplies":
                print(f"{self.agent.name} received request from {msg.sender}: {msg.body}")

                # Run the decision behavior and await completion
                deciding_behaviour = self.agent.DecidingWhosGoing()
                self.agent.add_behaviour(deciding_behaviour)
                await deciding_behaviour.join()  # Wait for decision-making

                # Check the decision to supply
                if deciding_behaviour.should_supply:
                    # Send response to shelter agent with supply confirmation
                    response = Message(to=msg.sender.jid)
                    response.set_metadata("performative", "inform")
                    response.body = "Supplying requested resources."
                    await self.send(response)
                    print(f"{self.agent.name}: Responded to {msg.sender.jid} with supply confirmation.")
                    # Optionally decrement supplies if fulfilling the request
                    self.agent.num_supplies -= 50  # Example decrement amount
                    print(f"{self.agent.name}: Supplies left after response: {self.agent.num_supplies}")
                else:
                    print(f"{self.agent.name}: Not supplying to {msg.sender.jid} this time.")

    class DecidingWhosGoing(OneShotBehaviour):
        async def run(self):
            # Decide to supply based on availability
            self.should_supply = self.agent.num_supplies > 0  # Ensure agent has enough supplies

    async def setup(self):
        print(f"Supplier Agent {self.name} started with max supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessageBehaviour())


class RescueAgent(agent.Agent):
    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                print(f"{self.agent.name} received message from {msg.sender}: {msg.body}")

    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        self.add_behaviour(self.ReceiveMessageBehaviour())
async def start_agents():
    shelters = []
    # Create shelter agents
    for jid in shelters_list:
        password = "password"
        agent_instance = ShelterAgent(jid, password, position="Unknown")
        shelters.append(agent_instance)
        await agent_instance.start()

    suppliers = []
    # Create supplier agents
    for jid in suppliers_list:
        password = "password"
        agent_instance = SupplierAgent(jid, password, position="Unknown")
        suppliers.append(agent_instance)
        await agent_instance.start()

    rescuers = []
    # Create rescue agents
    for jid in rescuers_list:
        password = "password"
        agent_instance = RescueAgent(jid, password)
        rescuers.append(agent_instance)
        await agent_instance.start()

    return shelters, suppliers, rescuers

async def main():
    shelters, suppliers, rescuers = await start_agents()  # Start agents based on predefined lists

    try:
        await asyncio.sleep(30)
    finally:
        for agent in shelters + suppliers + rescuers:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())

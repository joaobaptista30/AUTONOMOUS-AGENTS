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
        self.max_people = 100
        self.num_people = 0
        self.max_supplies = 500
        self.position = position
        self.current_supplies = self.max_supplies
        self.flag = True

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
                    self.agent.current_supplies += 50
                    print(f"{self.agent.name}: Supplies replenished. Current supplies: {self.agent.current_supplies}")
                    self.agent.flag = True
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
                self.agent.flag = False
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
        self.num_supplies = self.max_supplies

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "request_supplies":
                    print(f"{self.agent.name} received request from {msg.sender}: {msg.body}")
                    deciding_behaviour = self.agent.DecidingWhosGoing()
                    self.agent.add_behaviour(deciding_behaviour)
                    await deciding_behaviour.join()

                    if deciding_behaviour.should_supply:
                        response = Message(to=msg.sender.jid)
                        response.set_metadata("performative", "inform")
                        response.body = "Supplying requested resources."
                        await self.send(response)
                        print(f"{self.agent.name}: Responded to {msg.sender.jid} with supply confirmation.")
                        self.agent.num_supplies -= 50
                        print(f"{self.agent.name}: Supplies left after response: {self.agent.num_supplies}")
                    else:
                        print(f"{self.agent.name}: Not supplying to {msg.sender.jid} this time.")
                else:
                    print(f"{self.agent.name} received an unhandled message from {msg.sender.jid}: {msg.body}")

    class DecidingWhosGoing(OneShotBehaviour):
        async def run(self):
            self.should_supply = self.agent.num_supplies > 0

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
    for jid in shelters_list:
        password = "password"
        agent_instance = ShelterAgent(jid, password, position="Unknown")
        shelters.append(agent_instance)
        await agent_instance.start()

    suppliers = []
    for jid in suppliers_list:
        password = "password"
        agent_instance = SupplierAgent(jid, password, position="Unknown")
        suppliers.append(agent_instance)
        await agent_instance.start()

    rescuers = []
    for jid in rescuers_list:
        password = "password"
        agent_instance = RescueAgent(jid, password)
        rescuers.append(agent_instance)
        await agent_instance.start()

    return shelters, suppliers, rescuers

async def main():
    shelters, suppliers, rescuers = await start_agents()

    try:
        await asyncio.sleep(30)
    finally:
        for agent in shelters + suppliers + rescuers:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())

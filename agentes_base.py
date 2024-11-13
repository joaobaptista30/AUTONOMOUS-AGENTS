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
                    response.body = f"Available space: {self.agent.max_people - self.agent.num_people}, Position: {self.agent.position}"
                    await self.send(response)
                    print(f"{self.agent.name}: Responded to {msg.sender.jid} with space info.")
                elif performative == "inform":
                    if msg.body == "Supplying requested resources.":
                        self.agent.current_supplies += 50
                        print(f"{self.agent.name}: Supplies replenished. Current supplies: {self.agent.current_supplies}")
                        self.agent.flag = True
                    if msg.body == "delivering people:":
                        num_delivering = int(msg.body.split(":")[1].strip())
                        if self.agent.num_people + num_delivering <= self.agent.max_people:
                            self.agent.num_people += num_delivering
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
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position
        self.capacity = 25
        self.civilians = 0
        self.choices = []  # Store shelter options with space details

    class AskShelter(OneShotBehaviour):
        async def run(self):
            for agent_jid in shelters_list:
                message = Message(to=agent_jid)
                message.set_metadata("performative", "query_space")
                message.body = "How much space do you have?"
                await self.send(message)
                print(f"{self.agent.name} sent space query to {agent_jid}")

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "inform":
                    body_content = msg.body.split(", ")
                    available_space = int(body_content[0].split(": ")[1])
                    position = body_content[1].split(": ")[1]

                    # Save each shelter's info in choices
                    self.agent.choices.append({
                        "jid": msg.sender.jid,
                        "available_space": available_space,
                        "position": position
                    })
                    print(f"{self.agent.name} added {msg.sender.jid} to choices with space: {available_space}, position: {position}")

    async def chooseShelter(self):
        if self.choices:
            sorted_choices = sorted(self.choices, key=lambda x: x["available_space"], reverse=True)
            choice = sorted_choices[0]
            print(f"{self.name} chose shelter {choice['jid']} with space {choice['available_space']}")
            return choice
        else:
            print(f"{self.name} has no shelter choices available.")
            return None

    class DeliveringPeople(OneShotBehaviour):
        async def run(self):
            choice = self.agent.chooseShelter()
            if choice:
                message = Message(to=choice["jid"])
                message.set_metadata("performative", "inform")
                message.body = f"Delivering people: {self.agent.civilians}"
                await self.send(message)
                print(f"{self.agent.name} sent delivery message to {choice['jid']} with {self.agent.civilians} civilians.")
            else:
                print(f"{self.agent.name} has no valid shelter choice for delivery.")

    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        # Start behaviors in sequence: ask for space, then wait, then deliver people
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
        agent_instance = RescueAgent(jid, password, position="Unknown")
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

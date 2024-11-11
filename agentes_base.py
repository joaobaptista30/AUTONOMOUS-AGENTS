import asyncio
from spade import agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message

class ShelterAgent(agent.Agent):
    class SendMessageBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.target_type is not None and self.agent.target_count > 0:
                for i in range(self.agent.target_count):
                    msg = Message(to=f"{self.agent.target_type}{i}@localhost")
                    msg.set_metadata("performative", "inform")
                    msg.body = f"Requesting {self.agent.target_type} to point A"

                    await self.send(msg)
                    print(f"{self.agent.name}: Message sent to {self.agent.target_type}{i}@localhost")
                self.agent.target_type = None
                self.agent.target_count = 0

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.sender != self.agent.jid:
                print(f"{self.agent.name} received message from {msg.sender}: {msg.body}")

    async def setup(self):
        print(f"Shelter Agent {self.name} started.")
        self.target_type = None
        self.target_count = 0
        self.add_behaviour(self.SendMessageBehaviour())
        self.add_behaviour(self.ReceiveMessageBehaviour())

    def update_target(self, target_type, target_count):
        self.target_type = target_type
        self.target_count = target_count
        print(f"{self.name}: Target updated to {self.target_type} with count {self.target_count}")

class SupplierAgent(agent.Agent):
    class SendMessageBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.target_type is not None and self.agent.target_count > 0:
                for i in range(self.agent.target_count):
                    msg = Message(to=f"{self.agent.target_type}{i}@localhost")
                    msg.set_metadata("performative", "inform")
                    msg.body = f"Requesting {self.agent.target_type} to assist"

                    await self.send(msg)
                    print(f"{self.agent.name}: Message sent to {self.agent.target_type}{i}@localhost")

                    self.agent.target_type = None
                    self.agent.target_count = 0

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.sender != self.agent.jid:
                print(f"{self.agent.name} received message from {msg.sender}: {msg.body}")

    async def setup(self):
        print(f"Supplier Agent {self.name} started.")
        self.target_type = None
        self.target_count = 0
        self.add_behaviour(self.SendMessageBehaviour())
        self.add_behaviour(self.ReceiveMessageBehaviour())

    def update_target(self, target_type, target_count):
        self.target_type = target_type
        self.target_count = target_count
        print(f"{self.name}: Target updated to {self.target_type} with count {self.target_count}")


class RescueAgent(agent.Agent):
    class SendMessageBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.target_type is not None and self.agent.target_count > 0:
                for i in range(self.agent.target_count):
                    msg = Message(to=f"{self.agent.target_type}{i}@localhost")
                    msg.set_metadata("performative", "inform")
                    msg.body = f"Requesting {self.agent.target_type} to rescue operation"

                    await self.send(msg)
                    print(f"{self.agent.name}: Message sent to {self.agent.target_type}{i}@localhost")

                    self.agent.target_type = None
                    self.agent.target_count = 0

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.sender != self.agent.jid:
                print(f"{self.agent.name} received message from {msg.sender}: {msg.body}")

    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        self.target_type = None
        self.target_count = 0
        self.add_behaviour(self.SendMessageBehaviour())
        self.add_behaviour(self.ReceiveMessageBehaviour())


    def update_target(self, target_type, target_count):
        self.target_type = target_type
        self.target_count = target_count
        print(f"{self.name}: Target updated to {self.target_type} with count {self.target_count}")

async def start_agents(num_shelter, num_supplier, num_rescue):
    list_shelter = []
    list_supplier = []
    list_rescue = []

    for i in range(num_shelter):
        jid = f"shelter{i}@localhost"
        password = "password"
        agent_instance = ShelterAgent(jid, password)
        list_shelter.append(agent_instance)
        await agent_instance.start()

    for j in range(num_supplier):
        jid = f"supplier{j}@localhost"
        password = "password"
        agent_instance = SupplierAgent(jid, password)
        list_supplier.append(agent_instance)
        await agent_instance.start()

    for k in range(num_rescue):
        jid = f"rescue{k}@localhost"
        password = "password"
        agent_instance = RescueAgent(jid, password)
        list_rescue.append(agent_instance)
        await agent_instance.start()

    return list_shelter, list_supplier, list_rescue

async def main():
    num_shelter = 10
    num_supplier = 10
    num_rescue = 10

    list_shelter, list_supplier, list_rescue = await start_agents(num_shelter, num_supplier, num_rescue)

    list_shelter[0].update_target("shelter",1)

    try:
        await asyncio.sleep(30)
    finally:
        for agent in list_shelter:
            await agent.stop()
        for agent in list_supplier:
            await agent.stop()
        for agent in list_rescue:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())

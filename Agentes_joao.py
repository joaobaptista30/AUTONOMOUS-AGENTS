import asyncio
from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.behaviour import OneShotBehaviour


class ShelterAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.max_people = 100
        self.num_people = 0
        self.max_supplies = 500
        self.position = position
        self.current_supplies = self.max_supplies
        self.flag = True
        self.env = env

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
            for supplier_jid in self.agent.env.agents_contact["supplier"]:
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


class RescueAgent(agent.Agent):
    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                print(f"{self.agent.name} received message from {msg.sender}: {msg.body}")

    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        self.add_behaviour(self.ReceiveMessageBehaviour())


class CivilAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.home = position  # casa de origem, onde vai depois dos danos (guardar pointer para o bloco ou nome do bloco?)
        self.position = position  # posicao atual
        self.env = env
        self.deslocado = False  # saber se esta em abrigo ou em casa

    class AnalyzeDanger(CyclicBehaviour):
        async def run(self):
            if self.agent.env.blocks[self.agent.location].damage:
                # pedir ajuda para rescue
                # rescue vai decidir se precisa de apenas ajuda medica/comida ou abrigo
                self.agent.add_behaviour(self.agent.AskResque())

            elif self.agent.env.blocks[self.agent.home].damage == 0 and self.agent.deslocado:
                # agente retorna a casa mas precisa de transporte
                ...

    class AskResque(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.name}: Precisa de ajuda no bloco {self.agent.location}")
            ...

    async def setup(self):
        print(f"Civil Agent {self.name} started.")
        self.add_behaviour(self.AnalyzeDanger())


async def start_agents():
    shelters = []
    for jid in shelters_list:
        password = "password"
        agent_instance = ShelterAgent(jid, password, position="Unknown")
        shelters.append(agent_instance)
        await agent_instance.start()

    rescuers = []
    for jid in rescuers_list:
        password = "password"
        agent_instance = RescueAgent(jid, password)
        rescuers.append(agent_instance)
        await agent_instance.start()

    return shelters, rescuers


async def main():
    shelters, rescuers = await start_agents()

    try:
        await asyncio.sleep(30)
    finally:
        for agent in shelters + rescuers:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())

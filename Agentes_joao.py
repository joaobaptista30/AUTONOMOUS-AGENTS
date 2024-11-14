import asyncio
import random
from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.behaviour import OneShotBehaviour
from environment import load_env
from algorithms import dijkstra_min_distance

'''
TODO:
    adicionar logica para o melhor shelter de abrigo ao civil
    adicionar logica para quando apenas precisa de mantimentos
'''


class ShelterAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.max_people = 100
        self.num_people = 0
        self.max_supplies = 500
        self.current_supplies = self.max_supplies
        self.position = position
        self.env = env
        self.flag = True

    class ReceiveMessage(CyclicBehaviour):
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

    class AskSupplies(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.name}: Supplies low ({self.agent.current_supplies}). Requesting supplies.")
            for supplier_jid in self.agent.env.agents_contact["supplier"]:
                msg = Message(to=supplier_jid)
                msg.set_metadata("performative", "request_supplies")
                msg.body = "Need supplies"
                await self.send(msg)
                print(f"{self.agent.name}: Requested supplies from {supplier_jid}")

    class CheckSupplies(CyclicBehaviour):
        async def run(self):
            if self.agent.flag and self.agent.current_supplies <= self.agent.max_supplies / 2:
                self.agent.flag = False
                self.agent.add_behaviour(self.agent.AskSupplies())
            await asyncio.sleep(10)

    async def setup(self):
        print(f"Shelter Agent {self.name} started with max people {self.max_people} and supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessage())
        self.add_behaviour(self.CheckSupplies())


class RescuerAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.position = position  # referencia para o block atual
        self.env = env
        self.transp_space = 5
        self.ocupied = False

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=15)
            if msg:
                if self.agent.ocupied:
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "ocupied")
                    response.body = f""
                    await self.send(response)
                    return
                # print(f"{self.agent.name} received message from {msg.sender}\nBody: {msg.body}")
                performative = msg.get_metadata("performative")
                if performative == 'request_rescue':
                    block_name = msg.body.split(" ")[-1]
                    print(f"{self.agent.name} rescuer vai considerar para o civil {block_name}")

                    if (self.agent.env.blocks[block_name].zone != self.agent.position.zone and
                            self.agent.env.blocks[block_name].zone not in self.agent.position.adj_zone):
                        print("estou longe vou ignorar")
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "far_away")
                        response.body = f""
                        await self.send(response)
                        return  # esta fora do alcance de civil

                    print("estou na area vou responder")
                    bid = dijkstra_min_distance(self.agent.env, self.agent.position.name, block_name)
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "bid")
                    response.body = f"Estou a uma distancia de {bid}"
                    await self.send(response)
                elif performative == 'confirm_rescue':
                    # vamos mover ate ao local do civil
                    # depois vamos identificar se é preciso deslocar o civil ou pedir mantimentos
                    self.agent.ocupied = True
                    timer_ate_block = int(msg.body.split(" ")[-1])
                    self.agent.position = self.agent.env.blocks[msg.body.split(" ")[0]]
                    await asyncio.sleep(timer_ate_block)
                    resp = Message(to=str(msg.sender))

                    if self.agent.position.damage > 3:  # vamos deslocar para um shelter
                        print("vamos para um shelter")
                        # funcao para identificar o shelter (comunicar com os shelters e saber o mais perto com capacidade)
                        shelter = "AH"
                        dist_shelter = 10

                        resp.set_metadata("performative", "move_shelter")
                        resp.body = f"{dist_shelter} distancia para o shelter {shelter}"
                        await self.send(resp)
                        await asyncio.sleep(dist_shelter)

                        self.agent.ocupied = False
                        self.agent.position = self.agent.env.blocks[shelter]
                    else:  # vamos pedir mantimentos
                        print("vais receber mantimentos")
                        self.agent.position.damage = 0  # damage = 0 pois os rescuers ja ajudaram e nao foi um dano severo para precisar de tempo a recuperar


                        resp.body = f""

                elif performative == 'request_transport' and not self.agent.ocupied:
                    ...
                elif performative == 'confirm_transport':
                    ...

    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        self.add_behaviour(self.ReceiveMessage())


class CivilAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.home = position  # casa de origem, onde vai depois dos danos (guardar referencia para o block)
        self.position = position  # referencia para posicao atual
        self.env = env
        self.deslocado = False  # saber se esta em abrigo ou em casa
        self.pedido_realizado = False

    class AnalyzeDanger(CyclicBehaviour):
        async def run(self):
            # completo ?
            if self.agent.position.damage and self.agent.position.block_type != 'shelter' and not self.agent.pedido_realizado:
                # pedir ajuda para rescue
                # rescue vai decidir se precisa de apenas ajuda medica/comida ou abrigo
                self.agent.add_behaviour(self.agent.AskRescue())
                self.agent.pedido_realizado = True

            # por fazer
            elif self.agent.home.damage == 0 and self.agent.deslocado and not self.agent.pedido_realizado:
                # agente retorna a casa mas precisa de transporte
                # mandar mensagem ao shelter para ele fazer request a um rescuer para transporte
                self.agent.pedido_realizado = True

    class AskRescue(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.name}: Precisa de ajuda no block {self.agent.position.name}")
            best_resc = ""
            best_dist = float('inf')
            for rescuer_jid in self.agent.env.agents_contact["rescuer"]:
                msg = Message(to=rescuer_jid)
                msg.set_metadata("performative", "request_rescue")
                msg.body = f"Need Rescue at {self.agent.position.name}"
                await self.send(msg)

                response = await self.receive(timeout=15)  # sera suficiente ? | esta a ficar com o mesmo body que a msg ? wtf
                # o civil vai indentificar qual o melhor rescuer
                if response and response.get_metadata("performative") == "bid":
                    print(f"resposta do {rescuer_jid} foi {response.body}")
                    if int(response.body.split(" ")[-1]) < best_dist:  # mais perto melhor
                        best_resc = str(response.sender)
                        best_dist = int(response.body.split(" ")[-1])

            if best_dist == float("inf"):
                self.agent.pedido_realizado = False
                print(f"Nenhum rescuer disponivel para {self.agent.name}\nA pedir ajuda novamente dentro de 3 seg")
                await asyncio.sleep(3)
                return

            print(f"best rescuer: {best_resc} com a menor dist = {best_dist}")
            # informar qual e o melhor
            msg = Message(to=best_resc)
            msg.set_metadata("performative", "confirm_rescue")
            msg.body = f"{self.agent.position.name} vir ate aqui no tempo informado {best_dist}"
            await self.send(msg)

            # awd
            indicacoes_rescuer = await self.receive(timeout=best_dist+3)
            if indicacoes_rescuer and self.agent.pedido_realizado:
                performative = indicacoes_rescuer.get_metadata("performative")

                if performative == "move_shelter":
                    nome_shelter = indicacoes_rescuer.body.split(' ')[-1]
                    print(f"A mover {self.agent.name} para o shelter {nome_shelter}")
                    self.agent.position = self.agent.env.blocks[nome_shelter]
                    dist = int(indicacoes_rescuer.body.split(" ")[0])
                    self.agent.deslocado = True
                    await asyncio.sleep(dist)
                    self.agent.pedido_realizado = False

                elif performative == 'get_supply':
                    ...

    async def setup(self):
        print(f"Civil Agent {self.name} started.")
        self.add_behaviour(self.AnalyzeDanger())


async def populate_city(env):
    """
    there are 5 types of blocks
    house: will have 3 to 5 civil agents
    condo: will have 8 to 12 civil agents
    shelter: location of shelter agent
    supply_center: depo central com mantimentos para os supply agents
    empty: just an empty space
    """

    for block in env.blocks.values():
        if block.block_type == 'house':  # iniciar civis
            n_civil = random.choice([3, 4, 5])
            ...
        elif block.block_type == 'condo':  # iniciar civis
            n_civil = random.choice([8, 9, 10, 11, 12])
            ...
        elif block.block_type == 'shelter':  # iniciar shelters
            ...
        elif block.block_type == 'supply_center':  # iniciar supplies
            ...
        else:
            ...


async def main():
    environment = load_env("./city_desing.txt")

    # iniciar agents manualmente para teste
    civil1 = CivilAgent("civil1@localhost", "password", environment.blocks["AE"], environment)
    civil2 = CivilAgent("civil2@localhost", "password", environment.blocks["GG"], environment)

    rescuer1 = RescuerAgent("rescuer1@localhost", "password", environment.blocks["AF"], environment)
    rescuer2 = RescuerAgent("rescuer2@localhost", "password", environment.blocks["FA"], environment)

    shelter1 = ShelterAgent("shelter1@localhost", "password", environment.blocks["AH"], environment)
    shelter2 = ShelterAgent("shelter2@localhost", "password", environment.blocks["GH"], environment)

    environment.agents_contact["rescuer"] = ["rescuer1@localhost", "rescuer2@localhost"]
    environment.agents_contact["shelter"] = ["shelter1@localhost", "shelter2@localhost"]

    # Start all agents
    await rescuer1.start(auto_register=True)
    await rescuer2.start(auto_register=True)
    await shelter1.start(auto_register=True)
    await shelter1.start(auto_register=True)
    await civil1.start(auto_register=True)
    await civil2.start(auto_register=True)
    print()

    environment.blocks["AE"].damage = 10
    environment.blocks["GG"].damage = 10

    # Run the simulation for some time to allow interactions
    await asyncio.sleep(60)  # Adjust as needed to observe behavior

    print(civil1.position.name)
    print(civil2.position.name)
    # Stop agents after the test
    await civil1.stop()
    await civil2.stop()

    await rescuer1.stop()
    await rescuer2.stop()

    await shelter1.stop()
    await shelter2.stop()


if __name__ == "__main__":
    asyncio.run(main())

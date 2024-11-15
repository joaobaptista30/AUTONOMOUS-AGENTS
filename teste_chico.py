import asyncio
import math
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
"ASK FOR SUPPLIES FALTA DECIDIR QUAL É CONSIDERADO O MELHOR E MANDAR MNS A CONFIRMAR"
"rever linha 173, ha lista civilians?"
"linha 196 verificar se é assim e toda a logistica dps de confirmar o resgate "
"rever civis"

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
        self.needed_supplies = self.max_supplies - self.current_supplies

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "query_ref":
                    response = Message(to=msg.sender.jid)
                    response.set_metadata("performative", "inform")
                    response.body = f"Available space: {self.agent.max_people}, Position: {self.agent.position}"
                    await self.send(response)
                    print(f"{self.agent.name}: Responded to {msg.sender.jid} with space info.")
                elif performative == "inform":
                    body = msg.body
                    if body == "Supplying requested resources.":
                        if msg.sender.num_suplplies() < self.agent.max_supplies - self.agent.current_supplies:
                            self.agent.current_supplies += msg.sender.num_supplies
                        else:
                            self.agent.current_supplies = self.agent.max_supplies
                        response = Message(to=msg.sender.jid)
                        response.set_metadata("performative", "confirm" )
                        response.body = "Supplies received"
                        self.agent.flag = True
                    if body == "Delivering civilians":
                        return
                    else:
                        return
                elif performative == "confirm":
                    body = msg.body
                    if body.split()[-1] == "civilian":
                        self.agent.num_people += body.split()[-2]
                else:
                    print(f"{self.agent.name} received an unhandled message from {msg.sender.jid}: {msg.body}")

    class AskSupplies(OneShotBehaviour):
        async def run(self):
            options = {}
            self.agent.needed_supplies = self.agent.max_supplies - self.agent.num_supplies
            for agent_jid in self.agent.env.agents_contact["supply"]:
                request=Message(to=agent_jid)
                request.set_metadata("performative", "request_ref")
                request.body = "how many suplies do you have and where are you?"
                await self.send(request)
                msg = await self.receive(timeout=5)
                if msg:
                    options[msg.sender] = [msg.body.split()[1], msg.body.split()[5]]
            #melhor opçao?????

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

class SupplierAgent(agent.Agent):
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position
        self.max_supplies = 250
        self.num_supplies = self.max_supplies
        self.occupied = False

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "request_ref":
                    if not self.agent.occupied:
                            distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.sender.position)
                            response = Message(to=msg.sender)
                            response.set_metadata("performative", "inform")
                            response.body = f"Tenho {self.agent.num_supplies} e estou a {distance} metros"
                            await self.send(response)
                    else:
                        response = Message(to=msg.sender.jid)
                        response.set_metadata("performative","refuse")
                        response.body = f""
                        await self.send(response)
                if performative == "query_ref" and not self.agent.occupied:
                    if not self.agent.occupied:
                        if msg.sender in self.agent.env.agents_contact["shelter"]:
                            response = Message(to=msg.sender)
                            response.set_metadata("performative","inform")
                            response.body = f"Tenho {self.agent.num_supplies} e estou na posiçao {self.agent.position}"
                            await self.send(response)
                    else:
                        response = Message(to=msg.sender.jid)
                        response.set_metadata("performative","refuse")
                if performative == "confirm":
                    self.agent.occupied = True
                    body = msg.body
                    if body == "Come":
                        distancia = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.sender.position)
                        await asyncio.sleep(distancia)
                        self.agent.position = msg.sender.position
                        response = Message(to=msg.sender)
                        response.set_metadata("performative", "inform")
                        response.body = "Supplying requested resources."
                        needed_supplies = msg.sender.needed_suplies
                        await self.send(response)
                    if body == "Supplies received":
                        if needed_supplies > self.agent.num_supplies:
                            self.agent.num_supplies = 0
                        else:
                            self.agent.num_supplies -= needed_supplies
                        self.agent.occupied = False
                else:
                    print(f"{self.agent.name} received an unhandled message from {msg.sender.jid}: {msg.body}")

    async def setup(self):
        print(f"Supplier Agent {self.name} started with max supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessageBehaviour())

class RescuerAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.position = position  # referencia para o block atual
        self.env = env
        self.transp_space = 5
        self.occupied = False
        self.distances = {}
        self.needed_supplies = 0
        self.considering = None

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=15)
            if msg:
                if self.agent.occupied:
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "refuse")
                    response.body = f""
                    await self.send(response)
                    return
                # print(f"{self.agent.name} received message from {msg.sender}\nBody: {msg.body}")
                performative = msg.get_metadata("performative")
                if performative == 'request':
                    block_name = msg.body.split(" ")[-1]
                    print(f"vou procurar o melhor rescuer para {block_name}")
                    self.agent.considering = msg.sender
                    self.agent.add_behaviour(self.agent.DecideBestRescuer())

                    #if (self.agent.env.blocks[block_name].zone != self.agent.position.zone and
                    #        self.agent.env.blocks[block_name].zone not in self.agent.position.adj_zone):
                     #   print("estou longe vou ignorar")
                      #  response = Message(to=msg.sender)
                       # response.set_metadata("performative", "refuse")
                       # response.body = f""
                        #await self.send(response)

                    #else:
                     #   self.agent.considering = msg.sender
                      #  self.agent.add_behaviour(self.agent.DecideBestRescuer())

                elif performative == 'confirm':
                    # vamos mover ate ao local do civil
                    # depois vamos identificar se é preciso deslocar o civil ou pedir mantimentos
                    self.agent.occupied = True
                    timer_ate_block = int(msg.body.split(" ")[6])
                    self.agent.position = self.agent.env.blocks[msg.body.split(" ")[4]] #verificar
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

                        self.agent.occupied = False
                        self.agent.position = self.agent.env.blocks[shelter]
                    else:  # vamos pedir mantimentos
                        print("vais receber mantimentos")
                        self.agent.position.damage = 0  # damage = 0 pois os rescuers ja ajudaram e nao foi um dano severo para precisar de tempo a recuperar


                        resp.body = f""

                elif performative == 'request_transport' and not self.agent.occupied:
                    ...
                elif performative == 'confirm_transport':
                    ...
    class DecideBestRescuer(OneShotBehaviour):
        async def run(self):
            rescue_request = self.agent.considering.position
            options = {}
            options[self.agent.jid] = dijkstra_min_distance(self.agent.env, self.agent.position.name, rescue_request)
            for agent_jid in self.agent.env.agents_contact["rescuer"]:
                request=Message(to=agent_jid)
                request.set_metadata("performative", "request_ref")
                request.body = f"A que distancia estás do ponto {rescue_request}"
                await self.send(request)
                msg = await self.receive(timeout=5)
                if msg:
                    options[msg.sender.jid] = msg.body.split()[-2]
            best_distance = math.inf
            chosen_rescuer = None
            for key in options:
                if options[key]>best_distance:
                    chosen_rescuer = key
                    best_distance = options[key]
            request = Message(to=chosen_rescuer)
            request.set_metadata("performative", "confirm")
            request.body = f"Vai para o ponto {rescue_request} a {options[chosen_rescuer]} metros de distancia"
            await self.send(request)

            self.kill()


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
            print(f"{self.agent.name}: Precisa de ajuda no block: {self.agent.position.name}")

            agent_jid = random.choice(self.agent.env.agents_contact["rescuer"])
            msg = Message(to=agent_jid)
            msg.set_metadata("performative", "request")
            msg.body = f"Need Rescue at {self.agent.position.name}"
            await self.send(msg)


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

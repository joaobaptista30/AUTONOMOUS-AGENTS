import asyncio
import math
import random
from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.behaviour import OneShotBehaviour
from environment import load_env
from algorithms import dijkstra_min_distance
from spade.behaviour import PeriodicBehaviour
import time
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
        self.supplies_requested = False
        self.needed_supplies = 0

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "cpf":
                    # print(f"{self.agent.name}: Responded to {str(msg.sender)} with space info.")
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "propose")
                    response.body = f"Tenho espaco para {self.agent.max_people - self.agent.num_people} e estou em {self.agent.position.name}"
                    await self.send(response)

                elif performative == "inform-done":
                    if msg.sender.num_suplplies() < self.agent.max_supplies - self.agent.current_supplies:
                        self.agent.current_supplies += msg.sender.num_supplies
                    else:
                        self.agent.current_supplies = self.agent.max_supplies
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "confirm")
                    response.body = "Supplies received"
                    self.agent.supplies_requested = False

                elif performative == "accept-proposal":
                    self.agent.num_people += int(msg.body.split()[2])
                    done = Message(to=str(msg.sender))
                    done.set_metadata("performative", "inform-done")
                    done.body = f"estou em {self.agent.position.name}"
                    await self.send(done)
                elif performative == "reject-proposal":
                    return
                else:
                    print(f"{self.agent.name} received an unhandled message from {str(msg.sender)}: {msg}")

    class AskSupplies(OneShotBehaviour):
        async def run(self):
            options = {}
            self.agent.needed_supplies = self.agent.max_supplies - self.agent.current_supplies
            for agent_jid in self.agent.env.agents_contact["supply"]:
                request = Message(to=agent_jid)
                request.set_metadata("performative", "cpf")
                request.body = "how many suplies do you have and where are you?"
                await self.send(request)
                msg = await self.receive(timeout=5)
                if msg and msg.get_metadata("performative") == "propose":
                    options[msg.sender] = [msg.body.split()[1], msg.body.split()[5]]
            best_supplier = None
            mais_perto = math.inf
            for key in options:
                if options[key][1] < mais_perto:
                    best_supplier = key
                    mais_perto = options[key][1]
            for key in options:
                if key != best_supplier:
                    response = Message(to=key)
                    response.set_metadata("performative","reject_proposal")
                    response.body = f""
                    await self.send(response)
                else:
                    response = Message(to=key)
                    response.set_metadata("performative", "accept_proposal")
                    response.body = f""
                    await self.send(response)

    class CheckSupplies(CyclicBehaviour):
        async def run(self):
            if not self.agent.supplies_requested and self.agent.current_supplies <= self.agent.max_supplies / 2:
                self.agent.supplies_requested = True
                self.agent.add_behaviour(self.agent.AskSupplies())
            await asyncio.sleep(10)

    class DistributeSupplies(PeriodicBehaviour):
        async def run(self):
            self.agent.current_supplies -= self.agent.num_people

    async def setup(self):
        print(f"Shelter Agent {self.name} started with max people {self.max_people} and supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessage())
        self.add_behaviour(self.CheckSupplies())
        self.add_behaviour(self.DistributeSupplies(period=30))


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
                if performative == "cpf":
                    if not self.agent.occupied:
                        distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.sender.position)
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "propose")
                        response.body = f"Tenho {self.agent.num_supplies} e estou a {distance} metros"
                        await self.send(response)
                    else:
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative","refuse")
                        response.body = f""
                        await self.send(response)
                if performative == "query_ref" and not self.agent.occupied:
                    if not self.agent.occupied:
                        if msg.sender in self.agent.env.agents_contact["shelter"]:
                            response = Message(to=str(msg.sender))
                            response.set_metadata("performative","inform")
                            response.body = f"Tenho {self.agent.num_supplies} e estou na posiçao {self.agent.position.name}"
                            await self.send(response)
                    else:
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative","refuse")
                if performative == "accept_proposal":
                    self.agent.occupied = True
                    body = msg.body
                    distancia = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.sender.position)
                    await asyncio.sleep(distancia)
                    self.agent.position = msg.sender.position
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "inform_done")
                    if msg.sender in self.agent.env.agents_contact["shelter"]:
                        response.body = "Supplying requested resources."
                        needed_supplies = msg.sender.needed_suplies
                        await self.send(response)
                    else:
                        response.body = "arrived at the point of supply"
                        await self.send(response)
                        ...#entrega de supplys no local

                if performative == "confirm":
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
        self.num_need_save = 0
        self.civil_contact = "dummy"

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=15)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "reject-proposal":
                    return
                elif performative == "propose":
                    print("entrei no lugar errado")
                    return
                elif performative == "reject-propose":
                    return
                elif performative == "inform-done":
                    return

                elif self.agent.occupied:
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "refuse")
                    response.body = f""
                    await self.send(response)
                    return

                elif performative == "cpf":
                    # request.body = f"A que distancia estas do ponto {location_request}"
                    location_request = msg.body.split()[-1]
                    response = Message(to=str(msg.sender))
                    if (self.agent.env.blocks[location_request].zone != self.agent.position.zone and
                            self.agent.env.blocks[location_request].zone not in self.agent.position.adj_zone):
                        # print("estou longe vou ignorar")
                        response.set_metadata("performative", "refuse")
                        response.body = f""
                        await self.send(response)
                        return

                    distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, location_request)
                    response.set_metadata("performative", "propose")
                    response.body = f"Estou a uma distancia de {distance}"
                    await self.send(response)

                elif performative == 'request':
                    block_name = msg.body.split(" ")[-1]
                    print(f"vou procurar o melhor rescuer para ir ate {block_name}")
                    self.agent.num_need_save = int(msg.body.split(" ")[1])
                    self.agent.civil_contact = str(msg.sender)
                    self.agent.considering = block_name
                    self.agent.add_behaviour(self.agent.DecideBestRescuer())  # iniciar o ContractNet

                elif performative == 'accept-proposal':
                    if "Socorre" == msg.body.split(" ")[0]:
                        # vamos mover ate ao local do civil
                        # depois vamos identificar se é preciso deslocar o civil ou pedir mantimentos
                        self.agent.occupied = True
                        timer_ate_block = int(msg.body.split(" ")[-1])
                        self.agent.position = self.agent.env.blocks[msg.body.split(" ")[2]]
                        self.agent.num_need_save = int(msg.body.split(" ")[3])
                        self.agent.civil_contact = msg.body.split(" ")[8]
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "inform-done")
                        response.body = f"cheguei ao local {self.agent.position.name}"
                        await asyncio.sleep(timer_ate_block)
                        await self.send(response)

                        # --done--
                        if self.agent.position.damage > 3:   # vamos deslocar para um shelter
                            print(f"Vou {str(self.agent.jid)} escolher um shelter")
                            self.agent.add_behaviour(self.agent.FindShelter())

                        # --por fazer --
                        else:  # vamos pedir mantimentos
                            print("vais receber mantimentos")
                            self.agent.position.damage = 0  # damage = 0 pois os rescuers ja ajudaram e nao foi um dano severo para precisar de tempo a recuperar

                elif performative == 'request_transport' and not self.agent.occupied:
                    ...
                elif performative == 'confirm_transport':
                    ...

    # --done--
    class DecideBestRescuer(OneShotBehaviour):
        async def run(self):
            location_request = self.agent.considering
            num_civis = self.agent.num_need_save
            civil_contacto = self.agent.civil_contact
            best_distance = float("inf")
            chosen_rescuer = None  # Inicialmente nenhum escolhido

            for rescue_agent in self.agent.env.agents_contact["rescuer"]:
                if rescue_agent.name == self.agent.name:
                    resc_dist = dijkstra_min_distance(self.agent.env, self.agent.position.name, location_request)
                    resc_id = str(self.agent.jid)

                else:
                    request = Message(to=str(rescue_agent.jid))
                    request.set_metadata("performative", "cpf")
                    request.body = f"A que distancia estas do ponto {location_request}"
                    await self.send(request)
                    print(f"Mensagem enviada para {str(rescue_agent.jid)} a pedir a distância")

                    # time.sleep(1)
                    msg = await self.receive(timeout=10)  # Timeout evita espera infinita
                    if msg and msg.get_metadata("performative") in ["propose", "refuse"]:
                        print(f"resposta de {str(msg.sender)}\nbody: {msg.body}")
                        if msg.get_metadata("performative") == "refuse":
                            print(f"{str(msg.sender)} recusou")
                            continue
                        resc_dist = int(msg.body.split()[-1])
                        resc_id = str(msg.sender)
                        print(f"Recebida proposta de {msg.sender}: distância = {resc_dist}")

                    else:
                        print(f"Não houve resposta válida de {str(rescue_agent.jid)}\nbody: {msg.body}")

                # Atualizar o melhor rescuer
                if resc_dist < best_distance:
                    # Rejeitar o anterior escolhido, se houver
                    if chosen_rescuer:
                        reject = Message(to=chosen_rescuer)
                        reject.set_metadata("performative", "reject-proposal")
                        reject.body = ""
                        await self.send(reject)

                    best_distance = resc_dist
                    chosen_rescuer = resc_id
                else:
                    # Rejeitar o rescuer atual
                    reject = Message(to=str(msg.sender))
                    reject.set_metadata("performative", "reject-proposal")
                    reject.body = ""
                    await self.send(reject)

            # Após o loop, aceitar a melhor proposta
            if chosen_rescuer:
                accept = Message(to=chosen_rescuer)
                accept.set_metadata("performative", "accept-proposal")
                accept.body = f"Socorre em {location_request} {num_civis} civis o seu contacto {civil_contacto} tens de percorrer uma distancia de {best_distance}"
                await self.send(accept)
                print(f"Proposta aceita para {chosen_rescuer}")
            else:
                print("Nenhum rescuer adequado foi encontrado.")

            self.kill()

    # --done--
    class FindShelter(OneShotBehaviour):  # faz contratnet para encontrar o melhor shelter, desloca-se ate ao shelter e entrega os civis
        async def run(self):
            jid_rescuer = str(self.agent.jid)
            # aa._sender = jid_rescuer
            chosen_shelter = "dummy"
            best_distance = float("inf")

            for sheler_agent in self.agent.env.agents_contact["shelter"]:
                print(f"perguntar ao shelter {sheler_agent.jid} a pos e capaci")
                request = Message(to=str(sheler_agent.jid))
                request._sender = jid_rescuer  # problemas com o sender estar a None entao temos de dar set manual
                request.set_metadata("performative", "cpf")
                request.body = "Quanto espaço tens e em que ponto estas"
                print(self.agent.jid)
                print(f"mensagem enviada ao {sheler_agent.name}", request)
                await self.send(request)

                # print(f"mensagem recebida apos pedir info do {sheler_agent.name}", msg)
                msg = await self.receive(timeout=20)
                while str(msg.sender) != str(sheler_agent.jid):
                    msg = await self.receive(timeout=20)

                print(f"mensagem recebida apos pedir info do {sheler_agent.name}", msg)
                if msg and msg.get_metadata("performative") == "propose":
                    # print(f"mensagem recebida ao pedir ao agente {sheler_agent.name} {msg}")
                    shelter_espaco = int(msg.body.split(" ")[3])
                    shelter_position = msg.body.split(" ")[-1]
                    resc_dist = dijkstra_min_distance(self.agent.env, self.agent.position.name, shelter_position)
                    if best_distance > resc_dist and self.agent.num_need_save <= shelter_espaco:
                        best_distance = resc_dist
                        response = Message(to=chosen_shelter)
                        response.set_metadata("performative", "reject-proposal")
                        # response._sender = jid_rescuer  # problemas com o sender estar a None entao temos de dar set manual
                        response.body = f""
                        await self.send(response)
                        chosen_shelter = str(msg.sender)
                    else:
                        response = Message(to=str(msg.sender))
                        # response._sender = jid_rescuer  # problemas com o sender estar a None entao temos de dar set manual
                        response.set_metadata("performative", "reject-proposal")
                        response.body = f""
                        await self.send(response)

                print(f"melhor shelter: {chosen_shelter} dist: {best_distance}\n")

            accept = Message(to=chosen_shelter)
            accept.set_metadata("performative", "accept-proposal")
            accept.body = f"Vou transportar {self.agent.num_need_save} civis ate ai"  # msg para shelter a informar quantos civis
            await self.send(accept)

            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("performative") == "inform-done":
                await asyncio.sleep(best_distance)
                info = Message(to=self.agent.civil_contact)
                info.set_metadata("performative", "inform")
                info.body = f"Vamos para o shelter {msg.body.split(' ')[-1]}"
                await self.send(info)
                self.agent.position = self.agent.env.blocks[msg.body.split(" ")[-1]]
                self.agent.occupied = False
                self.agent.num_need_save = 0

    class AskSupplies(OneShotBehaviour):
        async def run(self):
            options = {}
            position_in_need = self.agent.position.name
            for agent_jid in self.agent.env.agents_contact["suppliers"]:
                cpf = Message(to=agent_jid)
                cpf.set_metadata("performative",  "cpf")
                cpf.body = "How many supplies you have and where are you"
                await self.send(cpf)
                msg = await self.receive(timeout=10)
                if msg.get_metadata("performative") == "propouse":
                    options[str(msg.sender)] = (msg.body.split()[1],msg.body.split()[-2])
            best_supplier = None
            best_distance = float("inf")
            for supplier in options:
                if options[supplier][0] < best_distance:
                    if best_supplier != None:
                        refuse_request = Message(to=best_supplier)
                        refuse_request.set_metadata("performative", "reject_proposal")
                        refuse_request.body = f"Not accepted"
                        await self.send(refuse_request)
                    best_supplier = supplier
                    best_distance = options[supplier][0]
            accept = Message(to=best_supplier)
            accept.set_metadata("performative", "accept_proposal")
            accept.body = f"Vai para o ponto {self.agent.position.name}"
            await self.send(accept)
            await self.receive(timeout=10)
    async def setup(self):
        print(f"Rescue Agent {self.name} started.")
        self.add_behaviour(self.ReceiveMessage())


# --done--
class CivilAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.home = position  # casa de origem, onde vai depois dos danos (guardar referencia para o block)
        self.position = position  # referencia para posicao atual
        self.env = env
        self.deslocado = ""  # str vazia significa que esta em casa, se estiver com texto entao esse texto vai ser o jid do shelter
        self.pedido_realizado = False
        self.civis = 3

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=15)
            if msg:
                message_text = msg.body.split(" ")
                performative = msg.get_metadata("performative")
                if performative == "inform":
                    self.agent.pedido_realizado = False  # ja realizamos o pedido
                    if message_text[0] == "Transporte":  # regressou a casa
                        self.agent.deslocado = ""
                        self.agent.position = self.agent.home
                    else:  # chegou ao shelter
                        for shelter_agent in self.agent.env.agents_contact["shelter"]:
                            if shelter_agent.position.name == message_text[-1]:
                                # como temos poucos shelter_aget podemos usar esta forma sem grande preocupacao de efficiencia
                                # caso tivessemos muitos sera melhor outra implementacao
                                self.agent.deslocado = str(shelter_agent.jid)
                                self.agent.position = shelter_agent.position
                                break
                else:
                    print(f"mensagem sem comportamento definido {str(msg.sender)} | msg\n{msg.body}\n")

    class AnalyzeDanger(CyclicBehaviour):
        async def run(self):
            if self.agent.position.damage and self.agent.position.block_type != 'shelter' and not self.agent.pedido_realizado:
                # pedir ajuda a um rescuer
                self.agent.add_behaviour(self.agent.AskRescue())
                self.agent.pedido_realizado = True

            elif self.agent.home.damage == 0 and self.agent.deslocado and not self.agent.pedido_realizado:
                # agente pode retornar a casa mas precisa de transporte
                self.agent.add_behaviour(self.agent.AskTransport())
                self.agent.pedido_realizado = True

    class AskRescue(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.name}: Precisa de ajuda no block: {self.agent.position.name}")
            for rescue_agent in self.agent.env.agents_contact["rescuer"]:
                if rescue_agent.occupied: continue
                msg = Message(to=str(rescue_agent.jid))
                msg.set_metadata("performative", "request")
                msg.body = f"Somos {self.agent.civis} e precisamos de ajuda na posicao {self.agent.position.name}"
                await self.send(msg)
                break

    class AskTransport(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.name}: pediu transporte para voltar a casa")
            msg = Message(to=self.agent.deslocado)
            msg.set_metadata("performative", "request")
            msg.body = f"Transporte para a minha casa {self.agent.position.name}"
            await self.send(msg)

    async def setup(self):
        print(f"Civil Agent {self.name} started.")
        self.add_behaviour(self.AnalyzeDanger())
        self.add_behaviour(self.ReceiveMessage())


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
    rescuer3 = RescuerAgent("rescuer3@localhost", "password", environment.blocks["DA"], environment)

    shelter1 = ShelterAgent("shelter1@localhost", "password", environment.blocks["AH"], environment)
    shelter2 = ShelterAgent("shelter2@localhost", "password", environment.blocks["GH"], environment)

    environment.agents_contact["rescuer"] = [rescuer1, rescuer2, rescuer3]
    environment.agents_contact["shelter"] = [shelter1, shelter2]

    #print(rescuer1.jid)
    #return

    # Start all agents
    await rescuer1.start(auto_register=True)
    await rescuer2.start(auto_register=True)
    await rescuer3.start(auto_register=True)
    await shelter1.start(auto_register=True)
    await shelter2.start(auto_register=True)
    await civil1.start(auto_register=True)
    await civil2.start(auto_register=True)
    print()

    environment.blocks["AE"].damage = 10
    #environment.blocks["GG"].damage = 10

    # Run the simulation for some time to allow interactions
    await asyncio.sleep(60)  # Adjust as needed to observe behavior

    print(civil1.position.name)
    print(civil2.position.name)
    # Stop agents after the test
    await civil1.stop()
    await civil2.stop()

    await rescuer1.stop()
    await rescuer2.stop()
    await rescuer3.stop()

    await shelter1.stop()
    await shelter2.stop()


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import random
from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.behaviour import OneShotBehaviour
from environment import load_env
from algorithms import dijkstra_min_distance
from spade.behaviour import PeriodicBehaviour

'''
TODO:
    adicionar logica para quando o civil precisa de mantimentos
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
                    negociation_id = msg.body.split(" ")[0]
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "propose")
                    response.body = f"{negociation_id} negociation_id | Tenho espaco para {self.agent.max_people - self.agent.num_people} e estou em {self.agent.position.name}"
                    await self.send(response)
                elif performative == "request":
                    if msg.body.split(" ")[0] == "Transporte":
                        # civil pediu para voltar para casa
                        # shelter vai pedir aos rescuer para algum vir e transportar
                        civil_jid = str(msg.sender)
                        civil_pos = msg.body.split(" ")[-1]
                        shelter_pos = self.agent.position.name

                        rescue_agent = random.choice(self.agent.env.agents_contact["rescuer"])
                        while rescue_agent.occupied:
                            rescue_agent = random.choice(self.agent.env.agents_contact["rescuer"])

                        ask_transport = Message(to=str(rescue_agent.jid))
                        ask_transport.set_metadata("performative", "request")
                        ask_transport.body = f"Transporte {msg.body.split(' ')[1]} civis do {civil_jid} para {civil_pos} primeiro vem ate mim em {shelter_pos}"
                        print(
                            f"--> {self.agent.name} vai pedir ao {rescue_agent.name} para iniciar o ContractNet para o {civil_jid.split('@')[0]} voltar a {civil_pos}")
                        await self.send(ask_transport)

                elif performative == "inform-done":
                    if "rescuer" == msg.body.split(" ")[1]:
                        # rescuer a informar que a contractnet foi concluida com sucesso e um rescuer inicio o trabalho
                        pass
                    else:
                        if msg.sender.num_suplplies() < self.agent.max_supplies - self.agent.current_supplies:
                            self.agent.current_supplies += msg.sender.num_supplies
                        else:
                            self.agent.current_supplies = self.agent.max_supplies
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "confirm")
                    response.body = "Supplies received"
                    self.agent.supplies_requested = False
                elif performative == "accept-proposal":
                    # foi o shelter escolhido pelo rescuer
                    self.agent.num_people += int(msg.body.split()[2])
                    done = Message(to=str(msg.sender))
                    done.set_metadata("performative", "inform-done")
                    done.body = f"estou em {self.agent.position.name}"
                    await self.send(done)
                elif performative == "inform":
                    if msg.body.split(" ")[0] == "Retirei":
                        # f"Retirei {msg.body.split(' ')[4]} civis do teu shelter"
                        # um civil foi transportado de volta para casa, atualizar contagem de civis
                        self.agent.num_people -= int(msg.body.split(" ")[1])
                elif performative == "failure":
                    if "rescuer" in str(
                            msg.sender):  # contractnet para saber melhor rescuer para transportar os civis falhou
                        failed_transp = Message(to=msg.body.split(" ")[-1])
                        failed_transp.set_metadata("performative", "failure")
                        failed_transp.body = "Nenhum rescuer disponivel para te transportar"
                        await self.send(failed_transp)
                elif performative == "reject-proposal":
                    pass
                elif performative == "agree":
                    pass
                else:
                    print(f"{self.agent.name} received an unhandled message from {str(msg.sender)}: {msg}")

    class AskSupplies(OneShotBehaviour):
        async def run(self):
            options = {}
            self.agent.needed_supplies = self.agent.max_supplies - self.agent.current_supplies
            for supply_agent in self.agent.env.agents_contact["supplyer"]:
                request = Message(to=str(supply_agent.jid))
                request.set_metadata("performative", "cpf")
                request.body = "how many suplies do you have and where are you?"
                await self.send(request)
                msg = await self.receive(timeout=5)
                if msg and msg.get_metadata("performative") == "propose":
                    options[msg.sender] = [msg.body.split()[1], msg.body.split()[5]]
            best_supplier = None
            closest = float("inf")
            for key in options:
                if options[key][1] < closest:
                    response = Message(to=best_supplier)
                    response.set_metadata("performative", "reject_proposal")
                    response.body = f""
                    await self.send(response)

                    best_supplier = key
                    closest = options[key][1]

            response = Message(to=best_supplier)
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
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.position = position
        self.max_supplies = 250
        self.num_supplies = self.max_supplies
        self.occupied = False
        self.env = env

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "cpf":
                    if not self.agent.occupied:
                        distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.sender.position.name)
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "propose")
                        response.body = f"Tenho {self.agent.num_supplies} e estou a {distance} metros"
                        await self.send(response)
                    else:
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "refuse")
                        response.body = f""
                        await self.send(response)
                if performative == "query_ref" and not self.agent.occupied:
                    if not self.agent.occupied:
                        if msg.sender in self.agent.env.agents_contact["shelter"]:
                            response = Message(to=str(msg.sender))
                            response.set_metadata("performative", "inform")
                            response.body = f"Tenho {self.agent.num_supplies} e estou na posiçao {self.agent.position.name}"
                            await self.send(response)
                    else:
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "refuse")
                if performative == "accept_proposal":
                    self.agent.occupied = True
                    body = msg.body
                    distancia = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.sender.position.name)
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
                        ...  # entrega de supplys no local

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
        self.tranport_civil = {}
        self.needed_supplies = 0
        self.considering = None
        self.num_need_save = 0
        self.requester_contact = "dummy"

    class ReceiveMessage(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if performative == "reject-proposal":
                    pass
                elif performative == "propose":
                    pass
                elif performative == "reject-propose":
                    pass
                elif performative == "inform-done":
                    pass

                elif self.agent.occupied:
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "refuse")
                    response.body = f"Estou ocupado"
                    await self.send(response)
                    return

                elif performative == "cpf":
                    # request.body = f"A que distancia estas do ponto {location_request}"
                    location_request = msg.body.split()[-1]
                    response = Message(to=str(msg.sender))
                    '''
                    # este if serve para ignorar caso o rescuer estaja numa divisao longe da divisao do civil,
                    # mas como o custo de calcular a distancia e pequeno pois a nossa cidade e pequena (apenas 77 nos)
                    # podemos calcular sempre, e assim evita o caso de nenhum rescuer estar perto do civil e ele nunca
                    # iria receber ajuda
                    if (self.agent.env.blocks[location_request].zone != self.agent.position.zone and
                            self.agent.env.blocks[location_request].zone not in self.agent.position.adj_zone):
                        # print("estou longe vou ignorar")
                        response.set_metadata("performative", "refuse")
                        response.body = f"Estou muito longe"
                        await self.send(response)
                        return
                    '''

                    distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, location_request)
                    response.set_metadata("performative", "propose")
                    response.body = f"{msg.body.split()[0]} negociation_id | Estou a uma distancia de {distance}"
                    await self.send(response)

                elif performative == 'request':
                    if msg.body.split(" ")[0] == "Somos":
                        # f"Somos {self.agent.civis} e precisamos de ajuda na posicao {self.agent.position.name}"
                        block_name = msg.body.split(" ")[-1]
                        print(f"\n--> {self.agent.name} vai procurar o melhor rescuer para ir socorrer em {block_name}")
                        self.agent.num_need_save = int(msg.body.split(" ")[1])
                        self.agent.requester_contact = str(msg.sender)  # jid do civil que fez o pedido
                        self.agent.considering = block_name

                    elif msg.body.split(" ")[0] == "Transporte":
                        # f"Transporte {msg.body.split(' ')[1]} civis do {civil_jid} para {civil_pos} primeiro vem ate mim em {shelter_pos}"
                        block_name = msg.body.split(" ")[-1]  # pos do shelter
                        civil_jid = msg.body.split(" ")[4]
                        civil_pos = msg.body.split(" ")[6]
                        print(
                            f"\n--> {self.agent.name} vai procurar o melhor rescuer para ir transportar o {civil_jid.split('@')[0]} de {block_name} ate {civil_pos}")
                        self.agent.considering = block_name
                        self.agent.requester_contact = str(msg.sender)  # jid do shelter que fez o pedido
                        self.agent.num_need_save = int(msg.body.split(" ")[1])
                        self.agent.tranport_civil["civil_jid"] = civil_jid
                        self.agent.tranport_civil["civil_pos"] = civil_pos

                    agree = Message(to=str(msg.sender))
                    agree.set_metadata("performative", "agree")
                    agree.body = "Vou enviar uma equipa para ajudar"
                    await self.send(agree)
                    self.agent.add_behaviour(self.agent.DecideBestRescuer())  # iniciar o ContractNet

                elif performative == 'accept-proposal':
                    if "Socorre" == msg.body.split(" ")[0]:
                        # msg.body = f"Socorre em {location_request} {num_civis} civis o seu contacto {requester_contact} tens de percorrer uma distancia de {best_distance}"
                        # vamos mover ate ao local do civil
                        # depois vamos identificar se é preciso deslocar o civil ou pedir mantimentos
                        self.agent.occupied = True
                        timer_ate_block = int(msg.body.split(" ")[-1])
                        self.agent.position = self.agent.env.blocks[msg.body.split(" ")[2]]
                        self.agent.num_need_save = int(msg.body.split(" ")[3])
                        self.agent.requester_contact = msg.body.split(" ")[8]
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "inform-done")
                        response.body = f"cheguei ao local {self.agent.position.name}"
                        await asyncio.sleep(timer_ate_block)
                        print(
                            f"--> Eu {self.agent.name} cheguei ao {self.agent.requester_contact.split('@')[0]} em {self.agent.position.name} apos viajar por {timer_ate_block}")
                        await self.send(response)

                        # --done--
                        if self.agent.position.damage > 3:  # vamos deslocar para um shelter
                            print(
                                f"\n--> Eu {str(self.agent.name)} vou escolher um shelter para o civil {self.agent.requester_contact.split('@')[0]}")
                            self.agent.add_behaviour(self.agent.FindShelter())

                        # --por fazer --
                        else:  # vamos pedir mantimentos
                            print(
                                f"\n--> Eu {str(self.agent.name)} conclui que o dano nao e severo, {self.agent.requester_contact.split('@')[0]} apenas precisas de mantimentos")
                            self.agent.position.damage = 0  # damage = 0 pois os rescuers ja ajudaram e nao foi um dano severo para precisar de tempo a recuperar

                    # --done--
                    elif "Transporte" == msg.body.split(" ")[0]:
                        # msg.body = f"Transporte o {civil_jid} com {num_civis} civis de {location_request} ate {civil_pos} distancia ate ao {requester_contact} e {best_distance}"
                        self.agent.occupied = True
                        timer_ate_block = int(msg.body.split(" ")[-1])
                        self.agent.position = self.agent.env.blocks[msg.body.split(" ")[7]]
                        self.agent.num_need_save = int(msg.body.split(" ")[4])
                        self.agent.requester_contact = msg.body.split(" ")[-3]
                        self.agent.tranport_civil["civil_jid"] = msg.body.split(" ")[2]
                        self.agent.tranport_civil["civil_pos"] = msg.body.split(" ")[9]
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "inform-done")
                        response.body = f"cheguei ao local {self.agent.position.name}"
                        # ir ate shelter
                        await asyncio.sleep(timer_ate_block)
                        await self.send(response)
                        print(
                            f"\n--> Eu {self.agent.name} cheguei ao {self.agent.requester_contact.split('@')[0]} em {self.agent.position.name} apos viajar por {timer_ate_block}")
                        # informar o shelter que vai levar x civis
                        inform_shelter = Message(to=self.agent.requester_contact)
                        inform_shelter.set_metadata("performative", "inform")
                        inform_shelter.body = f"Retirei {msg.body.split(' ')[4]} civis do teu shelter"
                        await self.send(inform_shelter)
                        # informar o civil que o vai levar a casa
                        dist_ate_casa_civil = dijkstra_min_distance(self.agent.env,
                                                                    self.agent.tranport_civil["civil_pos"],
                                                                    self.agent.position.name)
                        self.agent.position = self.agent.env.blocks[msg.body.split(" ")[9]]
                        inform_civil = Message(to=msg.body.split(" ")[2])
                        inform_civil.set_metadata("performative", "inform")
                        inform_civil.body = f"Transporte realizado ate a tua casa em {dist_ate_casa_civil}"
                        print(
                            f"--> Eu {self.agent.name} vou viajar ate a casa do {msg.body.split(' ')[2].split('@')[0]} em {msg.body.split(' ')[9]} durante {dist_ate_casa_civil}")
                        await asyncio.sleep(dist_ate_casa_civil)
                        await self.send(inform_civil)
                        self.agent.occupied = False
                        self.agent.num_need_save = 0

                elif performative == 'request_transport' and not self.agent.occupied:
                    ...
                elif performative == 'confirm_transport':
                    ...

    # --done--
    class DecideBestRescuer(OneShotBehaviour):
        async def run(self):
            location_request = self.agent.considering
            num_civis = self.agent.num_need_save
            requester_contact = self.agent.requester_contact
            negociation_id = requester_contact.split('@')[
                0]  # vamos usar requester_contact.split('@')[0] como id para a negociacao
            if "shelter" in negociation_id:
                civil_jid = self.agent.tranport_civil["civil_jid"]
                civil_pos = self.agent.tranport_civil["civil_pos"]

            best_distance = float("inf")
            chosen_rescuer = None  # Inicialmente nenhum escolhido

            for rescue_agent in self.agent.env.agents_contact["rescuer"]:
                resc_dist = float("inf")
                resc_id = "dummy"

                if rescue_agent.name == self.agent.name and not self.agent.occupied:
                    resc_dist = dijkstra_min_distance(self.agent.env, self.agent.position.name, location_request)
                    resc_id = str(self.agent.jid)
                    # print(f"{negociation_id} negociation_id | {rescue_agent.name} a uma distancia de {resc_dist}")

                else:
                    request = Message(to=str(rescue_agent.jid))
                    request.set_metadata("performative", "cpf")
                    request.body = f"{negociation_id} negociation_id | A que distancia estas do ponto {location_request}"
                    await self.send(request)
                    # print(f"Mensagem enviada para {str(rescue_agent.jid)} a pedir a distância ate {location_request}")

                    while True:
                        msg = await self.receive(timeout=5)
                        if msg and msg.body.split()[0] == negociation_id and str(msg.sender) == str(rescue_agent.jid):
                            break

                    # print(f"\n mesngagem final ao negociar dist do resc ao civil: \n{msg}\n\n")
                    if msg and msg.get_metadata("performative") in ["propose", "refuse"]:
                        if msg.get_metadata("performative") == "refuse":
                            # print(f"{str(msg.sender)} recusou")
                            continue
                        resc_dist = int(msg.body.split()[-1])
                        resc_id = str(msg.sender)
                        # print(f"{negociation_id} negociation_id | {str(msg.sender).split('@')[0]} a uma distancia de {resc_dist}")

                    else:
                        print(f"Não houve resposta válida de {str(rescue_agent.jid)}\nbody: {msg}")

                # Atualizar o melhor rescuer
                if resc_dist < best_distance:
                    # Rejeitar o anterior escolhido, se houver
                    if chosen_rescuer:
                        reject = Message(to=chosen_rescuer)
                        reject.set_metadata("performative", "reject-proposal")
                        reject.body = "exite um rescuer em melhor posicao"
                        await self.send(reject)

                    best_distance = resc_dist
                    chosen_rescuer = resc_id
                else:
                    # Rejeitar o rescuer atual
                    reject = Message(to=str(msg.sender))
                    reject.set_metadata("performative", "reject-proposal")
                    reject.body = "exite um rescuer em melhor posicao"
                    await self.send(reject)

            # Após o loop, aceitar a melhor proposta
            if chosen_rescuer:
                encontrado = Message(to=requester_contact)
                encontrado.set_metadata("performative", "inform-done")
                encontrado.body = "Um rescuer esta a dirigir-se para a sua posicao"
                await self.send(encontrado)
                if "civil" in negociation_id:
                    accept = Message(to=chosen_rescuer)
                    accept.set_metadata("performative", "accept-proposal")
                    accept.body = f"Socorre em {location_request} {num_civis} civis o seu contacto {requester_contact} tens de percorrer uma distancia de {best_distance}"
                    await self.send(accept)
                    print(
                        f"--> Proposta aceita para {chosen_rescuer} salvar o {requester_contact.split('@')[0]} em {location_request} a uma dist de {best_distance}")
                if "shelter" in negociation_id:
                    accept = Message(to=chosen_rescuer)
                    accept.set_metadata("performative", "accept-proposal")
                    accept.body = f"Transporte o {civil_jid} com {num_civis} civis de {location_request} ate {civil_pos} distancia ate ao {requester_contact} e {best_distance}"
                    await self.send(accept)
                    print(
                        f"--> Proposta aceita para {chosen_rescuer} ir ate o {requester_contact.split('@')[0]} em {location_request} a uma dist de {best_distance} e transportar o {civil_jid} com {num_civis} pessoas ate {civil_pos}")
            else:
                print(
                    f"--> Nenhum rescuer disponivel para o {requester_contact.split('@')[0]}, a informar que precisa de pedir ajuda outra vez")
                repeat_req = Message(to=requester_contact)
                repeat_req.set_metadata("performative", "failure")
                if "shelter" in negociation_id:
                    repeat_req.body = f"Repetir pedido pois nao esta nenhum rescuer disponivel para transportar o {civil_jid}"
                else:
                    repeat_req.body = "Repetir pedido pois nao esta nenhum rescuer disponivel"
                await self.send(repeat_req)

            self.kill()

    # --done--
    class FindShelter(OneShotBehaviour):  # faz contratnet para encontrar o melhor shelter, desloca-se ate ao shelter e entrega os civis
        async def run(self):
            jid_rescuer = str(self.agent.jid)
            chosen_shelter = "dummy"
            best_distance = float("inf")
            requester_contact = self.agent.requester_contact
            negociation_id = requester_contact.split('@')[0]

            for sheler_agent in self.agent.env.agents_contact["shelter"]:
                # print(f"perguntar ao shelter {sheler_agent.jid} a pos e capaci")
                request = Message(to=str(sheler_agent.jid))
                request._sender = jid_rescuer  # problemas com o sender estar a None entao temos de dar set manual
                request.set_metadata("performative", "cpf")
                request.body = f"{negociation_id} negociation_id | Quanto espaço tens e em que ponto estas"
                await self.send(request)

                while True:
                    msg = await self.receive(timeout=5)
                    if msg and msg.body.split()[0] == negociation_id and str(msg.sender) == str(sheler_agent.jid):
                        break

                if msg and msg.get_metadata("performative") == "propose":
                    shelter_espaco = int(msg.body.split(" ")[6])
                    shelter_position = msg.body.split(" ")[-1]
                    resc_dist = dijkstra_min_distance(self.agent.env, self.agent.position.name, shelter_position)
                    if best_distance > resc_dist and self.agent.num_need_save <= shelter_espaco:
                        best_distance = resc_dist
                        response = Message(to=chosen_shelter)
                        response.set_metadata("performative", "reject-proposal")
                        response.body = f"exite um shelter mais proximo"
                        await self.send(response)
                        chosen_shelter = str(msg.sender)
                    else:
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "reject-proposal")
                        response.body = f"exite um shelter mais proximo"
                        await self.send(response)

            print(
                f"--> EU {self.agent.name} vou levar o {requester_contact.split('@')[0]} para o {chosen_shelter.split('@')[0]} a uma distancia de {best_distance}\n")
            accept = Message(to=chosen_shelter)
            accept.set_metadata("performative", "accept-proposal")
            accept.body = f"Vou transportar {self.agent.num_need_save} civis ate ai"  # msg para shelter a informar quantos civis
            await self.send(accept)

            while True:
                msg = await self.receive(timeout=5)
                if msg and msg.get_metadata("performative") == "inform-done" and str(msg.sender) == chosen_shelter:
                    break

            info = Message(to=requester_contact)
            info.set_metadata("performative", "inform")
            info.body = f"Vamos para o shelter {msg.body.split(' ')[-1]}"
            await self.send(info)

            await asyncio.sleep(best_distance)
            self.agent.position = self.agent.env.blocks[msg.body.split(" ")[-1]]
            self.agent.occupied = False
            self.agent.num_need_save = 0

    class AskSupplies(OneShotBehaviour):
        async def run(self):
            options = {}
            best_supplier = None
            best_distance = float("inf")
            position_in_need = self.agent.position.name
            for agent_jid in self.agent.env.agents_contact["suppliers"]:
                cpf = Message(to=agent_jid)
                cpf.set_metadata("performative", "cpf")
                cpf.body = "How many supplies you have and where are you"
                await self.send(cpf)
                msg = await self.receive(timeout=10)
                if msg.get_metadata("performative") == "propouse":
                    options[str(msg.sender)] = (msg.body.split()[1], msg.body.split()[-2])
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
            msg = await self.receive(timeout=5)
            if msg:
                message_text = msg.body.split(" ")
                performative = msg.get_metadata("performative")
                if performative == "inform":
                    if message_text[0] == "Transporte":  # regressou a casa
                        self.agent.deslocado = ""
                        self.agent.position = self.agent.home
                        self.agent.pedido_realizado = False  # ja realizamos o pedido
                        print(
                            f"--> Eu {self.agent.name} cheguei a casa agora que ja nao tem danos apos viajar por {msg.body.split(' ')[-1]}")
                    elif message_text[0] == 'Vamos':  # chegou ao shelter
                        for shelter_agent in self.agent.env.agents_contact["shelter"]:
                            if shelter_agent.position.name == message_text[-1]:
                                # como temos poucos shelter_aget podemos usar esta forma sem grande preocupacao de efficiencia
                                # caso tivessemos muitos sera melhor outra implementacao
                                self.agent.deslocado = str(shelter_agent.jid)
                                self.agent.position = shelter_agent.position
                                await asyncio.sleep(dijkstra_min_distance(self.agent.env, self.agent.position.name,
                                                                          shelter_agent.position.name))
                                print(
                                    f"--> Eu {self.agent.name} cheguei ao {shelter_agent.name} apos ser salvo pelo {str(msg.sender).split('@')[0]}")
                                break
                        self.agent.pedido_realizado = False  # ja realizamos o pedido

                elif performative == "failure" or performative == "refuse":
                    await asyncio.sleep(5)  # aguardar 5 seg para pedir novamente ajuda
                    self.agent.pedido_realizado = False
                elif performative == "inform-done":
                    pass
                elif performative == "agree":
                    pass
                else:
                    print(f"mensagem sem comportamento definido {str(msg.sender)} | msg\n{msg}\n")

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
            print(
                f"--> Eu {self.agent.name} preciso de ajuda em {self.agent.position.name} vou pedir a um rescuer para me ajudar")
            rescue_agent = random.choice(self.agent.env.agents_contact["rescuer"])
            msg = Message(to=str(rescue_agent.jid))
            msg.set_metadata("performative", "request")
            msg.body = f"Somos {self.agent.civis} e precisamos de ajuda na posicao {self.agent.position.name}"
            await self.send(msg)

    class AskTransport(OneShotBehaviour):
        async def run(self):
            print(
                f"--> Eu {self.agent.name} pedi transporte ao {self.agent.deslocado.split('@')[0]} para voltar a casa pois ela ja nao tem dano")
            msg = Message(to=self.agent.deslocado)
            msg.set_metadata("performative", "request")
            msg.body = f"Transporte {self.agent.civis} civis para a minha casa {self.agent.home.name}"
            await self.send(msg)

    async def setup(self):
        print(f"Civil Agent {self.name} started.")
        self.add_behaviour(self.AnalyzeDanger())
        self.add_behaviour(self.ReceiveMessage())


async def populate_city(env):
    """
    there are 5 types of blocks
    house: will have 3 to 5 civil agents
    condo: will have 5 to 10 civil agents
    shelter: location of shelter agent
    supplier: depo central com mantimentos para os supply agents
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
        elif block.block_type == 'supplier':  # iniciar supplies
            ...
        elif block.block_type == "rescuer":
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

    # print(rescuer1.jid)
    # return

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
    environment.blocks["GG"].damage = 10

    # Run the simulation for some time to allow interactions
    await asyncio.sleep(40)  # Adjust as needed to observe behavior

    print(civil1.position.name)
    print(rescuer1.position.name)
    print()
    print(civil2.position.name)
    print(rescuer2.position.name)
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

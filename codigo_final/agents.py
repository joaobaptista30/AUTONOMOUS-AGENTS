import asyncio
import random
from codigo_final.algorithms import dijkstra_min_distance
from codigo_final.environment import load_env

from spade import agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour, PeriodicBehaviour
from spade.message import Message


class ShelterAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.max_people = 50
        self.num_people = 0
        self.max_supplies = 250
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
                        rescue_agent = None
                        while True:
                            rescue_agent = random.choice(self.agent.env.agents_contact["rescuer"])
                            if not rescue_agent.occupied: break

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
                        available_supplies = int(msg.body.split(" ")[-1])
                        response = Message(to=str(msg.sender))
                        response.set_metadata("perfromative", "confirm")
                        if available_supplies < self.agent.max_supplies - self.agent.current_supplies:
                            self.agent.current_supplies += available_supplies
                            response.body = f"recebi {available_supplies} supllies"
                            print(f"--> EU {self.agent.name} recebi {available_supplies} de {str(msg.sender).split('@')[0]}")
                            await self.send(response)
                        else:
                            self.agent.current_supplies = self.agent.max_supplies
                            response.body = f"recebi {available_supplies - (self.agent.max_supplies-self.agent.current_supplies)} supplies"
                            print(f"--> EU {self.agent.name} recebi {available_supplies - (self.agent.max_supplies-self.agent.current_supplies)} de {str(msg.sender).split('@')[0]}")
                            await self.send(response)

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
                    elif msg.body.split(" ")[-1] == "supplys":
                        self.agent.current_supplies += int(msg.body.split(" ")[-2])
                        print(f"--> Eu {self.agent.name} recebi {int(msg.body.split(' ')[-2])} supplies de {str(msg.sender).split('@')[0]}")
                        confirm = Message(to=str(msg.sender))
                        confirm.set_metadata("performative", "confirm")
                        confirm._sender = str(self.agent.jid)
                        confirm.body = "Recebi os supplys"
                        await self.send(confirm)
                elif performative == "failure":
                    if "rescuer" in str(msg.sender):  # contractnet para saber melhor rescuer para transportar os civis falhou
                        failed_transp = Message(to=msg.body.split(" ")[-1])
                        failed_transp.set_metadata("performative", "failure")
                        failed_transp.body = "Nenhum rescuer disponivel para te transportar"
                        await self.send(failed_transp)
                elif performative == "reject-proposal":
                    pass
                elif performative == "agree":
                    pass
                elif performative == "propose":
                    pass
                elif performative == "refuse":
                    pass
                else:
                    print(f"{self.agent.name} received an unhandled message from {str(msg.sender)}: {msg}")

    class CheckSupplies(CyclicBehaviour):
        async def run(self):
            if not self.agent.supplies_requested and self.agent.current_supplies <= self.agent.max_supplies / 2:
                self.agent.supplies_requested = True
                random_supplier = None
                while True:
                    random_supplier = random.choice(self.agent.env.agents_contact["supplier"])
                    if not random_supplier.occupied: break
                pedir_supplies = Message(to=str(random_supplier.jid))
                pedir_supplies.set_metadata("performative", "request")
                pedir_supplies.body = f"Preciso de supplies no ponto {self.agent.position.name}"
                print(f"--> Eu {self.agent.name} vou pedir supplies ao {random_supplier.name}")
                await self.send(pedir_supplies)

    class DistributeSupplies(PeriodicBehaviour):
        async def run(self):
            self.agent.current_supplies -= self.agent.num_people * 5

    async def setup(self):
        print(f"Shelter Agent {self.name} started with max people {self.max_people} and supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessage())
        self.add_behaviour(self.CheckSupplies())
        self.add_behaviour(self.DistributeSupplies(period=20))


class SupplierAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.position = position
        self.max_supplies = 125
        self.num_supplies = self.max_supplies
        self.occupied = False
        self.env = env
        self.helping_position = None
        self.helping_agent = None
        self.num_civis = 0
        self.home = position

    class ReceiveMessageBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                performative = msg.get_metadata("performative")
                if self.agent.occupied:
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "refuse")
                    response.body = f"estou ocupado"
                    await self.send(response)
                elif performative == "cpf":
                    distance = dijkstra_min_distance(self.agent.env,
                                                     self.agent.position.name,
                                                     msg.body.split(" ")[-1])
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "propose")
                    response.body = f"Tenho {self.agent.num_supplies} e estou a {distance} metros"
                    await self.send(response)
                elif performative == "accept-proposal":
                    self.agent.occupied = True
                    print(f"--> Eu {self.agent.name} fui escolhido por {str(msg.sender).split('@')[0]} para entregar supplies para no ponto {msg.body.split(' ')[-1]}")
                    distancia = dijkstra_min_distance(self.agent.env, self.agent.position.name, msg.body.split(" ")[-1])
                    self.agent.env.total_suppliers_trips += 1
                    self.agent.env.total_suppliers_time_traveled += distancia

                    await asyncio.sleep(distancia)
                    self.agent.position = self.agent.env.blocks[msg.body.split(" ")[-1]]
                    if msg.body.split(" ")[2] != "supplies":
                        self.agent.env.supplies_delivered += self.agent.num_supplies
                        agent = msg.body.split(" ")[3]
                        entregue = Message(to=str(agent))
                        entregue.set_metadata("performative", "inform")
                        entregue._sender = str(self.agent.jid)
                        entregue.body = f"Estou aqui para entregar {self.agent.num_supplies} supplys"
                        await self.send(entregue)
                        response = await self.receive(timeout=10)
                        if response.get_metadata("performative") == "confirm":
                            final = Message(to=str(msg.sender))
                            final.set_metadata("performative", "inform-done")
                            final._sender = str(self.agent.jid)
                            final.body = "No shelter entreguei os supplies"
                            await self.send(final)
                        else:
                            erro = Message(to=str(msg.sender))
                            erro.set_metadata("performative", "failure")
                            erro._sender = str(self.agent.jid)
                            erro.body = "Não entreguei os supplies"
                            await self.send(erro)
                    else:
                        self.agent.num_supplies -= int(msg.body.split(" ")[4]) * 5
                        self.agent.env.supplies_delivered += int(msg.body.split(" ")[4]) * 5
                        self.agent.position.damage = 0
                        done = Message(to=str(msg.sender))
                        done.set_metadata("performative", "inform-done")
                        done._sneder = self.agent.name
                        done.body = f"Entreguei os supplies a {int(msg.body.split(' ')[4])} civis no ponto {self.agent.position.name}"
                        await self.send(done)
                    if self.agent.num_supplies < self.agent.max_supplies * 0.25:
                        self.agent.add_behaviour(self.agent.RefillSupplies())
                    else:
                        self.agent.occupied = False
                elif performative == "confirm":
                    # if str(msg.sender) in self.agent.env.agents_contact["shelters"]:
                    if str(msg.sender) in [str(shelter.jid) for shelter in self.agent.env.agents_contact["shelter"]]:
                        supllies_taken = int(msg.body.split(" ")[-2])
                        self.agent.num_supplies -= supllies_taken
                        print(f"--> Eu {self.agent.name} entreguei {supllies_taken} ao {str(msg.sender).split('@')[0]}")
                    if self.agent.num_supplies < self.agent.max_supplies/3:
                        self.agent.add_behaviour(self.agent.RefillSupplies())
                elif performative == "request":
                    if msg.body.split(' ')[0] == 'Preciso': self.agent.num_civis = 0
                    else: self.agent.num_civis = int(msg.body.split(' ')[1])

                    self.agent.helping_agent = str(msg.sender)
                    self.agent.helping_position = msg.body.split(" ")[-1]
                    self.agent.add_behaviour(self.agent.FindSupplier())
                elif performative == "propose":
                    pass
                elif performative == "reject-proposal":
                    pass
                elif performative == "inform-done":
                    pass
                elif performative == 'refuse': # verificar se e preciso realizar algo
                    pass
                else:
                    print(f"{self.agent.name} received an unhandled message from {str(msg.sender)}: {msg.body}")

    class FindSupplier(OneShotBehaviour):
        async def run(self):
            num_civis = self.agent.num_civis
            position = self.agent.helping_position
            agent = self.agent.helping_agent
            #print(f"--> Eu {self.agent.name} vou encontrar o melhor supplier para {agent}")
            best_supplier = str(self.agent.jid)
            shortest_distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, position)
            for supplier in self.agent.env.agents_contact["supplier"]:
                cpf = Message(to=str(supplier.jid))
                cpf._sender = str(self.agent.jid)
                cpf.set_metadata("performative", "cpf")
                cpf.body = f"Quantos mantimentos tens e a que distancia estás do ponto {position}"
                await self.send(cpf)
                while True:
                    msg = await self.receive(timeout=5)
                    if msg and msg.get_metadata("performative") in ["propose","refuse"]:
                        break
                if msg.get_metadata("performative") == "propose":
                    if int(msg.body.split(" ")[-2]) <= shortest_distance:
                        reject = Message(to=best_supplier)
                        reject.set_metadata("performative", "reject-proposal")
                        reject._sender = str(self.agent.jid)
                        reject.body = "Encontrei um supplier mais próximo"
                        await self.send(reject)

                        best_supplier = str(msg.sender)
                        shortest_distance = int(msg.body.split(" ")[-2])

                    elif int(msg.body.split(" ")[-2]) > shortest_distance:
                        reject = Message(to=str(supplier.jid))
                        reject.set_metadata("performative", "reject-proposal")
                        reject._sender = str(self.agent.jid)
                        reject.body = "Encontrei um supplier mais próximo"
                        await self.send(reject)
            accept = Message(to=best_supplier)
            accept.set_metadata("performative", "accept-proposal")
            accept._sender = str(self.agent.jid)
            if num_civis == 0:
                accept.body = f"Vai levar ao {agent} supplies para o ponto {position}"
            else:
                accept.body = f"Vai levar supplies para {num_civis} civis ao ponto {position}"
                self.agent.env.civilians_rescued += num_civis
            await self.send(accept)
            while True:
                msg = await self.receive(timeout=5)
                if msg and msg.get_metadata("performative") in ["inform-done", "failure"]:
                    break
            if msg.get_metadata("performative") != "inform-done":
                self.agent.helping_agent = agent
                self.agent.helping_position = position
                self.agent.add_behaviour(self.agent.FindSupplier())
            elif msg.body.split(' ')[0] == "Entreguei":
                print(f"--> Os supplies foram distruibuidos para {num_civis} pelo {best_supplier.split('@')[0]}")
            else:
                print(f"--> Os supplies foram entregues por {str(msg.sender).split('@')[0]} ao {agent.split('@')[0]}")

    class RefillSupplies(OneShotBehaviour):
        async def run(self):
            closest_center = None
            closest_dist = float("inf")
            for supply_center in self.agent.env.supply_center:
                distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, supply_center.name)
                if distance < closest_dist:
                    closest_center = supply_center
                    closest_dist = distance

            await asyncio.sleep(distance)
            self.agent.position = closest_center
            await asyncio.sleep(3)  # tempo para refill
            self.agent.num_supplies = self.agent.max_supplies
            self.agent.occupied = False

    async def setup(self):
        print(f"Supplier Agent {self.name} started with max supplies {self.max_supplies}.")
        self.add_behaviour(self.ReceiveMessageBehaviour())


class RescuerAgent(agent.Agent):
    def __init__(self, jid, password, position, env):
        super().__init__(jid, password)
        self.position = position  # referencia para o block atual
        self.env = env
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
                elif performative == "refuse":
                    pass

                elif self.agent.occupied:
                    response = Message(to=str(msg.sender))
                    response.set_metadata("performative", "refuse")
                    response.body = f"Estou ocupado"
                    await self.send(response)

                elif performative == "cpf":
                    # request.body = f"A que distancia estas do ponto {location_request}"
                    location_request = msg.body.split()[-1]
                    response = Message(to=str(msg.sender))
                    distance = dijkstra_min_distance(self.agent.env, self.agent.position.name, location_request)
                    response.set_metadata("performative", "propose")
                    response.body = f"{msg.body.split()[0]} negociation_id | Estou a uma distancia de {distance}"
                    await self.send(response)

                elif performative == 'request':
                    if msg.body.split(" ")[0] == "Somos":
                        self.agent.num_civis = int(msg.body.split(" ")[1])
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
                    self.agent.add_behaviour(self.agent.FindRescuer())  # iniciar o ContractNet

                elif performative == 'accept-proposal':
                    if "Socorre" == msg.body.split(" ")[0]:
                        self.agent.env.total_rescuers_trips += 1
                        # msg.body = f"Socorre em {location_request} {num_civis} civis o seu contacto {requester_contact} tens de percorrer uma distancia de {best_distance}"
                        # vamos mover ate ao local do civil
                        # depois vamos identificar se é preciso deslocar o civil ou pedir mantimentos
                        self.agent.occupied = True
                        timer_ate_block = int(msg.body.split(" ")[-1])
                        self.agent.env.total_rescuers_time_traveled += timer_ate_block
                        self.agent.position = self.agent.env.blocks[msg.body.split(" ")[2]]
                        self.agent.num_need_save = int(msg.body.split(" ")[3])
                        self.agent.requester_contact = msg.body.split(" ")[8]
                        response = Message(to=str(msg.sender))
                        response.set_metadata("performative", "inform-done")
                        response.body = f"cheguei ao local {self.agent.position.name}"
                        await asyncio.sleep(timer_ate_block)
                        print(f"--> Eu {self.agent.name} cheguei ao {self.agent.requester_contact.split('@')[0]} em {self.agent.position.name} apos viajar por {timer_ate_block}")
                        await self.send(response)

                        # --done--
                        if self.agent.position.damage > 5:  # vamos deslocar para um shelter
                            print(f"\n--> Eu {str(self.agent.name)} vou escolher um shelter para o civil {self.agent.requester_contact.split('@')[0]}")
                            self.agent.add_behaviour(self.agent.FindShelter())
                    
                        # --done--
                        else:  # vamos pedir mantimentos
                            num_civis = msg.body.split(' ')[3]
                            print(f"\n--> Eu {str(self.agent.name)} conclui que o dano nao e severo, {self.agent.requester_contact.split('@')[0]} apenas precisas de mantimentos")
                            random_supplier = None
                            while True:
                                random_supplier = random.choice(self.agent.env.agents_contact["supplier"])
                                if not random_supplier.occupied: break

                            request = Message(to=str(random_supplier.jid))
                            request.set_metadata("performative", "request")
                            request._sender = self.agent.name
                            request.body = f"Há {num_civis} civis que precisao de supplies no ponto {self.agent.position.name}"
                            await self.send(request)
                            self.agent.occupied = False
                    # --done--
                    elif "Transporte" == msg.body.split(" ")[0]:
                        # msg.body = f"Transporte o {civil_jid} com {num_civis} civis de {location_request} ate {civil_pos} distancia ate ao {requester_contact} e {best_distance}"
                        self.agent.occupied = True
                        timer_ate_block = int(msg.body.split(" ")[-1])
                        self.agent.env.total_transport_home_trips += 1
                        self.agent.env.total_transport_home_time_traveled += timer_ate_block
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
                        print(f"\n--> Eu {self.agent.name} cheguei ao {self.agent.requester_contact.split('@')[0]} em {self.agent.position.name} apos viajar por {timer_ate_block}")
                        # informar o shelter que vai levar x civis
                        inform_shelter = Message(to=self.agent.requester_contact)
                        inform_shelter.set_metadata("performative", "inform")
                        inform_shelter.body = f"Retirei {msg.body.split(' ')[4]} civis do teu shelter"
                        await self.send(inform_shelter)
                        # informar o civil que o vai levar a casa
                        dist_ate_casa_civil = dijkstra_min_distance(self.agent.env,self.agent.tranport_civil["civil_pos"],self.agent.position.name)
                        self.agent.env.total_transport_home_time_traveled += dist_ate_casa_civil
                        self.agent.position = self.agent.env.blocks[msg.body.split(" ")[9]]
                        inform_civil = Message(to=msg.body.split(" ")[2])
                        inform_civil.set_metadata("performative", "inform")
                        inform_civil.body = f"Transporte realizado ate a tua casa em {dist_ate_casa_civil}"
                        print(f"--> Eu {self.agent.name} vou viajar ate a casa do {msg.body.split(' ')[2].split('@')[0]} em {msg.body.split(' ')[9]} durante {dist_ate_casa_civil}")
                        await asyncio.sleep(dist_ate_casa_civil)
                        await self.send(inform_civil)
                        self.agent.occupied = False
                        self.agent.num_need_save = 0
                else:
                    print(f"mensagem sem comportamento definido {str(msg.sender)} | msg\n{msg}\n")

    # --done--
    class FindRescuer(OneShotBehaviour):
        async def run(self):
            location_request = self.agent.considering
            num_civis = self.agent.num_need_save
            requester_contact = self.agent.requester_contact
            negociation_id = requester_contact.split('@')[0]  # vamos usar requester_contact.split('@')[0] como id para a negociacao
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
                        if (msg and msg.body.split()[0] == negociation_id and str(msg.sender) == str(rescue_agent.jid)
                                and msg.get_metadata("performative") in ["propose", "refuse"]):
                            break

                    # print(f"\n mesngagem final ao negociar dist do resc ao civil: \n{msg}\n\n")
                    if msg:
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
                    print(f"--> Proposta aceita para {chosen_rescuer.split('@')[0]} salvar o {requester_contact.split('@')[0]} em {location_request} a uma dist de {best_distance}")
                if "shelter" in negociation_id:
                    accept = Message(to=chosen_rescuer)
                    accept.set_metadata("performative", "accept-proposal")
                    accept.body = f"Transporte o {civil_jid} com {num_civis} civis de {location_request} ate {civil_pos} distancia ate ao {requester_contact} e {best_distance}"
                    await self.send(accept)
                    print(f"--> Proposta aceita para {chosen_rescuer.split('@')[0]} ir ate o {requester_contact.split('@')[0]} em {location_request} a uma dist de {best_distance} e transportar o {civil_jid.split('@')[0]} com {num_civis} pessoas ate {civil_pos}")
            else:
                print(f"--> Nenhum rescuer disponivel para o {requester_contact.split('@')[0]}, a informar que precisa de pedir ajuda outra vez")
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
            civis_to_transport = self.agent.num_need_save
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
                    if best_distance > resc_dist and civis_to_transport <= shelter_espaco:
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

            self.agent.env.total_rescuers_time_traveled += best_distance
            print(f"--> EU {self.agent.name} vou levar o {requester_contact.split('@')[0]} para o {chosen_shelter.split('@')[0]} a uma distancia de {best_distance}\n")
            accept = Message(to=chosen_shelter)
            accept.set_metadata("performative", "accept-proposal")
            accept.body = f"Vou transportar {civis_to_transport} civis ate ai"  # msg para shelter a informar quantos civis
            await self.send(accept)

            self.agent.env.civilians_rescued += civis_to_transport

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
                        print(f"--> Eu {self.agent.name} cheguei a casa agora que ja nao tem danos apos viajar por {msg.body.split(' ')[-1]}")
                    elif message_text[0] == 'Vamos':  # chegou ao shelter
                        for shelter_agent in self.agent.env.agents_contact["shelter"]:
                            if shelter_agent.position.name == message_text[-1]:
                                # como temos poucos shelter_aget podemos usar esta forma sem grande preocupacao de efficiencia
                                # caso tivessemos muitos sera melhor outra implementacao
                                self.agent.deslocado = str(shelter_agent.jid)
                                self.agent.position = shelter_agent.position
                                await asyncio.sleep(dijkstra_min_distance(self.agent.env, self.agent.position.name,shelter_agent.position.name))
                                print(f"--> Eu {self.agent.name} cheguei ao {shelter_agent.name} apos ser salvo pelo {str(msg.sender).split('@')[0]}")
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
            print(f"--> Eu {self.agent.name} preciso de ajuda em {self.agent.position.name} vou pedir a um rescuer para me ajudar")
            rescue_agent = random.choice(self.agent.env.agents_contact["rescuer"])
            msg = Message(to=str(rescue_agent.jid))
            msg.set_metadata("performative", "request")
            msg.body = f"Somos {self.agent.civis} e precisamos de ajuda na posicao {self.agent.position.name}"
            await self.send(msg)

    class AskTransport(OneShotBehaviour):
        async def run(self):
            print(f"--> Eu {self.agent.name} pedi transporte ao {self.agent.deslocado.split('@')[0]} para voltar a casa pois ela ja nao tem dano")
            msg = Message(to=self.agent.deslocado)
            msg.set_metadata("performative", "request")
            msg.body = f"Transporte {self.agent.civis} civis para a minha casa {self.agent.home.name}"
            await self.send(msg)

    async def setup(self):
        print(f"Civil Agent {self.name} started.")
        self.add_behaviour(self.AnalyzeDanger())
        self.add_behaviour(self.ReceiveMessage())


def populate_city(env,n_rescuers,n_suppliers):
    """
    n_rescuers: max number of rescuers in the city
    n_suppliers: number of supply agents per central

    there are 5 types of blocks
    house: will have 3 to 5 civilians in the civil agent
    condo: will have 6 to 10 civilians in the civil agent
    shelter: location of shelter agent
    supplier: depo central com mantimentos para os supply agents
    empty: just an empty space
    """
    agents_list = []
    civil_id = rescuer_id = shelter_id = supply_id = 1

    for block in env.blocks.values():
        agent_creation = None
        if block.block_type == 'house':  # iniciar civis
            n_civil = random.choice([3, 4, 5])
            agent_creation = CivilAgent(f"civil{civil_id}@localhost","password",block,env)
            agent_creation.civis = n_civil
            civil_id += 1

        elif block.block_type == 'condo':  # iniciar civis
            n_civil = random.choice([6, 7, 8, 9, 10])
            agent_creation = CivilAgent(f"civil{civil_id}@localhost", "password", block, env)
            agent_creation.civis = n_civil
            civil_id += 1

        elif block.block_type == 'shelter':  # iniciar shelters
            agent_creation = ShelterAgent(f"shelter{shelter_id}@localhost", "password", block, env)
            shelter_id += 1
            env.agents_contact["shelter"].append(agent_creation)

        elif block.block_type == 'supplier':  # iniciar supplies
            for i in range(n_suppliers):
                agent_creation = SupplierAgent(f"supplier{supply_id}@localhost", "password", block, env)
                supply_id += 1
                agents_list.append(agent_creation)
                env.agents_contact["supplier"].append(agent_creation)

        else:
            if random.choice([0,1]) % 2 == 0 and rescuer_id < n_rescuers:
                agent_creation = RescuerAgent(f"rescuer{rescuer_id}@localhost", "password", block, env)
                rescuer_id += 1
                env.agents_contact["rescuer"].append(agent_creation)

        if agent_creation and block.block_type != 'supplier': agents_list.append(agent_creation)

    return agents_list


async def main():
    environment = load_env("city_design.txt")
    autonomous_agents = populate_city(environment, 12, 4)

    for autonom_agent in autonomous_agents:
        await autonom_agent.start(auto_register=True)

    await asyncio.sleep(10)

    for autonom_agent in autonomous_agents:
        await autonom_agent.stop()


if __name__ == "__main__":
    asyncio.run(main())

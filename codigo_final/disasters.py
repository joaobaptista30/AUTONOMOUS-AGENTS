import asyncio
import random
from spade import agent
from spade.behaviour import PeriodicBehaviour

from codigo_final.environment import load_env


class Disaster(agent.Agent):
    # vai invocar um desastre para causar danos e assim começarem os salvamentos
    def __init__(self, jid, password, env):
        super().__init__(jid, password)
        self.env = env
        self.distaster_type = ["flood", "hurricane", "earthquake"]
        self.damage_spread = {"flood": [[10,10],[12,8],[14,6],[16,4],[18,2]],
                              "hurricane": [[10,15],[15,11],[20,7],[25,3]],
                              "earthquake": [[7,20],[10,15],[13,10],[16,5]]}
        '''
        flood: cria um dano de 10 num raio de 10m, depois a cada 2m de distancia vai diminuir 2 em dano (dist-dano) 10-10 | 12-8 | 14-6 | 16-4 | 18-2 | X-0
        hurricane: cria um dano de 15 num raio de 10m, depois a cada 5m de distancia vai diminuir 4 em dano (dist-dano) 10-15 | 15-11 | 20-7 | 25-3 | X-0 
        earthquake: cria um dano de 20 num raio de 7m, depois a cada 3m de distancia vai diminuir 5 em dano (dist-dano) 7-20 | 10-15 | 13-10 | 16-5 | X-0
        '''

    class StartDisaster(PeriodicBehaviour):
        async def on_start(self):
            await asyncio.sleep(10)

        async def run(self):
            afetados = []
            disaster_selected = random.choice(self.agent.distaster_type)
            disaster_epicenter = random.choice(list(self.agent.env.blocks.values()))
            environment = self.agent.env
            max_dist = self.agent.damage_spread[disaster_selected][-1][-2]

            # adicionar o dano em casa bloco
            visited = []
            queu = [[disaster_epicenter,0]]

            while queu:
                curr, dist = queu.pop(0)
                visited.append(curr.name)

                if curr.block_type != "shelter":
                    for dist_center, damage_taken in self.agent.damage_spread[disaster_selected]:
                        if dist <= dist_center:
                            curr.damage = damage_taken
                            afetados.append(curr.name)
                            break

                for adj in curr.adj:
                    if adj.destiny.name not in visited and dist+adj.distance <= max_dist:
                        if adj.distance < 5: 
                            adj.distance += 5
                            if random.choice([i for i in range(30)]) == 15:  # 1/30 chance the road will be blocked by the disaster
                                adj.blocked = True
                            
                        elif adj.distance < 10: adj.distance += 3
                        
                        queu.append([adj.destiny,dist+adj.distance])
            afetados.pop(0) # primeiro vai ser a disaster_epicenter e nao precisamos
            print(f"Aviso uma catastrofe ({disaster_selected}) iniciou se em {disaster_epicenter.name} e espalhou-se pelos blocos {afetados}")

    async def setup(self):
        self.add_behaviour(self.StartDisaster(period=80)) # vai iniciar um desastre a cada 60 segundos


class RepairMan(agent.Agent):
    # vai repara as casa com danos para permitir os civil regressarem
    def __init__(self, jid, password, env):
        super().__init__(jid, password)
        self.env = env

    class FixDamage(PeriodicBehaviour):
        async def run(self):
            for block in list(self.agent.env.blocks.values()):
                block.damage = max(0, block.damage-5)

    class FixRoad(PeriodicBehaviour):
        async def run(self):
            for block in list(self.agent.env.blocks.values()):
                for conn in block.adj:
                    conn.distance = conn.normal_time

    async def setup(self):
        self.add_behaviour(self.FixDamage(period=20)) # vai reparar os danos em 5 a cada 60 segundos
        self.add_behaviour(self.FixRoad(period=35)) # vai reparar os danos em 5 a cada 60 segundos


async def main():
    env = load_env("city_design.txt")
    disasters = Disaster("disastermanager@localhost","password",env)
    await disasters.start(auto_register=True)

    repairman = RepairMan("repairman@localhost","password",env)
    await repairman.start(auto_register=True)

    await asyncio.sleep(15)

    await disasters.stop()
    await repairman.stop()


if __name__ == "__main__":
    asyncio.run(main())

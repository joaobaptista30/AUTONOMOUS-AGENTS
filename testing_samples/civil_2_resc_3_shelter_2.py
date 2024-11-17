import asyncio
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms import load_env
from testes_isolados import ShelterAgent, CivilAgent, RescuerAgent


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

import asyncio
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codigo_final.algorithms import load_env
from codigo_final.agents import ShelterAgent, CivilAgent, RescuerAgent


async def main():
    environment = load_env("./codigo_final/city_design.txt")

    # iniciar agents manualmente para teste
    civil1 = CivilAgent("civil1@localhost", "password", environment.blocks["AE"], environment)
    civil2 = CivilAgent("civil2@localhost", "password", environment.blocks["GG"], environment)
    civil3 = CivilAgent("civil3@localhost", "password", environment.blocks["DE"], environment)

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
    await civil3.start(auto_register=True)
    print()

    environment.blocks["AE"].damage = 10
    environment.blocks["GG"].damage = 10
    environment.blocks["DE"].damage = 10

    # Run the simulation for some time to allow interactions
    await asyncio.sleep(60)  # Adjust as needed to observe behavior

    print("civil 1 pos:", civil1.position.name)
    print("rescuer 1 pos:", rescuer1.position.name)
    print()
    print("civil 2 pos:", civil2.position.name)
    print("rescuer 2 pos:", rescuer2.position.name)
    print()
    print("civil 3 pos:", civil3.position.name)
    print("rescuer 3 pos:", rescuer3.position.name)
    print()
    print("shelter1 espaco: ", shelter1.num_people)
    print("shelter2 espaco: ", shelter2.num_people)

    # Stop agents after the test
    await civil1.stop()
    await civil2.stop()
    await civil3.stop()

    await rescuer1.stop()
    await rescuer2.stop()
    await rescuer3.stop()

    await shelter1.stop()
    await shelter2.stop()


if __name__ == "__main__":
    asyncio.run(main())

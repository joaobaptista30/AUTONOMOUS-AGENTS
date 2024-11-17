import asyncio
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms import load_env
from testes_isolados import ShelterAgent, SupplierAgent


async def main():
    environment = load_env("./city_desing.txt")

    # iniciar agents manualmente para teste
    shelter1 = ShelterAgent("shelter1@localhost", "password", environment.blocks["AH"], environment)
    supplyer1 = SupplierAgent("supplyer1@localhost", "password", environment.blocks["BD"], environment)

    environment.agents_contact["shelter"] = [shelter1]
    environment.agents_contact["supplyer"] = [supplyer1]

    # Start all agents

    await shelter1.start(auto_register=True)
    await supplyer1.start(auto_register=True)
    print()

    shelter1.current_supplies = 100

    # Run the simulation for some time to allow interactions
    await asyncio.sleep(50)  # Adjust as needed to observe behavior

    print("shelter na pos: ", shelter1.position.name)
    print("mantimentos no shelter: ", shelter1.current_supplies)
    print("posicao atual do supplie apos entregar mantimentos ao shelter: ", supplyer1.position.name)

    # Stop agents after the test
    await shelter1.stop()
    await supplyer1.stop()


if __name__ == "__main__":
    asyncio.run(main())

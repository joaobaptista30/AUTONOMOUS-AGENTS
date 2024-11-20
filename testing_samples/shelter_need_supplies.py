import asyncio
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codigo_final.algorithms import load_env
from codigo_final.agents import ShelterAgent, SupplierAgent


async def main():
    environment = load_env("./codigo_final/city_design.txt")

    # iniciar agents manualmente para teste
    shelter1 = ShelterAgent("shelter1@localhost", "password", environment.blocks["AH"], environment)
    supplier1 = SupplierAgent("supplier1@localhost", "password", environment.blocks["BD"], environment)

    environment.agents_contact["shelter"] = [shelter1]
    environment.agents_contact["supplier"] = [supplier1]

    # Start all agents

    await shelter1.start(auto_register=True)
    await supplier1.start(auto_register=True)
    print()

    shelter1.current_supplies = 100

    # Run the simulation for some time to allow interactions
    await asyncio.sleep(40)  # Adjust as needed to observe behavior

    print("shelter na pos: ", shelter1.position.name)
    print("mantimentos no shelter: ", shelter1.current_supplies)
    print("posicao atual do supplie apos entregar mantimentos ao shelter: ", supplier1.position.name)
    print("supplies no supplier: ", supplier1.num_supplies)

    print("\ntempo medio para reabastecer: ",environment.total_suppliers_time_traveled/environment.total_suppliers_trips)
    print("mantimentos entregues: ",environment.supplies_delivered)
    # Stop agents after the test
    await shelter1.stop()
    await supplier1.stop()


if __name__ == "__main__":
    asyncio.run(main())

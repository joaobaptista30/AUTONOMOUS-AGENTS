import spade
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import asyncio

class AgenteA(spade.agent.Agent):
    class EnviaMensagem(CyclicBehaviour):
        async def run(self):
            # Cria uma mensagem destinada ao Agente B
            msg = Message(to="bob@localhost")  # Troque pelo JID do Agente B
            msg.set_metadata("performative", "inform")  # Metadados ACL
            msg.body = "Olá, Agente B! Deseja conversar?"  # Conteúdo da mensagem

            # Envia a mensagem
            await self.send(msg)
            print("Agente A: Mensagem enviada para o Agente B!")

            # Espera pela resposta
            resposta = await self.receive(timeout=10)  # Tempo limite de 10 segundos
            if resposta:
                print(f"Agente A: Resposta recebida de {resposta.sender}: {resposta.body}")
                print("Agente A: Comunicação finalizada.")
                # Finaliza o agente após receber a resposta
                await self.agent.stop()  # Para o agente A
            else:
                print("Agente A: Nenhuma resposta recebida.")
                await self.agent.stop()  # Para o agente A se não receber resposta

    async def setup(self):
        print("Agente A inicializado!")
        comportamento = self.EnviaMensagem()
        self.add_behaviour(comportamento)


class AgenteB(spade.agent.Agent):
    class RecebeMensagem(CyclicBehaviour):
        async def run(self):
            # Espera pela mensagem do Agente A
            msg = await self.receive(timeout=10)  # Espera por 10 segundos
            if msg:
                print(f"Agente B: Mensagem recebida de {msg.sender}: {msg.body}")

                # Responde de volta ao Agente A
                resposta = Message(to=str(msg.sender))  # JID do remetente (Agente A)
                resposta.set_metadata("performative", "inform")  # Metadados ACL
                resposta.body = "Sim, estou ouvindo!"  # Resposta

                # Envia a resposta
                await self.send(resposta)
                print("Agente B: Resposta enviada para o Agente A!")
                # Finaliza o agente após enviar a resposta
                await self.agent.stop()  # Para o agente B
            else:
                print("Agente B: Nenhuma mensagem recebida.")

    async def setup(self):
        print("Agente B inicializado!")
        comportamento = self.RecebeMensagem()
        self.add_behaviour(comportamento)


async def main():
    # Inicializa ambos os agentes com JIDs diferentes
    agent_b = AgenteB("bob@localhost", "password")  # Troque pelo JID e senha do Agente B
    await agent_b.start()
    await asyncio.sleep(1)  # Aguarda um momento para o Agente B estar pronto

    agent_a = AgenteA("alice@localhost", "password")  # Troque pelo JID e senha do Agente A
    await agent_a.start()

    # Aguarda indefinidamente enquanto os agentes trocam mensagens
    try:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando agentes...")

    # Para os agentes
    await agent_a.stop()
    await agent_b.stop()

# Roda o programa
if __name__ == "__main__":
    asyncio.run(main())

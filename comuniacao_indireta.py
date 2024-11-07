import spade
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import asyncio


class AgenteChat(spade.agent.Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.mensagens = []  # Lista para armazenar mensagens do chat

    class GerenciaChat(CyclicBehaviour):
        async def run(self):
            # Espera por mensagens de qualquer agente
            msg = await self.receive(timeout=10)  # Espera por 10 segundos
            if msg:
                print(f"Agente Chat: Mensagem recebida de {msg.sender}: {msg.body}")
                # Armazena a mensagem no servidor de chat
                self.agent.mensagens.append((msg.sender, msg.body))
                print("Agente Chat: Mensagem armazenada.")
            else:
                print("Agente Chat: Nenhuma mensagem recebida.")

    async def setup(self):
        print("Agente Chat inicializado!")
        comportamento = self.GerenciaChat()
        self.add_behaviour(comportamento)


class AgenteA(spade.agent.Agent):
    class EnviaMensagem(CyclicBehaviour):
        async def run(self):
            # Cria e envia uma mensagem para o AgenteChat
            msg = Message(to="chat@localhost")  # Troque pelo JID do AgenteChat
            msg.set_metadata("performative", "inform")
            msg.body = "Olá, Agente Chat! Esta é uma mensagem de Agente A."

            await self.send(msg)
            print("Agente A: Mensagem enviada para o Agente Chat!")

            # Aguarda antes de tentar ler as mensagens armazenadas no AgenteChat
            await asyncio.sleep(2)

            # Acessa as mensagens armazenadas no AgenteChat
            print("Agente A: Acessando mensagens do chat:")
            for sender, body in self.agent.chat_agent.mensagens:
                print(f"Agente A: Mensagem de {sender}: {body}")

            # Decide se quer responder a alguma mensagem
            if len(self.agent.chat_agent.mensagens) > 0:
                resposta = Message(to="chat@localhost")
                resposta.set_metadata("performative", "inform")
                resposta.body = "Agente A: Respondendo a uma mensagem."
                await self.send(resposta)
                print("Agente A: Resposta enviada para o Agente Chat!")
            # Encerra o comportamento depois de executar
            await self.agent.stop()

    async def setup(self):
        print("Agente A inicializado!")
        # Obtém uma referência ao agente de chat
        self.chat_agent = agent_chat  # Referência direta ao AgenteChat inicializado
        comportamento = self.EnviaMensagem()
        self.add_behaviour(comportamento)


class AgenteB(spade.agent.Agent):
    class EnviaMensagem(CyclicBehaviour):
        async def run(self):
            # Envia uma mensagem para o AgenteChat
            msg = Message(to="chat@localhost")  # Troque pelo JID do AgenteChat
            msg.set_metadata("performative", "inform")
            msg.body = "Olá, Agente Chat! Esta é uma mensagem de Agente B."

            await self.send(msg)
            print("Agente B: Mensagem enviada para o Agente Chat!")

            # Aguarda um pouco antes de tentar ler as mensagens
            await asyncio.sleep(2)

            # Acessa as mensagens armazenadas no AgenteChat
            print("Agente B: Acessando mensagens do chat:")
            for sender, body in self.agent.chat_agent.mensagens:
                print(f"Agente B: Mensagem de {sender}: {body}")

            # Decide se quer responder a alguma mensagem
            if len(self.agent.chat_agent.mensagens) > 0:
                resposta = Message(to="chat@localhost")
                resposta.set_metadata("performative", "inform")
                resposta.body = "Agente B: Respondendo a uma mensagem."
                await self.send(resposta)
                print("Agente B: Resposta enviada para o Agente Chat!")
            # Encerra o comportamento depois de executar
            await self.agent.stop()

    async def setup(self):
        print("Agente B inicializado!")
        # Obtém uma referência ao agente de chat
        self.chat_agent = agent_chat  # Referência direta ao AgenteChat inicializado
        comportamento = self.EnviaMensagem()
        self.add_behaviour(comportamento)


async def main():
    # Inicializa o agente de chat
    global agent_chat
    agent_chat = AgenteChat("chat@localhost", "password")  # Troque pelo JID e senha do AgenteChat
    await agent_chat.start()
    await asyncio.sleep(1)  # Aguarda um momento para o Agente Chat estar pronto

    # Inicializa os agentes A e B
    agent_a = AgenteA("alice@localhost", "password")  # Troque pelo JID e senha do Agente A
    await agent_a.start()
    await asyncio.sleep(1)  # Garante que o Agente A inicie antes de B

    agent_b = AgenteB("bob@localhost", "password")  # Troque pelo JID e senha do Agente B
    await agent_b.start()

    # Aguarda indefinidamente enquanto os agentes trocam mensagens
    try:
        while agent_a.is_alive() or agent_b.is_alive():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando agentes...")

    # Para os agentes
    await agent_a.stop()
    await agent_b.stop()
    await agent_chat.stop()


# Roda o programa
if __name__ == "__main__":
    asyncio.run(main())

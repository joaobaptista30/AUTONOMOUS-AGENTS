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
                # Armazena a mensagem e o destinatário na lista do chat
                target = msg.metadata.get("target", "todos")  # Destinatário
                self.agent.mensagens.append({"sender": msg.sender, "body": msg.body, "target": target})
                print(f"Agente Chat: Mensagem armazenada com target '{target}'.")
            else:
                print("Agente Chat: Nenhuma mensagem recebida.")

    async def setup(self):
        print("Agente Chat inicializado!")
        comportamento = self.GerenciaChat()
        self.add_behaviour(comportamento)


class AgenteA(spade.agent.Agent):
    class EnviaMensagem(CyclicBehaviour):
        async def run(self):
            # Cria e envia uma mensagem para o AgenteChat direcionada ao AgenteB
            msg = Message(to="chat@localhost")  # Troque pelo JID do AgenteChat
            msg.set_metadata("performative", "inform")
            msg.set_metadata("target", "bob@localhost")  # Define o "target" como Agente B
            msg.body = "Olá, Agente B! Esta mensagem é para você."

            await self.send(msg)
            print("Agente A: Mensagem enviada para o Agente Chat com target para Agente B!")

            await asyncio.sleep(2)  # Aguarda um pouco antes de finalizar
            await self.agent.stop()  # Encerra o agente A

    async def setup(self):
        print("Agente A inicializado!")
        comportamento = self.EnviaMensagem()
        self.add_behaviour(comportamento)


class AgenteB(spade.agent.Agent):
    class VerificaMensagensChat(CyclicBehaviour):
        async def run(self):
            # Verifica as mensagens armazenadas no AgenteChat
            print("Agente B: Acessando mensagens do chat:")
            for mensagem in self.agent.chat_agent.mensagens:
                if mensagem["target"] == "bob@localhost":  # Só responde se o target for Agente B
                    print(f"Agente B: Mensagem de {mensagem['sender']}: {mensagem['body']}")

                    # Cria uma resposta para a mensagem específica
                    resposta = Message(to="chat@localhost")  # Envia resposta ao Agente Chat
                    resposta.set_metadata("performative", "inform")
                    resposta.set_metadata("target", str(mensagem["sender"]))  # Define o remetente original como target
                    resposta.body = "Agente B: Estou respondendo à sua mensagem."

                    await self.send(resposta)
                    print("Agente B: Resposta enviada para o Agente Chat!")
                    break  # Responde uma vez e finaliza para simplificar

            await self.agent.stop()  # Encerra o agente B

    async def setup(self):
        print("Agente B inicializado!")
        # Obtém uma referência ao agente de chat
        self.chat_agent = agent_chat  # Referência direta ao AgenteChat inicializado
        comportamento = self.VerificaMensagensChat()
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

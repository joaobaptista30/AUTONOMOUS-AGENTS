import spade


class DummyAgent(spade.agent.Agent):
    async def setup(self):
        print("Hello World! I'm agent {}".format(str(self.jid)))


async def main():
    dummy = DummyAgent("bob@localhost", "password")
    dummy2 = DummyAgent("eva@localhost", "password")
    await dummy.start()
    await dummy2.start()


if __name__ == "__main__":
    spade.run(main())

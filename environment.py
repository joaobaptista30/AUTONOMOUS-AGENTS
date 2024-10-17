class Connections:
    def __init__(self, custo):
        ...


class Block:
    def __init__(self, name: str, zone: int):
        self.name = name
        self.zone = zone
        self.adj = {}


class Graph:
    def __init__(self, n_blocks):
        self.n_blocks = n_blocks
        self.blocks = []
        for i in range(n_blocks):
            self.blocks.append(Block)


class Environment:
    def __init__(self):
        # performance stats
        self.civilians_rescued = 0

    def load_env(self, env_desing_path=None) -> None:
        with open(env_desing_path, 'r') as file:
            # <input city data>
            city = Graph(0)
            ...

    def display(self) -> None:
        ...


if __name__ == "__main__":
    env = Environment()
    env.load_env(env_desing_path="./")

    env.display()

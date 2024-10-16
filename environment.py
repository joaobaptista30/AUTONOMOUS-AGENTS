class Block:
    def __init__(self, name: str, zone: int):
        self.name = name
        self.zone = zone
        self.adj = {}


class Environment:
    def __init__(self, name: str):
        self.name = name
        self.blocks = {}

        # performance stats
        self.civilians_rescued = 0

    def start_env(self, env_desing_path=None):
        with open(env_desing_path, 'r') as file:
            # <input city data>
            ...

    def display(self) -> None:
        ...


if __name__ == "__main__":
    env = Environment('porto')
    env.display()



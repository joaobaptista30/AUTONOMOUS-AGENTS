class Connections:  # edge
    def __init__(self, destiny, distance, blocked=False):
        self.destiny = destiny  # referencia para o block
        self.distance: int = distance
        self.normal_time = distance
        self.blocked: bool = blocked

    def get_destiny(self):
        return self.destiny

    def get_distance(self) -> int:
        return self.distance

    def set_distance(self, new_distance: int):
        self.distance = new_distance


class Block:  # nodes
    def __init__(self, name, block_type, zone, adj_zone):
        self.name: str = name
        self.block_type = block_type
        self.zone: int = zone
        self.adj_zone = adj_zone
        self.adj = []  # referencia para connections
        self.disaster: str = "clear"
        self.damage: int = 0

    def get_adj(self) -> list:
        return self.adj

    def set_disaster_damage(self, disaster, damage):
        self.disaster = disaster
        self.damage = damage


class Environment:
    def __init__(self):
        self.blocks = {}
        self.agents_contact = {"rescuer": [],"supplier": [],"shelter": []}  # like yellow pages for communication ['rescuer','supplier','shelter'] storing a pointer to the agent
        self.supply_center = []  # pointers to the block of supplies center
        # performance stats
        self.civilians_rescued = 0
        self.supplies_delivered = 0
        self.total_rescuers_trips = 0
        self.total_rescuers_time_traveled = 0
        self.total_suppliers_trips = 0
        self.total_suppliers_time_traveled = 0
        self.total_transport_home_trips = 0
        self.total_transport_home_time_traveled = 0


    def display(self) -> None:  # currently show the input to analise if it is correct
        print(self.blocks)
        for node in self.blocks.values():
            print(node.name, node.zone, node.adj_zone)
            for adj in node.adj:
                print(adj.destiny, adj.distance)


def load_env(env_desing_path) -> Environment:
    """
    file format:
    1st line -> number os blocks (nodes)
    n_blocks lines -> <name>,<type>,<zone>,<neighbour_zones> // type:{house,condo,shelter,supplier,empty}
    n_blocks lines -> same order input as the nodes creation to reference the adj nodes
    example:
        4
        A,house,1,2 3
        B,condo,2,1
        C,empty,3,1
        D,shelter,1,
        B 4,C 5,D 5  -- connections from A to _ with cost x
        A 10         -- connections from B to _ with cost x
                     -- connections from C to _ with cost x
        A 3          -- connections from D to _ with cost x
    /example
        in this example C does not have an exit, something that in practice will not happen
        but is allowed for other project
    """
    envir = Environment()
    with open(env_desing_path, 'r') as file:
        lines = file.read().splitlines()
        i = 1
        while i <= int(lines[0]):  # create blocks (nodes)
            name, block_type, zone, adj_z = lines[i].split(",")
            adj_zones = [int(j) for j in adj_z.split(" ") if len(adj_z) > 0]
            envir.blocks[name] = (Block(name, block_type, int(zone), adj_zones))
            if block_type == "supplier":
                envir.supply_center.append(envir.blocks[name])
            i += 1

        for node in envir.blocks.values():
            if len(lines[i]) == 0:
                i += 1
                continue
            conn = [k for k in lines[i].split(",")]
            for j in range(len(conn)):
                adj_name, dist = conn[j].split(" ")
                node.adj.append(Connections(envir.blocks[adj_name], int(dist)))
            i += 1

    return envir


if __name__ == "__main__":
    env = load_env("./city_desing.txt")
    env.display()

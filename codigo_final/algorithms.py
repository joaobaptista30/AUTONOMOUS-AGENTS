import heapq
from codigo_final.environment import load_env
import time


def dijkstra_min_distance(graph, start, target):
    '''
    graph: environment
    start: "--" letters for block name
    target: "--" letters for block name
    return: min dist | inf if can't acess
    '''

    # dict para guardar as dist min
    shortest_distances = {nome: float('inf') for nome in graph.blocks.keys()}
    shortest_distances[start] = 0

    # heap min para procurar melhor caminho
    priority_queue = [(0, start)]

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)

        # atingimos o objetivo
        if current_node == target:
            return current_distance

        # se a distancia for maior do que a menor ja encontrada ignorar
        if current_distance > shortest_distances[current_node]:
            continue

        # explorar novas connections
        for connection in graph.blocks[current_node].adj:
            if connection.blocked: continue  # ligacao obstruida
            
            distance = current_distance + connection.distance
            neighbor = connection.destiny.name

            # apenas considerar se for melhor do que o anterior
            if distance < shortest_distances[neighbor]:
                shortest_distances[neighbor] = distance
                heapq.heappush(priority_queue, (distance, neighbor))

    # se nao encontrar (caminho bloqueado) retornar inf
    return float('inf')


if __name__ == "__main__":
    env = load_env("./city_design.txt")
    i = time.time()
    P1 = "DE"
    P2 = "FA"
    a_to_b = dijkstra_min_distance(env, P1, P2)

    print(f"dist de {P1} a {P2} min={a_to_b} calculado em {time.time()-i:.2e}")

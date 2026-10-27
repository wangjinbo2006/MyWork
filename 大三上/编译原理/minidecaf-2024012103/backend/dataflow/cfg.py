from backend.dataflow.basicblock import BasicBlock


class CFG:
    def __init__(self, nodes: list[BasicBlock], edges: list[tuple[int, int]]) -> None:
        self.nodes = nodes
        self.edges = edges

        self.links = []

        for i in range(len(nodes)):
            self.links.append((set(), set()))

        for (u, v) in edges:
            self.links[u][1].add(v)
            self.links[v][0].add(u)

        self.reachable: set[int] = set()
        pending = [0] if nodes else []
        while pending:
            block_id = pending.pop()
            if block_id in self.reachable:
                continue
            self.reachable.add(block_id)
            pending.extend(self.getSucc(block_id) - self.reachable)

    def isReachable(self, id: int) -> bool:
        return id in self.reachable

    def getBlock(self, id):
        return self.nodes[id]

    def getPrev(self, id):
        return self.links[id][0]

    def getSucc(self, id):
        return self.links[id][1]

    def getInDegree(self, id):
        return len(self.links[id][0])

    def getOutDegree(self, id):
        return len(self.links[id][1])

    def iterator(self):
        return iter(self.nodes)

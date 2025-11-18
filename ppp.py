import sys
sys.setrecursionlimit(200000)

def dfs(u, parent, total, graph, chocolates):
    farthest_node = u
    max_chocolates = total + chocolates[u]
    for v in graph[u]:
        if v == parent:
            continue
        node, choco_sum = dfs(v, u, total + chocolates[u], graph, chocolates)
        if choco_sum > max_chocolates:
            farthest_node, max_chocolates = node, choco_sum
    return farthest_node, max_chocolates


def main():
    n = int(sys.stdin.readline())
    chocolates = [0] + list(map(int, sys.stdin.readline().split()))

    graph = [[] for _ in range(n + 1)]
    for _ in range(n - 1):
        u, v = map(int, sys.stdin.readline().split())
        graph[u].append(v)
        graph[v].append(u)

    # Step 1: Find farthest node from an arbitrary node (say node 1)
    farthest1, _ = dfs(1, -1, 0, graph, chocolates)

    # Step 2: From that farthest node, find farthest again (tree diameter)
    _, max_chocolates = dfs(farthest1, -1, 0, graph, chocolates)

    print(max_chocolates)


if __name__ == "__main__":
    main()

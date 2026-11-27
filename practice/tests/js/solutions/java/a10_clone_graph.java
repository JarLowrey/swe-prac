import java.util.*;

class Solution {
    public Node cloneGraph(Node node) {
        if (node == null) return null;
        Map<Node, Node> copies = new HashMap<>();
        Deque<Node> todo = new ArrayDeque<>();
        copies.put(node, new Node(node.val));
        todo.add(node);
        while (!todo.isEmpty()) {
            Node current = todo.poll();
            for (Node next : current.neighbors) {
                if (!copies.containsKey(next)) {
                    copies.put(next, new Node(next.val));
                    todo.add(next);
                }
                copies.get(current).neighbors.add(copies.get(next));
            }
        }
        return copies.get(node);
    }
}

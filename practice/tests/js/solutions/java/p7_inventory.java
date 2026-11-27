import java.util.*;

class Inventory {
    private static final class Product {
        int price;
        int stock;
        int sold; // net of returns
        final List<int[]> discounts = new ArrayList<>(); // {percent, start, end}

        Product(int price) {
            this.price = price;
        }
    }

    private static final class Line {
        final int qty;
        final int unitPrice;
        int returned;

        Line(int qty, int unitPrice) {
            this.qty = qty;
            this.unitPrice = unitPrice;
        }
    }

    private final Map<String, Product> products = new HashMap<>();
    private final Map<String, Map<String, Line>> orders = new HashMap<>();
    private final List<long[]> ledger = new ArrayList<>(); // {timestamp, +sale or -refund}
    private int nextOrder = 1;

    public Inventory() {
    }

    private int unitPrice(Product product, int timestamp) {
        int percent = 0;
        for (int[] d : product.discounts) {
            if (d[1] <= timestamp && timestamp < d[2]) percent = Math.max(percent, d[0]);
        }
        return (int) ((long) product.price * (100 - percent) / 100);
    }

    public boolean addProduct(int timestamp, String sku, int price) {
        if (products.containsKey(sku)) return false;
        products.put(sku, new Product(price));
        return true;
    }

    public Integer restock(int timestamp, String sku, int qty) {
        Product product = products.get(sku);
        if (product == null || qty <= 0) return null;
        product.stock += qty;
        return product.stock;
    }

    public String sell(int timestamp, String sku, int qty) {
        return placeOrder(timestamp, Arrays.asList(new OrderLine(sku, qty)));
    }

    public String placeOrder(int timestamp, List<OrderLine> lines) {
        if (lines.isEmpty()) return null;
        Map<String, Integer> wanted = new LinkedHashMap<>();
        for (OrderLine line : lines) {
            if (!products.containsKey(line.sku()) || line.qty() <= 0) return null;
            wanted.merge(line.sku(), line.qty(), Integer::sum);
        }
        for (Map.Entry<String, Integer> e : wanted.entrySet()) {
            if (products.get(e.getKey()).stock < e.getValue()) return null;
        }
        String orderId = "order" + nextOrder++;
        Map<String, Line> order = new HashMap<>();
        for (Map.Entry<String, Integer> e : wanted.entrySet()) {
            Product product = products.get(e.getKey());
            int unit = unitPrice(product, timestamp);
            int qty = e.getValue();
            product.stock -= qty;
            product.sold += qty;
            order.put(e.getKey(), new Line(qty, unit));
            ledger.add(new long[] {timestamp, (long) unit * qty});
        }
        orders.put(orderId, order);
        return orderId;
    }

    public String topSellers(int timestamp, int n) {
        List<Map.Entry<String, Product>> ranked = new ArrayList<>();
        for (Map.Entry<String, Product> e : products.entrySet()) {
            if (e.getValue().sold > 0) ranked.add(e);
        }
        ranked.sort((a, b) -> a.getValue().sold != b.getValue().sold
                ? Integer.compare(b.getValue().sold, a.getValue().sold)
                : a.getKey().compareTo(b.getKey()));
        List<String> parts = new ArrayList<>();
        for (int i = 0; i < Math.min(n, ranked.size()); i++) {
            parts.add(ranked.get(i).getKey() + "(" + ranked.get(i).getValue().sold + ")");
        }
        return String.join(", ", parts);
    }

    public boolean setPrice(int timestamp, String sku, int price) {
        Product product = products.get(sku);
        if (product == null) return false;
        product.price = price;
        return true;
    }

    public Integer returnItems(int timestamp, String orderId, String sku, int qty) {
        Map<String, Line> order = orders.get(orderId);
        Line line = order == null ? null : order.get(sku);
        if (line == null || qty <= 0 || qty > line.qty - line.returned) return null;
        line.returned += qty;
        Product product = products.get(sku);
        product.stock += qty;
        product.sold -= qty;
        int refund = qty * line.unitPrice;
        ledger.add(new long[] {timestamp, -refund});
        return refund;
    }

    public boolean addDiscount(int timestamp, String sku, int percent, int startTs, int endTs) {
        Product product = products.get(sku);
        if (product == null) return false;
        product.discounts.add(new int[] {percent, startTs, endTs});
        return true;
    }

    public int revenue(int timestamp, int startTs, int endTs) {
        long total = 0;
        for (long[] entry : ledger) {
            if (startTs <= entry[0] && entry[0] < endTs) total += entry[1];
        }
        return (int) total;
    }
}

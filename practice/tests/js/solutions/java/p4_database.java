import java.util.*;

class InMemoryDB {
    // A field is alive while timestamp < expiresAt (infinity: no TTL). In a backup, expiresAt
    // holds the time it had left instead.
    private record Field(String value, double expiresAt) {}

    private Map<String, Map<String, Field>> data = new HashMap<>();
    private final List<Integer> backupTimes = new ArrayList<>();
    private final List<Map<String, Map<String, Field>>> backups = new ArrayList<>();

    public InMemoryDB() {
    }

    private TreeMap<String, Field> live(int timestamp, String key) {
        TreeMap<String, Field> out = new TreeMap<>();
        Map<String, Field> fields = data.get(key);
        if (fields != null) {
            for (Map.Entry<String, Field> e : fields.entrySet()) {
                if (timestamp < e.getValue().expiresAt()) out.put(e.getKey(), e.getValue());
            }
        }
        return out;
    }

    private static String format(Map<String, Field> fields) {
        List<String> parts = new ArrayList<>();
        for (Map.Entry<String, Field> e : fields.entrySet()) parts.add(e.getKey() + "(" + e.getValue().value() + ")");
        return String.join(", ", parts);
    }

    public void set(int timestamp, String key, String field, String value) {
        data.computeIfAbsent(key, k -> new HashMap<>()).put(field, new Field(value, Double.POSITIVE_INFINITY));
    }

    public String get(int timestamp, String key, String field) {
        Field found = live(timestamp, key).get(field);
        return found == null ? null : found.value();
    }

    public boolean delete(int timestamp, String key, String field) {
        if (!live(timestamp, key).containsKey(field)) return false;
        Map<String, Field> fields = data.get(key);
        fields.remove(field);
        if (fields.isEmpty()) data.remove(key);
        return true;
    }

    public String scan(int timestamp, String key) {
        return format(live(timestamp, key));
    }

    public String scanByPrefix(int timestamp, String key, String prefix) {
        TreeMap<String, Field> matching = new TreeMap<>();
        for (Map.Entry<String, Field> e : live(timestamp, key).entrySet()) {
            if (e.getKey().startsWith(prefix)) matching.put(e.getKey(), e.getValue());
        }
        return format(matching);
    }

    public void setWithTtl(int timestamp, String key, String field, String value, int ttl) {
        data.computeIfAbsent(key, k -> new HashMap<>()).put(field, new Field(value, (double) timestamp + ttl));
    }

    public int backup(int timestamp) {
        Map<String, Map<String, Field>> snapshot = new HashMap<>();
        for (String key : data.keySet()) {
            Map<String, Field> fields = new HashMap<>();
            for (Map.Entry<String, Field> e : live(timestamp, key).entrySet()) {
                fields.put(e.getKey(), new Field(e.getValue().value(), e.getValue().expiresAt() - timestamp));
            }
            if (!fields.isEmpty()) snapshot.put(key, fields);
        }
        backupTimes.add(timestamp);
        backups.add(snapshot);
        return snapshot.size();
    }

    public void restore(int timestamp, int timestampToRestore) {
        int i = backupTimes.size() - 1;
        while (backupTimes.get(i) > timestampToRestore) i--;
        data = new HashMap<>();
        for (Map.Entry<String, Map<String, Field>> e : backups.get(i).entrySet()) {
            Map<String, Field> fields = new HashMap<>();
            for (Map.Entry<String, Field> f : e.getValue().entrySet()) {
                fields.put(f.getKey(), new Field(f.getValue().value(), timestamp + f.getValue().expiresAt()));
            }
            data.put(e.getKey(), fields);
        }
    }
}

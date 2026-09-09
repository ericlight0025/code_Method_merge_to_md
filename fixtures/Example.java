package demo;

public class OrderService {
    private final String prefix = "{not a method}";

    // function hiddenComment() { return false; }
    public OrderService() {
        // 大括號在字串與註解中不應影響 method 範圍。
        System.out.println(prefix);
    }

    @Override
    public String greet(String name) {
        String message = "hello {world}";
        return prefix + name + message.substring(0, 0);
    }

    public static int add(int left, int right) {
        return left + right;
    }

    public int calculateTotal(
        int price,
        int quantity
    ) throws IllegalArgumentException {
        if (quantity < 0) {
            throw new IllegalArgumentException("quantity must not be negative");
        }
        return price * quantity;
    }

    private void log(String message) {
        System.out.println(message);
    }
}

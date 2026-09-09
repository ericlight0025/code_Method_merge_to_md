package demo;

import org.springframework.stereotype.Service;

@Service
public class GreetingService {
    public String greet(String name) {
        String safeName = normalizeName(name);
        return "Hello, " + safeName + "!";
    }

    private String normalizeName(String name) {
        if (name == null || name.isBlank()) {
            return "World";
        }
        return name.trim();
    }
}

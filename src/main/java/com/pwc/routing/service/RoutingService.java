package com.pwc.routing.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pwc.routing.model.Country;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service responsible for loading country border data and finding the shortest route.
 */
@Service
public class RoutingService {

    private static final Logger log = LoggerFactory.getLogger(RoutingService.class);

    @Value("${routing.countries-url:https://raw.githubusercontent.com/mledoze/countries/master/countries.json}")
    private String countriesUrl;

    private final ObjectMapper objectMapper;
    private final ResourceLoader resourceLoader;
    private final Map<String, List<String>> countryGraph = new ConcurrentHashMap<>();

    public RoutingService(ObjectMapper objectMapper, ResourceLoader resourceLoader) {
        this.objectMapper = objectMapper;
        this.resourceLoader = resourceLoader;
    }

    /**
     * Initializes the graph by fetching the country JSON. Runs after application startup.
     */
    @EventListener(ApplicationReadyEvent.class)
    public void initializeGraph() {
        try {
            log.info("Fetching country data from: {}", countriesUrl);
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(countriesUrl))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                parseAndBuildGraph(response.body());
                log.info("Successfully initialized country graph from remote URL. Total countries loaded: {}", countryGraph.size());
            } else {
                throw new RuntimeException("Failed to fetch country data. Status code: " + response.statusCode());
            }
        } catch (Exception e) {
            log.warn("Could not load country data from remote URL: {}. Falling back to local classpath copy.", e.getMessage());
            loadFallbackData();
        }
    }

    /**
     * Helper to load data from the local classpath countries.json when offline or remote is down.
     */
    private void loadFallbackData() {
        try {
            Resource resource = resourceLoader.getResource("classpath:countries.json");
            try (InputStream inputStream = resource.getInputStream()) {
                List<Country> countries = objectMapper.readValue(inputStream, new TypeReference<List<Country>>() {});
                buildGraphFromList(countries);
                log.info("Successfully initialized country graph from local fallback. Total countries loaded: {}", countryGraph.size());
            }
        } catch (Exception e) {
            log.error("Critical error: Failed to load local fallback country data.", e);
        }
    }

    /**
     * Parses the raw JSON array string and populates the graph map.
     */
    public void parseAndBuildGraph(String jsonContent) throws Exception {
        List<Country> countries = objectMapper.readValue(jsonContent, new TypeReference<List<Country>>() {});
        buildGraphFromList(countries);
    }

    /**
     * Populates the internal graph representation.
     */
    public void buildGraphFromList(List<Country> countries) {
        countryGraph.clear();
        if (countries == null) return;
        for (Country country : countries) {
            if (country.cca3() != null) {
                String code = country.cca3().toUpperCase();
                List<String> borders = country.borders() != null ? country.borders() : List.of();
                countryGraph.put(code, borders);
            }
        }
    }

    /**
     * Finds the shortest route from origin to destination using Breadth-First Search (BFS).
     *
     * @param origin      3-letter country code of the origin (case-insensitive)
     * @param destination 3-letter country code of the destination (case-insensitive)
     * @return List of country codes from origin to destination inclusive, or empty list if unreachable
     * @throws IllegalArgumentException if country codes are invalid or null
     */
    public List<String> findRoute(String origin, String destination) {
        if (origin == null || destination == null) {
            throw new IllegalArgumentException("Origin and destination must not be null");
        }

        String start = origin.trim().toUpperCase();
        String end = destination.trim().toUpperCase();

        if (!countryGraph.containsKey(start)) {
            throw new IllegalArgumentException("Origin country code '" + start + "' is not a valid country");
        }
        if (!countryGraph.containsKey(end)) {
            throw new IllegalArgumentException("Destination country code '" + end + "' is not a valid country");
        }

        // Trivial case
        if (start.equals(end)) {
            return List.of(start);
        }

        // BFS setup
        Queue<String> queue = new LinkedList<>();
        Set<String> visited = new HashSet<>();
        Map<String, String> parentMap = new HashMap<>();

        queue.add(start);
        visited.add(start);

        boolean found = false;

        while (!queue.isEmpty()) {
            String current = queue.poll();

            if (current.equals(end)) {
                found = true;
                break;
            }

            List<String> neighbors = countryGraph.get(current);
            if (neighbors != null) {
                for (String neighbor : neighbors) {
                    String neighborUpper = neighbor.trim().toUpperCase();
                    // Ensure the neighbor actually exists in our loaded database
                    if (countryGraph.containsKey(neighborUpper) && !visited.contains(neighborUpper)) {
                        visited.add(neighborUpper);
                        parentMap.put(neighborUpper, current);
                        queue.add(neighborUpper);
                    }
                }
            }
        }

        if (!found) {
            return List.of();
        }

        // Reconstruct path
        List<String> path = new LinkedList<>();
        String step = end;
        while (step != null) {
            path.add(0, step);
            step = parentMap.get(step);
        }

        return path;
    }

    /**
     * Gets a read-only view of the loaded countries graph. Useful for debugging and testing.
     */
    public Map<String, List<String>> getCountryGraph() {
        return Collections.unmodifiableMap(countryGraph);
    }
}

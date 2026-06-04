package com.pwc.routing.service;

import com.pwc.routing.model.Country;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.DefaultResourceLoader;
import org.springframework.core.io.ResourceLoader;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class RoutingServiceTest {

    private RoutingService routingService;

    @BeforeEach
    void setUp() {
        ResourceLoader resourceLoader = new DefaultResourceLoader();
        routingService = new RoutingService(null, resourceLoader);

        // Build a mock graph:
        // CZE is connected to DEU, POL, SVK, AUT
        // AUT is connected to CZE, ITA, SVK
        // ITA is connected to AUT
        // MDG is an island (no borders)
        List<Country> mockCountries = List.of(
                new Country("CZE", List.of("DEU", "POL", "SVK", "AUT")),
                new Country("AUT", List.of("CZE", "ITA", "SVK")),
                new Country("ITA", List.of("AUT")),
                new Country("DEU", List.of("CZE")),
                new Country("POL", List.of("CZE")),
                new Country("SVK", List.of("CZE", "AUT")),
                new Country("MDG", List.of())
        );

        routingService.buildGraphFromList(mockCountries);
    }

    @Test
    void testFindRoute_Success_DirectConnection() {
        List<String> route = routingService.findRoute("CZE", "AUT");
        assertEquals(List.of("CZE", "AUT"), route);
    }

    @Test
    void testFindRoute_Success_MultiHopConnection() {
        List<String> route = routingService.findRoute("CZE", "ITA");
        assertEquals(List.of("CZE", "AUT", "ITA"), route);
    }

    @Test
    void testFindRoute_Success_CaseInsensitiveAndWhitespace() {
        List<String> route = routingService.findRoute(" cze ", "  ita ");
        assertEquals(List.of("CZE", "AUT", "ITA"), route);
    }

    @Test
    void testFindRoute_Success_SameCountry() {
        List<String> route = routingService.findRoute("CZE", "CZE");
        assertEquals(List.of("CZE"), route);
    }

    @Test
    void testFindRoute_Unreachable_IslandCountry() {
        List<String> route = routingService.findRoute("CZE", "MDG");
        assertTrue(route.isEmpty());
    }

    @Test
    void testFindRoute_Throws_InvalidOrigin() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                routingService.findRoute("XYZ", "ITA")
        );
        assertTrue(exception.getMessage().contains("Origin country code 'XYZ' is not a valid country"));
    }

    @Test
    void testFindRoute_Throws_InvalidDestination() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                routingService.findRoute("CZE", "XYZ")
        );
        assertTrue(exception.getMessage().contains("Destination country code 'XYZ' is not a valid country"));
    }

    @Test
    void testFindRoute_Throws_NullInput() {
        assertThrows(IllegalArgumentException.class, () ->
                routingService.findRoute(null, "ITA")
        );
        assertThrows(IllegalArgumentException.class, () ->
                routingService.findRoute("CZE", null)
        );
    }
}

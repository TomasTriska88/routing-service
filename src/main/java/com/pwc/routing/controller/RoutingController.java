package com.pwc.routing.controller;

import com.pwc.routing.service.RoutingService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * REST Controller for routing queries.
 */
@RestController
@RequestMapping("/routing")
public class RoutingController {

    private final RoutingService routingService;

    public RoutingController(RoutingService routingService) {
        this.routingService = routingService;
    }

    /**
     * Exposes endpoint to calculate the land route between origin and destination.
     *
     * @param origin      The origin country code (e.g. CZE)
     * @param destination The destination country code (e.g. ITA)
     * @return HTTP 200 with the route, or HTTP 400 if unreachable or invalid
     */
    @GetMapping("/{origin}/{destination}")
    public ResponseEntity<RoutingResponse> getRoute(
            @PathVariable("origin") String origin,
            @PathVariable("destination") String destination) {

        List<String> route = routingService.findRoute(origin, destination);

        if (route.isEmpty()) {
            // Throw custom exception representing "No land route found"
            throw new NoRouteException("No land route found between " + origin + " and " + destination);
        }

        return ResponseEntity.ok(new RoutingResponse(route));
    }

    /**
     * Response payload representing the calculated route list.
     */
    public record RoutingResponse(List<String> route) {}

    /**
     * Custom exception thrown when no route is found between two valid countries.
     */
    public static class NoRouteException extends RuntimeException {
        public NoRouteException(String message) {
            super(message);
        }
    }
}

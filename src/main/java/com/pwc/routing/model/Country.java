package com.pwc.routing.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

/**
 * Represents a country's model containing its 3-letter code and list of neighboring country codes.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Country(
    String cca3,
    List<String> borders
) {}

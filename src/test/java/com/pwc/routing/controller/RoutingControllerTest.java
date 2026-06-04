package com.pwc.routing.controller;

import com.pwc.routing.service.RoutingService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(RoutingController.class)
class RoutingControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private RoutingService routingService;

    @Test
    void testGetRoute_Success() throws Exception {
        when(routingService.findRoute("CZE", "ITA")).thenReturn(List.of("CZE", "AUT", "ITA"));

        mockMvc.perform(get("/routing/CZE/ITA")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.route").isArray())
                .andExpect(jsonPath("$.route[0]").value("CZE"))
                .andExpect(jsonPath("$.route[1]").value("AUT"))
                .andExpect(jsonPath("$.route[2]").value("ITA"));
    }

    @Test
    void testGetRoute_NoRoute_ReturnsHttp400() throws Exception {
        // When there's no land crossing, service returns empty list
        when(routingService.findRoute("CZE", "MDG")).thenReturn(List.of());

        mockMvc.perform(get("/routing/CZE/MDG")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.message").value("No land route found between CZE and MDG"));
    }

    @Test
    void testGetRoute_InvalidCountry_ReturnsHttp400() throws Exception {
        // When a country code is invalid, service throws IllegalArgumentException
        when(routingService.findRoute("CZE", "XYZ")).thenThrow(new IllegalArgumentException("Destination country code 'XYZ' is not a valid country"));

        mockMvc.perform(get("/routing/CZE/XYZ")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.message").value("Destination country code 'XYZ' is not a valid country"));
    }
}

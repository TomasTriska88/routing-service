package com.pwc.routing.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

import java.time.LocalDateTime;

/**
 * Controller advice to globally handle application exceptions and map them to HTTP 400.
 */
@ControllerAdvice
public class GlobalExceptionHandler {

    /**
     * Handles exceptions relating to unreachable countries or invalid country input parameters.
     */
    @ExceptionHandler({
            IllegalArgumentException.class,
            RoutingController.NoRouteException.class
    })
    public ResponseEntity<ErrorResponse> handleRoutingExceptions(RuntimeException ex) {
        ErrorResponse errorResponse = new ErrorResponse(
                HttpStatus.BAD_REQUEST.value(),
                ex.getMessage(),
                LocalDateTime.now()
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Payload for REST error responses.
     */
    public record ErrorResponse(
            int status,
            String message,
            LocalDateTime timestamp
    ) {}
}

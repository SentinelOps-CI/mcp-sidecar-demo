# Multi-stage build for MCP Sidecar
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o sidecar .

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates tzdata

# Create non-root user
RUN addgroup -g 1001 -S sidecar && \
    adduser -u 1001 -S sidecar -G sidecar

# Set working directory
WORKDIR /opt/sidecar

# Copy binary from builder
COPY --from=builder /app/sidecar .

# Copy configuration files
COPY config.yaml ./
COPY policy.yaml ./

# Create necessary directories
RUN mkdir -p /opt/mcp-servers /var/log/sidecar && \
    chown -R sidecar:sidecar /opt/sidecar /var/log/sidecar

# Switch to non-root user
USER sidecar

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the sidecar
CMD ["./sidecar"]
